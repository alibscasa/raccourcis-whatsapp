# Raccourcis WhatsApp

Une icône par personne sur l'écran d'accueil du téléphone, avec sa photo : un appui lance l'appel WhatsApp.

## Comment ça marche

1. Dans l'écran de gestion (protégé par mot de passe), on ajoute un nom et un numéro.
   La photo de profil WhatsApp est lue via Green API (`getAvatar`) ; on peut aussi importer une photo.
2. « Mettre l'icône sur ce téléphone » ouvre la page de la personne, avec la marche à suivre
   (Safari → Partager → Sur l'écran d'accueil ; Chrome → ⋮ → Ajouter à l'écran d'accueil).
   « Envoyer le lien » sert à installer l'icône sur un autre téléphone.
3. Un appui sur l'icône ouvre la page et lance l'action choisie :
   appel WhatsApp (`wa.me/call/<numéro>`), discussion WhatsApp ou appel téléphonique.

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
