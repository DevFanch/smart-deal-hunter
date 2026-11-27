import pytest

from app.security.input_sanitizer import QueryRejected, sanitize_query, sanitize_optional


def test_requete_simple_acceptee():
    assert sanitize_query("Nike Air Max 90").value == "Nike Air Max 90"


def test_references_commerciales_conservees():
    kept = "Bosch 0125812015 / 0 258 012-015 (OEM #12) + 'Super' 50%"
    assert sanitize_query(kept).value == kept


def test_balise_script_rejetee():
    with pytest.raises(QueryRejected):
        sanitize_query("<script>alert(1)</script>")


def test_balise_img_onerror_rejetee():
    with pytest.raises(QueryRejected):
        sanitize_query("<img src=x onerror=alert(1)>")


def test_javascript_uri_rejete():
    with pytest.raises(QueryRejected):
        sanitize_query("javascript:alert(1)")


def test_data_uri_rejete():
    with pytest.raises(QueryRejected):
        sanitize_query("data:text/html;base64,PHNjcmlwdD4=")


def test_caracteres_de_controle_supprimes():
    result = sanitize_query("Nike\x00 Air\x0b Max\x7f 90")
    assert result.value == "Nike Air Max 90"


def test_normalisation_unicode():
    assert sanitize_query("Pégéot  208 GTi").value == "Pégéot 208 GTi"


def test_trop_long_rejete():
    with pytest.raises(QueryRejected):
        sanitize_query("a" * 161)


def test_limite_exacte_acceptee():
    assert sanitize_query("a" * 160).value == "a" * 160


def test_union_sql_ne_provoque_pas_erreur_de_traitement():
    # Sans base SQL et en traitement de données, cette chaîne est simplement une donnée
    result = sanitize_query("chaussures running 42 prix - ou dupré")
    assert "chaussures" in result.value


def test_champ_facultatif_vide_ne_bloque_pas():
    assert sanitize_optional("") is None
    assert sanitize_optional(None) is None


def test_champ_facultatif_malveillant_rejete():
    with pytest.raises(QueryRejected):
        sanitize_optional("<iframe src=javascript:x>")


def test_apostrophe_et_slash_conserves():
    assert sanitize_query("Veste homme d'été 3/4").value == "Veste homme d'été 3/4"
