# Raccourcis WhatsApp

Une icône par personne sur l'écran d'accueil du téléphone, avec sa photo : un appui lance l'appel WhatsApp.

## Comment ça marche

Tout se fait depuis le téléphone, derrière un mot de passe unique.

1. **Choisir les personnes** : « Gérer » → « Choisir dans mes contacts WhatsApp » liste les contacts du
   compte relié à Green API (`getContacts`) ; on coche, la photo de profil de chacun est lue (`getAvatar`).
   On peut aussi saisir un numéro à la main et importer une photo.
2. **Appeler** : la page d'accueil est une grille de photos ; un appui sur une photo lance l'action de la
   personne : appel WhatsApp (`wa.me/call/<numéro>`), discussion WhatsApp ou appel téléphonique.
3. **Sur l'écran d'accueil du téléphone** : ajouter la page d'accueil (une seule icône « Appels »), ou
   une icône à part par personne (« Gérer » → « Icône à part sur l'écran d'accueil »).

Les pages d'appel (`/a/<jeton>/`) s'ouvrent sans mot de passe : c'est le jeton, impossible à deviner, qui protège.
Retirer une personne désactive son icône.

## Réglages (variables d'environnement)

| Variable | Rôle |
| --- | --- |
| `SECRET_KEY` | Longue chaîne aléatoire (obligatoire). |
| `APP_PASSWORD` | Mot de passe de l'écran de gestion (obligatoire). |
| `GREENAPI_INSTANCE`, `GREENAPI_TOKEN` | Identifiants de l'instance Green API. |
| `DATABASE_URL` | Base Postgres. Sans elle : fichier SQLite local. |
| `COUNTRY_PREFIX` | Indicatif des numéros saisis en 06… (défaut `212`). |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | À renseigner avec un domaine personnalisé. |

## Mise en ligne

**Render, en un clic** : ouvrir
https://render.com/deploy?repo=https://github.com/alibscasa/raccourcis-whatsapp
puis saisir `APP_PASSWORD`, `GREENAPI_INSTANCE` et `GREENAPI_TOKEN`. Le fichier `render.yaml`
crée le service, génère `SECRET_KEY` et range les données dans un fichier SQLite sur disque persistant.

**Railway** : créer un service à partir de ce dépôt, lui ajouter une base Postgres et saisir les
variables ci-dessus. Le `Procfile` applique les migrations puis démarre gunicorn.

## En local

```
pip install -r requirements.txt
DEBUG=1 APP_PASSWORD=demo python manage.py migrate
DEBUG=1 APP_PASSWORD=demo python manage.py runserver
DEBUG=1 python manage.py test
```
