# Sécurité — Smart Deal Hunter

## Saisie utilisateur
- Normalisation Unicode NFC, suppression des caractères de contrôle (Cc/Cf/Sk), collapsing des espaces, plafond 160 caractères.
- Détection de balisage par **parsing HTML réel** (`html.parser`), pas uniquement une regex : toute balise, déclaration ou PI → rejet.
- Schémas dangereux (`javascript:`, `data:`, `vbscript:`, `file:`, `about:`) → rejet.
- Liste blanche de catégories Unicode conservant les caractères utiles aux références commerciales (`- . / ' ( ) + # & % : ; ,`…).
- Double validation : extension (sanitize.ts) **et** backend (input_sanitizer.py). Raison de rejet générique, sans écho du contenu.
- Toute donnée marchande affichée dans l'extension l'est via `textContent` (jamais `innerHTML`) ; liens en `rel="noopener noreferrer nofollow"`.

## Récupération de pages (anti-SSRF)
- Seuls http/https, ports 80/443, pas d'identifiants dans l'URL.
- Résolution DNS vérifiée pour **chaque IP** : privées, loopback, link-local, réservées, multicast, non-globales rejetées.
- Redirections suivies **manuellement** et revalidées à chaque saut (anti DNS-rebinding à chaque hop), max 4 sauts.
- Réponses plafonnées (512 Ko), timeout 10 s, types de contenu limités (texte/JSON/JSON-LD).
- robots.txt consulté et respecté ; interdiction explicite = piste, jamais de contournement.
- Jamais d'exécution de code ni de rendu HTML des pages marchandes côté extension.

## API et déploiement
- Rate limiting fenêtre glissante (10 req/min/IP par défaut) sur `/api/*`.
- CORS strict : uniquement l'origine `chrome-extension://<ID>` déclarée ; mode permissif réservé au dev (`SDH_CORS_ALLOW_ALL_DEV`).
- Backend lié sur `127.0.0.1` dans Docker Compose, conteneur non-root, `read_only`, `no-new-privileges`, HTTPS délégué au reverse proxy.
- Secrets uniquement via variables d'environnement (`.env` hors dépôt, `.env.example` fourni). Aucune clé API requise en niveau 1.
- Logs sans données personnelles ; IP utilisée uniquement pour l'approximation pays, non stockée (clé hachée en cache mémoire court).

## RGPD
- Aucune donnée personnelle collectée : pas de compte, pas de tracking, pas d'IP persistée.
- Données transmises aux tiers : requête produit → moteur public, pays → ip-api.com (optionnel), montant → frankfurter.dev.
- Permissions Chrome minimales : `storage` (préférences locales) + host_permissions limitées au backend configuré. Aucun accès aux pages visitées.
