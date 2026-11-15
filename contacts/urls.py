from django.urls import path

from . import views

urlpatterns = [
    path('', views.accueil, name='accueil'),
    path('gerer/', views.liste, name='liste'),
    path('choisir/', views.choisir, name='choisir'),
    path('manifest.json', views.app_manifest, name='app_manifest'),
    path('icon-<int:size>.png', views.app_icon, name='app_icon'),
    path('healthz/', views.healthz),
    path('connexion/', views.connexion, name='connexion'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),
    path('personne/nouvelle/', views.fiche, name='nouvelle'),
    path('personne/<int:pk>/', views.fiche, name='fiche'),
    path('personne/<int:pk>/photo/', views.relire_photo, name='relire_photo'),
    path('personne/<int:pk>/supprimer/', views.supprimer, name='supprimer'),
    # Pages d'appel : sans mot de passe, le jeton fait foi.
    path('a/<str:token>/', views.appel, name='appel'),
    path('a/<str:token>/manifest.json', views.manifest, name='manifest'),
    path('a/<str:token>/icon-<int:size>.png', views.icone, name='icone'),
]
