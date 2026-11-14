import io
import json
from unittest import mock

from django.test import TestCase, override_settings
from PIL import Image

from . import services
from .models import Contact


def _jpeg(size=(800, 600)):
    out = io.BytesIO()
    Image.new('RGB', size, '#336699').save(out, 'JPEG')
    return out.getvalue()


class PhoneTests(TestCase):
    def test_normalize(self):
        n = services.normalize_phone
        self.assertEqual(n('06 61 23 45 67'), '212661234567')
        self.assertEqual(n('+212 661-234567'), '212661234567')
        self.assertEqual(n('00212661234567'), '212661234567')
        self.assertEqual(n('+33 6 12 34 56 78'), '33612345678')
        self.assertIsNone(n('123'))
        self.assertIsNone(n(''))


@override_settings(APP_PASSWORD='secret', GREENAPI_INSTANCE='7107000000', GREENAPI_TOKEN='t',
                   GREENAPI_URL='https://7107.api.greenapi.com')
class AppTests(TestCase):
    def login(self):
        self.client.post('/connexion/', {'password': 'secret'})

    def test_gestion_needs_password(self):
        self.assertRedirects(self.client.get('/'), '/connexion/')
        self.assertRedirects(self.client.get('/personne/nouvelle/'), '/connexion/')
        r = self.client.post('/connexion/', {'password': 'faux'})
        self.assertContains(r, 'incorrect')
        self.login()
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_create_reads_whatsapp_photo(self):
        self.login()
        api = mock.Mock(status_code=200, json=lambda: {'urlAvatar': 'https://pps.whatsapp.net/x.jpg'})
        img = mock.Mock(content=_jpeg(), raise_for_status=lambda: None)
        with mock.patch('contacts.services.requests.post', return_value=api) as post, \
                mock.patch('contacts.services.requests.get', return_value=img):
            r = self.client.post('/personne/nouvelle/', {'name': 'Hind B', 'phone': '06 61 23 45 67',
                                                         'action': 'call'})
        self.assertRedirects(r, '/')
        self.assertEqual(post.call_args.kwargs['json'], {'chatId': '212661234567@c.us'})
        c = Contact.objects.get()
        self.assertEqual((c.phone, c.photo_source), ('212661234567', 'whatsapp'))
        self.assertEqual(Image.open(io.BytesIO(bytes(c.photo))).size, (512, 512))
        icon = self.client.get(f'/a/{c.token}/icon-192.png')
        self.assertEqual(Image.open(io.BytesIO(icon.content)).size, (192, 192))
        self.assertEqual(c.action_url, 'https://wa.me/call/212661234567')

    def test_create_without_whatsapp_photo_and_duplicate(self):
        self.login()
        api = mock.Mock(status_code=200, json=lambda: {'urlAvatar': '', 'available': False})
        with mock.patch('contacts.services.requests.post', return_value=api):
            self.client.post('/personne/nouvelle/', {'name': 'Ali', 'phone': '0661234567', 'action': 'chat'})
            r = self.client.post('/personne/nouvelle/', {'name': 'Bis', 'phone': '+212661234567',
                                                         'action': 'call'})
        self.assertContains(r, 'déjà dans la liste')
        c = Contact.objects.get()
        self.assertIsNone(c.photo)
        self.assertEqual(c.action_url, 'https://wa.me/212661234567')

    def test_upload_wins_and_survives_rename(self):
        self.login()
        photo = io.BytesIO(_jpeg((300, 900)))
        photo.name = 'p.jpg'
        with mock.patch('contacts.services.requests.post') as post:
            self.client.post('/personne/nouvelle/', {'name': 'Ali', 'phone': '0661234567',
                                                     'action': 'tel', 'photo': photo})
            c = Contact.objects.get()
            self.client.post(f'/personne/{c.pk}/', {'name': 'Ali B', 'phone': '0661234567', 'action': 'tel'})
        post.assert_not_called()
        c.refresh_from_db()
        self.assertEqual((c.name, c.photo_source, c.action_url), ('Ali B', 'import', 'tel:+212661234567'))

    def test_public_pages(self):
        c = Contact.objects.create(name='Hind B', phone='212661234567')
        r = self.client.get(f'/a/{c.token}/')
        self.assertContains(r, 'https://wa.me/call/212661234567')
        self.assertNotContains(r, 'écran d’accueil')
        self.assertEqual(r['X-Robots-Tag'], 'noindex, nofollow')
        self.assertContains(self.client.get(f'/a/{c.token}/?installer=1'), 'écran d’accueil')
        m = json.loads(self.client.get(f'/a/{c.token}/manifest.json').content)
        self.assertEqual((m['name'], m['short_name'], m['start_url'], m['display']),
                         ('Hind B', 'Hind', f'/a/{c.token}/', 'standalone'))
        m = json.loads(self.client.get(f'/a/{c.token}/manifest.json',
                                       HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 18_0)').content)
        self.assertEqual(m['display'], 'browser')
        icon = self.client.get(f'/a/{c.token}/icon-192.png')  # sans photo : initiales
        self.assertEqual(Image.open(io.BytesIO(icon.content)).size, (192, 192))
        self.assertEqual(self.client.get(f'/a/{c.token}/icon-999.png').status_code, 404)
        self.assertEqual(self.client.get('/a/inconnu/').status_code, 404)

    def test_delete(self):
        self.login()
        c = Contact.objects.create(name='X', phone='212661234567')
        self.client.post(f'/personne/{c.pk}/supprimer/')
        self.assertEqual(self.client.get(f'/a/{c.token}/').status_code, 404)
