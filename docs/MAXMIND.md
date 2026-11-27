# Guide MaxMind GeoLite2 — clé de licence gratuite

## Pourquoi vous voyez « Your account doesn't have access to this page »

Créer un compte MaxMind ne donne PAS accès à GeoLite. MaxMind le dit
explicitement : « Creating an account does not give you immediate access to
GeoLite ». Il faut d'abord **s'inscrire au service GeoLite** depuis le portail.
Le message d'erreur s'affiche aussi quand on ouvre une page d'un service
**payant** (GeoIP2, minFraud…) : ces services ne nous concernent pas.

## Étape 1 — S'inscrire au service GeoLite (obligatoire, gratuit)

1. Être connecté sur MaxMind ;
2. Ouvrir : **https://www.maxmind.com/en/geolite2/signup** ;
3. Renseigner « Industry » et « Intended use » (ex. `eCommerce Platform`,
   `Content customization`) ;
4. Accepter le contrat GeoLite EULA ;
5. Le service GeoLite est alors rattaché au compte.

Si la page renvoie vers un formulaire de connexion, se connecter puis revenir :
l'inscription au service se fait depuis le portail de compte.

## Étape 2 — Générer la clé de licence

1. Ouvrir : **https://www.maxmind.com/en/accounts/current/license-key**
   (menu latéral **Account → Manage License Keys**) ;
2. Cliquer **Generate new license key** ;
3. Choisir le type **geoip-update** (suffit pour télécharger GeoLite2) ;
4. ⚠️ La clé n'est affichée **qu'une seule fois** : la copier immédiatement ;
5. L'ID numérique du compte est dans **Account → Account Information**.

## Étape 3 — Renseigner le `.env` à la racine du projet

```
SDH_MAXMIND_ACCOUNT_ID=123456        (Account → Account Information : « Your account ID »)
SDH_MAXMIND_LICENSE_KEY=coller_ici
```

## Étape 4 — Télécharger la base

Depuis la racine du projet :

```bash
python3 backend/scripts/download_geolite.py
```

Le fichier `GeoLite2-Country.mmdb` est extrait dans `backend/data/`
(exclu de Git, licence MaxMind). La géolocalisation locale devient prioritaire.

## Le projet fonctionne sans MaxMind

En l'absence de base locale, le fallback `ip-api.com` (gratuit, non commercial)
prend le relais : aucun test ni fonctionnalité n'est bloqué par cette étape.

## Quotas gratuits GeoLite2

- Téléchargements de bases : 30 / 24 h par compte ;
- Lookups web service GeoLite2 : 1 000 / jour / service ;
- Le projet lit la base **localement** : aucun quota réseau consommé ;
- EULA : supprimer les bases de plus de 30 jours (mettre à jour régulièrement).
