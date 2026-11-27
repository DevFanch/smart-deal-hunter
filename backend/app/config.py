"""Configuration centrale. Aucune valeur sensible dans le code : tout vient de l'environnement."""
import os


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool) -> bool:
    v = os.environ.get(key)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, "").strip() or default)
    except ValueError:
        return default


class Settings:
    # API
    api_title: str = "Smart Deal Hunter API"
    # CORS : origines autorisées pour l'extension (chrome-extension://<id>)
    cors_origins: list[str] = [
        o.strip() for o in _env_str("SDH_CORS_ORIGINS", "").split(",") if o.strip()
    ]
    # Si aucune origine n'est configurée, l'API n'est pas exposée à des pages Web arbitraires
    cors_allow_all_dev: bool = _env_bool("SDH_CORS_ALLOW_ALL_DEV", False)

    # Recherche
    max_query_length: int = _env_int("SDH_MAX_QUERY_LENGTH", 160)
    search_timeout_s: float = _env_int("SDH_SEARCH_TIMEOUT_S", 12)
    verify_top_n: int = _env_int("SDH_VERIFY_TOP_N", 8)
    max_results_per_source: int = _env_int("SDH_MAX_RESULTS_PER_SOURCE", 10)

    # Serper.dev (Google Search) : gratuit jusqu'à épuisement du quota d'inscription
    # (2 500 requêtes offertes, sans carte bancaire). Sans clé : connecteur inactif.
    serper_api_key: str = _env_str("SDH_SERPER_API_KEY", "")
    serper_quota_total: int = _env_int("SDH_SERPER_QUOTA_TOTAL", 2500)

    # MaxMind GeoLite2 (GeoIP locale, gratuite avec licence) : si un chemin de
    # base valide est fourni, aucune dépendance réseau et aucune limite de débit.
    maxmind_account_id: str = _env_str("SDH_MAXMIND_ACCOUNT_ID", "")
    maxmind_license_key: str = _env_str("SDH_MAXMIND_LICENSE_KEY", "")
    geoip_db_path: str = _env_str("SDH_GEOIP_DB_PATH", "data/GeoLite2-Country.mmdb")

    # Icecat (Open Icecat, gratuit après inscription) : identifiants optionnels.
    icecat_username: str = _env_str("SDH_ICECAT_USERNAME", "")
    icecat_password: str = _env_str("SDH_ICECAT_PASSWORD", "")

    # Recherche approfondie (niveau 2, payant) : désactivée par défaut
    deep_search_enabled: bool = _env_bool("SDH_DEEP_SEARCH_ENABLED", False)
    deep_search_provider: str = _env_str("SDH_DEEP_SEARCH_PROVIDER", "")  # ex. "serpapi"
    deep_search_api_key: str = _env_str("SDH_DEEP_SEARCH_API_KEY", "")
    # Budget mensuel en EUR : 0 => aucun appel payant autorisé, jamais.
    monthly_budget_eur: float = float(_env_str("SDH_MONTHLY_BUDGET_EUR", "0") or 0)

    # Limites techniques
    max_response_bytes: int = _env_int("SDH_MAX_RESPONSE_BYTES", 512_000)
    fetch_timeout_s: float = _env_int("SDH_FETCH_TIMEOUT_S", 10)
    max_fetch_redirects: int = _env_int("SDH_MAX_FETCH_REDIRECTS", 4)

    # Rate limiting (par IP)
    rate_limit_requests: int = _env_int("SDH_RATE_LIMIT_REQUESTS", 10)
    rate_limit_window_s: int = _env_int("SDH_RATE_LIMIT_WINDOW_S", 60)

    # FX (BCE via frankfurter, gratuit)
    fx_api_url: str = _env_str("SDH_FX_API_URL", "https://api.frankfurter.dev/v1/latest")
    fx_cache_ttl_s: int = _env_int("SDH_FX_CACHE_TTL_S", 6 * 3600)

    # GeoIP : service gratuit optionnel (ip-api.com, 45 req/min, non commercial)
    geoip_enabled: bool = _env_bool("SDH_GEOIP_ENABLED", True)
    geoip_url: str = _env_str("SDH_GEOIP_URL", "http://ip-api.com/json/{ip}?fields=countryCode")
    geoip_cache_ttl_s: int = _env_int("SDH_GEOIP_CACHE_TTL_S", 3600)
    default_country: str = _env_str("SDH_DEFAULT_COUNTRY", "FR")


settings = Settings()
