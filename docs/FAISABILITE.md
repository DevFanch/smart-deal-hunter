# Faisabilité des sources (vérifiée le 2025-11-27 depuis l'environnement de développement)

| Source | Usage | Accès gratuit | Statut testé | Limites |
|---|---|---|---|---|
| `ddgs` (Bing / DuckDuckGo / Yahoo publics) | Recherche web niveau 1 | Oui, sans clé | ✅ OK (intermittent : limitations temporaires possibles) | Accès non officiel, résultats variables |
| Consultation directe pages + JSON-LD Schema.org | Vérification offres | Oui (GET public) | ✅ OK sur sites accessibles | 403/anti-bot sur grands marchands (Decathlon, Snowleader testés) → pistes |
| frankfurter.dev (BCE) | Taux de change | Oui, sans clé | ✅ OK | ECB : jours ouvrés, ~20 devises |
| ip-api.com | GeoIP approximative | Oui non-commercial | ✅ OK | 45 req/min, pas d'usage commercial sans licence |
| Alibaba / Made-in-China / Global Sources | API officielles grossistes | Non : inscription partenaire | ❌ Non intégrées | Clé obligatoire ; prévu en connecteur niveau 2 |
| Alibaba / DHgate / AliExpress (scraping direct) | — | — | ❌ Refusé | CGU interdisent l'automatisation + anti-bot : jamais contourné |
| Amazon Product Advertising API | Marketplace | Non : affiliation requise | ❌ Non intégré | Nécessite compte affilié validé |
| SerpAPI / Brave / Mojeek API | Recherche niveau 2 | Payant / clé | ⏸ Optionnel | Intégration prévue derrière budget |

## Décisions

1. **Niveau 1 = 100 % gratuit** : moteurs publics + consultation directe + robots.txt respecté.
2. Les plateformes B2B asiatiques sont ciblées via les moteurs publics (`site:`) : on ne scrape pas leurs sites. Les résultats sont des **pistes** sauf page effectivement consultable.
3. Les frais de port exacts nécessiteraient des API marchands : affichés CONFIRMÉ/ESTIMÉ/INCONNU, jamais inventés.
4. La recherche approfondie (niveau 2) reste une interface prête mais **sans aucun service payant branché** tant qu'aucun budget n'est explicitement configuré.

## Mise à jour 2026-11-27 — sources à clé gratuite ajoutées

| Source | Statut |
|---|---|
| Serper.dev (2 500 requêtes offertes, sans CB) | ✅ Connecteur `serper` intégré — actif uniquement si clé présente ; coupure automatique à l'épuisement du quota (aucune facturation possible) |
| MaxMind GeoLite2 (compte gratuit + license key) | ✅ GeoIP locale intégrée (base téléchargée via `backend/scripts/download_geolite.py`, .mmdb hors dépôt) ; ip-api reste en secours |
| Open Icecat | ⏳ En attente d'identifiants utilisateur (guide : docs/ICECAT.md) |
| Bing Search API | ❌ Retirée le 11/08/2025 (l'interrogation publique via ddgs reste indépendante) |
| Google Custom Search JSON API | ❌ Fermé aux nouveaux clients, fin prévue 01/01/2027 |
