# Guide MaxMind GeoLite2 — clé de licence gratuite

## Le problème visible sur votre capture

Le message « Your account doesn't have access to this page. This page requires a
MaxMind service that your account doesn't include » apparaît quand on ouvre une page
d'un service **payant** (GeoIP2 Insights, minFraud, GeoIP2 Precision…).
Ces services ne nous concernent pas : nous utilisons **GeoLite2**, la base gratuite.

## Chemin exact (portail actuel)

1. Se connecter sur **https://www.maxmind.com/en/account** ;
2. Dans le menu latéral gauche, section **Account**, ouvrir :
   **https://www.maxmind.com/en/accounts/current/license-key**
   (libellé du menu : **Manage License Keys**) ;
3. Cliquer **Generate new license key** ;
4. Choisir le type **geoip-update** ou **geoip-api** (les deux permettent le
   téléchargement GeoLite2 ; « geoip-update » suffit pour le script du projet) ;
5. ⚠️ La clé n'est affichée **qu'une seule fois** : la copier immédiatement.

## Si le menu « Manage License Keys » n'apparaît pas

Cela signifie que le service GeoLite2 n'a pas encore été activé sur le compte :

1. Aller sur **https://www.maxmind.com/en/accounts/current/geolite2/signup**
   (ou menu latéral **GeoLite2 → Get Started**) ;
2. Renseigner « Industry » et « Intended use » (ex. `eCommerce Platform`,
   `Content customization`) ;
3. Accepter le contrat GeoLite2 EULA ;
4. Le menu **Manage License Keys** devient disponible ensuite.

## Renseigner le `.env` à la racine du projet

```
SDH_MAXMIND_ACCOUNT_ID=123456        (Account → Account Information : « Your account ID »)
SDH_MAXMIND_LICENSE_KEY=coller_ici
```

## Télécharger la base

Depuis la racine du projet :

```bash
python3 backend/scripts/download_geolite.py
```

Le fichier `GeoLite2-Country.mmdb` est extrait dans `backend/data/`
(exclu de Git). La géolocalisation locale devient prioritaire ; en son absence,
le fallback `ip-api.com` reste actif — le moteur fonctionne dès maintenant sans clé.

## Quotas gratuits GeoLite2

- Téléchargements de bases : ~30 / 24 h par compte ;
- Lookups web service GeoLite2 : 1 000 / jour / service ;
- Le projet lit la base **localement** : aucun quota réseau consommé.
