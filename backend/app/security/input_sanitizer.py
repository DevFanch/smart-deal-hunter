"""Sécurisation de la saisie produit.

Principes :
- le texte saisi est une DONNÉE, jamais du code ;
- protection en couches : normalisation Unicode, suppression des caractères de
  contrôle, analyse syntaxique HTML (html.parser, pas seulement une regex),
  liste blanche de catégories Unicode, vérification de schémas d'URL dangereux ;
- les caractères utiles aux références commerciales sont conservés :
  - . / ' ( ) + # & % : ; , ! ? ainsi que tirets et chiffres.
"""
import html.parser
import unicodedata
from dataclasses import dataclass

MAX_LENGTH = 160

# Schémas d'URL interdits dans une requête (jamais légitimes dans un nom de produit)
DANGEROUS_SCHEMES = ("javascript:", "data:", "vbscript:", "file:", "about:")

# Catégories Unicode autorisées
_ALLOWED_CATEGORIES = ("L", "N", "Z", "P", "S")


class QueryRejected(ValueError):
    """Requête refusée (raison compréhensible, sans écho du contenu)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class _MarkupDetector(html.parser.HTMLParser):
    """Détecte toute tentative d'injection de balisage, en parsing réel et non en regex seule."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.markup_found = False
        self.tag_names: list[str] = []

    def _flag(self, tag: str) -> None:
        self.markup_found = True
        self.tag_names.append(tag.lower())

    def handle_starttag(self, tag, attrs):
        self._flag(tag)
        for _, value in attrs:
            if value and value.strip().lower().startswith(DANGEROUS_SCHEMES):
                self.markup_found = True

    def handle_startendtag(self, tag, attrs):
        self._flag(tag)

    def handle_decl(self, decl):
        self.markup_found = True

    def handle_pi(self, data):
        self.markup_found = True


def _contains_dangerous_scheme(text_lower: str) -> bool:
    return any(s in text_lower for s in DANGEROUS_SCHEMES)


def _strip_controls(text: str) -> str:
    """Supprime caractères de contrôle et de formatage invisibles (Cc, Cf, Cs, Co, Cn)."""
    cleaned = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith(("C", "Sk")) and ch != "\n":
            continue
        cleaned.append(ch)
    return "".join(cleaned)


@dataclass
class SanitizeResult:
    value: str
    warnings: list[str]


def sanitize_query(raw: str, max_length: int = MAX_LENGTH) -> SanitizeResult:
    """Valide et neutralise une requête utilisateur. Lève QueryRejected si malveillante."""
    if raw is None:
        raise QueryRejected("requête vide")
    warnings: list[str] = []

    # 1. Normalisation Unicode canonique
    text = unicodedata.normalize("NFC", str(raw))

    # 2. Suppression des caractères de contrôle
    text = _strip_controls(text)

    # 3. Collapsing des espaces
    text = " ".join(text.split()).strip()

    if not text:
        raise QueryRejected("requête vide")

    # 4. Longueur maximale
    if len(text) > max_length:
        raise QueryRejected(f"requête trop longue (max {max_length} caractères)")

    # 5. Analyse HTML réelle : toute balise, déclaration ou instruction de
    #    traitement détectée => rejet (protection XSS de premier niveau)
    detector = _MarkupDetector()
    detector.feed(text)
    if detector.markup_found:
        raise QueryRejected("balisage HTML interdit dans la recherche")

    # 6. Schémas d'URL dangereux
    lowered = text.lower()
    if _contains_dangerous_scheme(lowered):
        raise QueryRejected("contenu de type code/URL exécutable interdit")

    # 7. Liste blanche de catégories Unicode : on refuse uniquement ce qui n'a
    #    aucune utilité dans une désignation produit (math=<>, symboles divers…)
    result_chars = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith(_ALLOWED_CATEGORIES):
            if ch in "<>":
                raise QueryRejected("caractères interdits")
            result_chars.append(ch)
        else:
            warnings.append("caractères non autorisés supprimés")
    text = "".join(result_chars).strip()
    if not text:
        raise QueryRejected("requête vide après nettoyage")

    return SanitizeResult(value=text, warnings=warnings)


def sanitize_optional(value: str | None, max_length: int = 80) -> str | None:
    """Valide un champ de filtre facultatif (marque, modèle, couleur, taille…).

    Ne bloque jamais la recherche si le champ est vide. Refuse le contenu
    malveillant exactement comme la requête principale.
    """
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    res = sanitize_query(value, max_length=max_length)
    return res.value
