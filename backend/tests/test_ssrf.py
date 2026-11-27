import pytest

from app.security.ssrf import UnsafeUrlError, validate_url, safe_fetch


class FakeResponse:
    def __init__(self, status_code=200, headers=None, content=b"<html><body>ok</body></html>", url="http://x/"):
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/html"}
        self._content = content
        self.url = url
        self.text = content.decode("utf-8", "replace")

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, value):
        self._content = value


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, headers=None):
        self.calls.append(url)
        return self.responses[len(self.calls) - 1] if len(self.calls) <= len(self.responses) else self.responses[-1]


def test_schemas_non_http_rejetes():
    for url in ["file:///etc/passwd", "ftp://example.com/x", "gopher://x", "data:text/html,x"]:
        with pytest.raises(UnsafeUrlError):
            validate_url(url)


def test_boucle_locale_rejetee():
    for url in ["http://127.0.0.1:8000/", "http://localhost/x", "http://[::1]/",
                "http://10.0.0.5/admin", "http://192.168.1.1/", "http://169.254.169.254/latest/meta-data",
                "http://172.16.0.9/"]:
        with pytest.raises(UnsafeUrlError):
            validate_url(url)


def test_identifiants_dans_url_rejetes():
    with pytest.raises(UnsafeUrlError):
        validate_url("http://user:pass@example.com/")


def test_port_non_standard_rejete():
    with pytest.raises(UnsafeUrlError):
        validate_url("http://example.com:8080/x")


def test_dns_inexistant_rejete():
    with pytest.raises(UnsafeUrlError):
        validate_url("http://ce-domaine-nexiste-pas-sdh-xyz.invalid/")


def test_url_publique_valide():
    assert validate_url("https://www.patagonia.com/product/x.html")


def test_redirection_vers_ressource_privee_bloquee():
    # Un site public redirige vers une IP interne : la revalidation du saut doit bloquer
    client = FakeClient([
        FakeResponse(302, {"location": "http://127.0.0.1:9/admin", "content-type": "text/html"}),
    ])
    with pytest.raises(UnsafeUrlError):
        safe_fetch("https://example.com/redirect", client=client)


def test_trop_de_redirections_bloque():
    loop = FakeResponse(302, {"location": "https://example.com/loop", "content-type": "text/html"})
    client = FakeClient([loop] * 10)
    with pytest.raises(UnsafeUrlError):
        safe_fetch("https://example.com/loop", client=client)


def test_type_de_contenu_non_autorise():
    client = FakeClient([FakeResponse(200, {"content-type": "application/octet-stream"}, b"\x00\x01")])
    with pytest.raises(UnsafeUrlError):
        safe_fetch("https://example.com/bin", client=client)


def test_taille_de_reponse_plafonnee():
    big = b"A" * (600_000)
    client = FakeClient([FakeResponse(200, {"content-type": "text/html"}, big)])
    resp = safe_fetch("https://example.com/big", client=client, max_bytes=512_000)
    assert len(resp.content) <= 512_000
