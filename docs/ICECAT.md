# Guide Icecat — inscription Open Icecat (gratuit)

Vous étiez sur la page de connexion des produits Icecat (Global Catalog / Icecat Studio…) :
ce ne sont pas les bons points d'entrée. Suivez ce chemin :

## 1. Créer le compte gratuit « Open Icecat »

1. Aller sur **https://icecat.biz/en/register** (bouton « Sign up », PAS la page de login des applications) ;
2. Choisir le rôle **Content User** (vous consommez des fiches produits) ;
3. Type de compte : **Open Icecat — Free** (les offres payantes « Full Icecat » ne concernent pas ce projet au stade actuel) ;
4. Renseigner entreprise/email, valider, puis confirmer l'email ;
5. L'approbation peut prendre de quelques heures à 1-2 jours ouvrés.

## 2. Récupérer les identifiants

Une fois le compte approuvé : connexion sur **icecat.biz** → coin supérieur droit → **My Profile / Account**
→ onglet **Icecat Access** : vous y trouvez votre **username** et votre **password d'API**
(indépendant du mot de passe du site). C'est ce couple qui va dans le `.env` :

```
SDH_ICECAT_USERNAME=votre_username
SDH_ICECAT_PASSWORD=votre_password_api
```

## 3. Ce qu'Open Icecat apporte à Smart Deal Hunter

- Fiches produits normalisées par **GTIN/EAN ou référence fabricant** : nom officiel, marque,
  catégorie, images, caractéristiques → améliore l'autocomplétion, la correspondance (Top 5)
  et le remplissage automatique des références.
- Limite : seules les fiches **« Open » (sponsorisées par les marques)** sont gratuites ;
  beaucoup de produits de marque courants en font partie, pas tous.

## 4. Intégration prévue

Connecteur `icecat` à ajouter une fois vos identifiants reçus (recherche par GTIN/référence,
enrichissement des offres vérifiées). Prévu dans l'architecture actuelle : il s'ajoute comme
les autres connecteurs, sans impact sur le reste du moteur.

⚠️ À ne pas confondre : « Icecat Studio », « PIM », « Batavi » (visibles sur la capture) sont
des produits payants/séparés — aucun intérêt pour ce projet.
