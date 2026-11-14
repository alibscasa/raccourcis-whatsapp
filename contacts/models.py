import secrets

from django.db import models


def _new_token():
    return secrets.token_urlsafe(16)


class Contact(models.Model):
    """Une personne à joindre en un appui depuis l'écran d'accueil du téléphone.

    La page /a/<token>/ s'ajoute à l'écran d'accueil : son icône est la photo et
    son ouverture lance l'action choisie. Le jeton tient lieu d'accès, une icône
    d'écran d'accueil n'ayant pas de session.
    """
    CALL, CHAT, PHONE = 'call', 'chat', 'tel'
    ACTIONS = [
        (CALL, 'Appel WhatsApp'),
        (CHAT, 'Discussion WhatsApp'),
        (PHONE, 'Appel téléphone'),
    ]
    name = models.CharField(max_length=60)
    # Format international sans « + » ni espaces (ex. 212661234567).
    phone = models.CharField(max_length=15, unique=True)
    action = models.CharField(max_length=4, choices=ACTIONS, default=CALL)
    token = models.CharField(max_length=32, unique=True, default=_new_token, editable=False)
    # Photo carrée 512 px en JPEG, gardée en base (le disque des hébergeurs est éphémère).
    photo = models.BinaryField(null=True, blank=True, editable=False)
    photo_source = models.CharField(max_length=10, blank=True)  # 'whatsapp' | 'import'
    version = models.PositiveIntegerField(default=1)  # change → les icônes en cache sont refaites
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} (+{self.phone})'

    @property
    def first_name(self):
        parts = self.name.split()
        return parts[0] if parts else self.name

    @property
    def pretty_phone(self):
        return f'+{self.phone}'

    def url_for(self, action):
        if action == self.PHONE:
            return f'tel:+{self.phone}'
        if action == self.CHAT:
            return f'https://wa.me/{self.phone}'
        return f'https://wa.me/call/{self.phone}'

    @property
    def action_url(self):
        return self.url_for(self.action)

    @property
    def other_actions(self):
        return [(label, self.url_for(code)) for code, label in self.ACTIONS if code != self.action]
