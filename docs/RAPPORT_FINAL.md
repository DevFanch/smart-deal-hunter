# RAPPORT FINAL — Smart Deal Hunter MVP (bêta privée)

Date : 2025-11-27 · État Git : dépôt local initialisé, commit initial du MVP.

## 1. Architecture retenue

```
Extension Chrome MV3 (TypeScript + esbuild, zéro dépendance runtime)
   │  POST /api/search (JSON strict, CORS limité à l'origine de l'extension)
   ▼
API FastAPI (backend/app/main.py)
   ├─ Sécurité : input_sanitizer, SSRF guard, rate limiter
   ├─ Orchestrator : exécution concurrente des connecteurs
   │    ├─ websearch    (ddgs : Bing/DuckDuckGo/Yahoo publics, sans clé)
   │    ├─ wholesale    (cible B2B via moteurs publics, jamais de scraping direct)
   │    └─ page_verify  (fetch sûr + JSON-LD Schema.org → offres vérifiées)
   ├─ Normalizer (correspondance, prix, MOQ, condition, pays — déterministe)
   ├─ Ranker (correspondance > coût livré > fiabilité > dispo > fraîcheur)
   └─ FX (BCE/frankfurter) + GeoIP (ip-api, optionnel)
```

Justifications : pas de Redis/Celery/Kafka/PostgreSQL (SQLite non encore nécessaire : aucun état persistant requis au stade bêta) ; 4 dépendances runtime seulement (fastapi, uvicorn, httpx, ddgs) ; un connecteur défaillant n'arrête jamais la recherche (testé).

## 2. Fichiers créés

- **Backend** : `backend/app/main.py`, `config.py`, `fx.py`, `geo.py`, `security/{input_sanitizer,ssrf,rate_limit}.py`, `search/{models,normalizer,query_builder,ranker,orchestrator}.py`, `search/connectors/{base,websearch,page_verify,wholesale}.py`
- **Tests** : `backend/tests/test_{sanitizer,ssrf,normalizer,ranker,orchestrator,api}.py` — **54 tests, tous passés**
- **Extension** : `extension/{manifest.json,sidepanel.html,sidepanel.css,build.mjs,tsconfig.json,package.json}`, `extension/src/{sidepanel,api,sanitize,types,background}.ts`, `icons/` ; bundle construit (`dist/`) et typecheck strict OK
- **Déploiement** : `Dockerfile` (backend), `docker-compose.yml` (port lié sur 127.0.0.1, conteneur non-root read-only), `.env.example`, `.gitignore`
- **Docs** : `README.md`, `docs/FAISABILITE.md`, `docs/SECURITE.md`, `docs/RAPPORT_FINAL.md`

## 3. Connecteurs et sources

| Connecteur | Statut |
|---|---|
| websearch (ddgs/Bing…) | **Fonctionnel et testé** (accès non officiel, limitations temporaires possibles — gérées) |
| page_verify (JSON-LD/Schema.org) | **Fonctionnel et testé** (offre réelle extraite : prix 1 199 EUR sur coolblue.nl, horodatage, pays vendeur NL, correspondance évaluée) |
| wholesale | **Fonctionnel et testé** (19 pistes B2B détectées, MOQ/prix extraits quand présents, contrefaçons exclues par règle) |
| fx (BCE) | **Fonctionnel et testé** (USD 1,0975 / GBP 0,8376, source horodatée) |
| geoip | **Fonctionnel et testé** (défaut FR, IP privée → défaut sans appel réseau) |
| API Alibaba/Made-in-China/Global Sources/Amazon PA-API | **Bloqué par service externe** : inscription partenaire payante/approuvée requise — prévu comme connecteur niveau 2 |

## 4. Tests exécutés (réels, données à la source)

| Test | Résultat |
|---|---|
| 1. Chaussures (Nike Air Max 90, EU 42) | ✅ mécanique complète ; 6 résultats détectés, tous 403/robots.txt → 6 pistes motivées (Zalando, Amazon…). 0 offre vérifiée : les grands sites sneakers bloquent les bots — comportement voulu |
| 2. Vêtements (Patagonia Torrentshell M) | ✅ 8 résultats détectés ; patagonia.com en page de maintenance (vérifié à la source) → pistes |
| 3. Automobile (réf. Bosch 0125812015) | ✅ recherche par référence en tête ; 3 pages consultées vérifiées, produits non correspondants correctement marqués `approximative`/`non_confirmee` (compatibilité jamais annoncée sans preuve) |
| 4. Électronique (Lenovo IdeaPad 3 82H8003NMH) | ✅ 5 détectés, pages amazon/lenovo consultées mais sans prix exploitable → requalifiées pistes avec motif ; offre vérifiée réelle démontrée sur coolblue.nl via le connecteur de vérification |
| 5. Grossistes (sneakers génériques ×12) | ✅ 19 pistes B2B (Alibaba, DHgate, grossistes), avertissement commercial affiché, MOQ extrait quand présent |
| 6. Sécurité | ✅ `<script>`, `<img onerror>`, `javascript:` → 422 ; caractères de contrôle → neutralisés ; trop long → 422 ; SSRF privé/localhost/redirection vers privé → bloqué (tests automatisés) |

Métriques observées : 2,3–15 s par recherche (limité par l'limitation des moteurs publics et les timeouts marchands), erreurs isolées sans échec global.

## 5. Sécurité (tests automatisés + revue)

- Saisie : parsing HTML réel (pas qu'une regex), schémas dangereux, contrôles, 160 max, whitelist Unicode — 13 tests.
- SSRF : schémas, loopback/privé/link-local, identifiants, port non standard, DNS inexistant, redirection vers privé, boucle de redirections, type de contenu, plafond de taille — 9 tests.
- API : rejet 422 sans écho du contenu, rate limiting testé.
- Extension : permissions minimales (`storage`), aucune navigation ni code distant, rendu via `textContent`, liens `noopener noreferrer nofollow`.
- Déploiement : port 127.0.0.1 uniquement, HTTPS à déléguer au reverse proxy (procédure README).

## 6. Coûts

| Service | Coût réel | 100 recherches | 1 000 recherches |
|---|---|---|---|
| ddgs (moteurs publics) | 0 € | 0 € | 0 € |
| frankfurter.dev (BCE) | 0 € | 0 € | 0 € |
| ip-api.com | 0 € (non commercial, 45 req/min) | 0 € | 0 € |
| Services payants optionnels | désactivés, budget 0 € | 0 € | 0 € |

Plafond mensuel configurable ; budget 0 = aucun appel payant possible (vérifié par construction : aucun connecteur payant branché).

## 7. Déploiement

1. `cp .env.example .env` → renseigner `SDH_CORS_ORIGINS` ;
2. Backend : `docker compose up --build -d` ou `uvicorn app.main:app --port 8000` ;
3. Extension : `cd extension && npm install && npm run build` puis chrome://extensions → charger `extension/` (procédure détaillée dans le README, y compris publication Web Store).

## 8. État des fonctionnalités

**Fonctionnel et testé** : recherche avec seul nom de produit ; multi-sources ; séparation offres vérifiées / pistes avec motifs ; classement (correspondance d'abord, coût livré ensuite, jamais d'offre sans frais comme moins chère) ; devise commune + devise originale ; sanitisation et SSRF ; rate limiting ; mode grossistes + MOQ + quantités + avertissements ; GeoIP par défaut + sélecteur de pays ; filtres dynamiques par catégorie ; interface side panel complète ; API de métadonnées.

**Fonctionnel mais non testé en réel** : build Docker (démon indisponible dans l'environnement — syntaxe standard, à valider sur le VPS) ; publication Web Store.

**Partiellement fonctionnel** : frais de port (statuts CONFIRMÉ/ESTIMÉ/INCONNU implémentés ; aucune source gratuite fiable par destination → INCONNU + coût partiel signalé, conforme au cahier des charges) ; autocomplétion (liste blanches locales déterministes côté extension, pas de référentiel externe encore).

**Non implémenté (assumé)** : connecteurs payants (niveau 2 : interface et budget prêts, aucun service branché) ; persistance SQLite (inutile au stade bêta) ; conversions de pointures EU/US/UK (listes fournies, conversion non automatisée — exigence de prudence des grilles par marque).

**Bloqué par service externe** : API officielles Alibaba/Amazon (inscription partenaire) ; consultation directe des grands marchands (anti-bot/403, contournement refusé).

## 9. Risques connus

1. `ddgs` est un accès non officiel : risque d'indisponibilité prolongée → mitigé par multi-backends et signalement d'erreur ; alternative long terme : clé API gratuite Mojeek/Brave (documentée niveau 2).
2. Taux d'offres vérifiées faible sur produits de marque (anti-bot généralisé) : le produit assume d'afficher des pistes plutôt que de mentir.
3. Un seul utilisateur à la fois par instance (rate limit en mémoire) : prévoir Redis uniquement si bêta publique.

## 10. Validation du cahier des charges

Recherche libre ✅ · Filtres par catégorie ✅ · Sécurité saisie ✅ (testée) · Multi-sources ✅ · Pistes conservées ✅ · Vérification à la source ✅ (testée sur site accessible) · Classement explicite ✅ (tests) · Livraison CONFIRMÉ/ESTIMÉ/INCONNU ✅ (jamais inventée) · Grossistes/MOQ ✅ (quand accessibles) · Coûts ✅ (0 € par défaut) · Extension installable ✅ (build OK) · Backend déployable ✅ · Tests automatisés ✅ (54 passés).
