# Smart Deal Hunter

Extension Chrome (Manifest V3) + API Python : recherche multi-sources de produits, comparaison des prix, et recherche de fournisseurs/grossistes asiatiques. Recherche **gratuite par défaut** (aucune API payante, aucun abonnement, aucun crédit IA consommé automatiquement).

## Fonctionnement

1. L'utilisateur saisit uniquement le nom du produit (160 caractères max, saisie sécurisée).
2. L'extension appelle le backend, qui interroge plusieurs sources **gratuites** en parallèle :
   - **websearch** : moteurs de recherche publics via `ddgs` (Bing, DuckDuckGo, Yahoo) — sans clé API ;
   - **page_verify** : consulte réellement les pages candidates (protection SSRF, respect de robots.txt, extraction JSON-LD / Schema.org) → offres **vérifiées** ;
   - **wholesale** (case à cocher) : cible Alibaba, Made-in-China, DHgate, AliExpress, Global Sources via les moteurs publics — aucune suppression de protections anti-bot, MOQ et prix extraits uniquement quand réellement accessibles.
3. Deux sections strictement séparées :
   - **Top 5 — offres vérifiées** (page consultée à la source, horodatée) ;
   - **Autres pistes à vérifier** (site bloqué, CAPTCHA, robots.txt…) avec motif et lien direct.
4. Conversion des devises via les taux **BCE** (frankfurter.dev, gratuit), source et date affichées. Les frais de port sont affichés **CONFIRMÉ / ESTIMÉ / INCONNU** — jamais inventés.
5. Recherche approfondie (niveau 2, payante) : **désactivée par défaut**, verrouillée par un budget mensuel (`SDH_MONTHLY_BUDGET_EUR`, 0 = aucun appel payant).

## Démarrage rapide (bêta privée locale)

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Ou avec Docker :

```bash
cp .env.example .env   # compléter SDH_CORS_ORIGINS après l'étape 2
docker compose up --build -d
```

### 2. Extension

```bash
cd extension
npm install
npm run build
```

Si les icônes `extension/icons/icon*.png` sont absentes du dépôt (fichiers binaires non
poussés), les régénérer une fois : `python3 extension/icons/generate_icons.py`.

Puis dans Chrome :
1. Ouvrir `chrome://extensions` → activer **Mode développeur** ;
2. **Charger l'extension non empaquetée** → sélectionner le dossier `extension/` ;
3. Épingler l'icône et cliquer : le panneau latéral s'ouvre ;
4. Copier l'ID de l'extension (chrome://extensions) puis renseigner `SDH_CORS_ORIGINS=chrome-extension://<ID>` dans `.env` et redémarrer le backend ;
5. Lancer une recherche (ex. `Nike Air Max 90`).

> Le backend est préconfiguré dans l'extension sur `http://localhost:8000`. Pour un backend distant (VPS), changer l'URL dans ⚙ Préférences **et** ajouter l'origine du backend dans `host_permissions` de `manifest.json` puis recharger l'extension.

## Déploiement VPS (HTTPS)

Le service n'est **jamais** exposé tel quel : `docker-compose.yml` lie le port uniquement sur `127.0.0.1`. Placer un reverse proxy HTTPS devant (exemple Caddy) :

```
sdh.exemple.fr {
    reverse_proxy 127.0.0.1:8000
    header Strict-Transport-Security "max-age=31536000"
}
```

Restrictions complémentaires recommandées : authentification basique au niveau du proxy pendant la bêta privée, `SDH_CORS_ORIGINS` strict, rate limiting déjà actif (10 req/min/IP par défaut).

Mise à jour : `git pull && docker compose up --build -d`.

## Publication Chrome Web Store (si nécessaire)

1. Renseigner l'URL du backend dans `manifest.json` → `host_permissions` ;
2. `npm run build` ; zipper le contenu du dossier `extension/` (manifest.json à la racine du zip) ;
3. Créer un compte développeur Chrome Web Store (frais Google ponctuels) et soumettre le zip avec une fiche déclarant : aucune collecte de données utilisateur hors pays de destination approximatif, aucune exécution de code distant.

## Coûts

| Service | Coût |
|---|---|
| Recherche web (ddgs/Bing public) | 0 € |
| Taux de change BCE (frankfurter.dev) | 0 € |
| GeoIP (ip-api.com, usage non commercial) | 0 € (45 req/min) |
| Services payants optionnels | 0 € par défaut (budget = 0) |

Coût estimé : **0 € pour 100 et 1 000 recherches** en configuration par défaut.

## Tests

```bash
cd backend && python -m pytest tests/ -v
cd ../extension && npm run typecheck && npm run build
```

## Documentation

- [Faisabilité des sources](docs/FAISABILITE.md)
- [Sécurité](docs/SECURITE.md)
- [Rapport final](docs/RAPPORT_FINAL.md)

## Limites connues (transparence)

- Les gros marchands (Decathlon, Snowleader, etc.) bloquent les agents automatisés : leurs offres apparaissent en **pistes à vérifier**, pas en offres vérifiées. C'est voulu : aucun contournement de protections anti-bot.
- `ddgs` est un accès non officiel : il peut être temporairement limité ; la recherche continue avec les autres backends et signale les erreurs.
- Les frais de port exacts par destination nécessitent des API marchands payantes : ils sont affichés INCONNU avec coût partiel signalé.
- Les API officielles des marketplaces (Alibaba, Amazon…) exigent une inscription partenaire : non intégrées en niveau 1, prévues comme connecteurs optionnels (niveau 2).
