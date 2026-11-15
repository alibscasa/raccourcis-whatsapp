"""Numéros, photos et appel à Green API."""
import io
import re

import requests
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont, ImageOps

PHOTO_SIZE = 512
ICON_SIZES = (180, 192, 512)
_COLORS = ['#2e7d32', '#1565c0', '#6a1b9a', '#c62828', '#ef6c00', '#00838f', '#4e342e']
_FONTS = ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
          '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf']


def normalize_phone(raw):
    """« 06 61 23 45 67 », « +212 661-234567 », « 00212… » → « 212661234567 ».

    Renvoie None si le résultat n'est pas un numéro international plausible.
    """
    digits = re.sub(r'\D', '', raw or '')
    if digits.startswith('00'):
        digits = digits[2:]
    elif digits.startswith('0'):
        digits = settings.COUNTRY_PREFIX + digits[1:]
    return digits if 8 <= len(digits) <= 15 else None


def square_jpeg(raw):
    """Octets d'une image quelconque → JPEG carré 512 px (recadrage centré)."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('RGB')
    img = ImageOps.fit(img, (PHOTO_SIZE, PHOTO_SIZE), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, 'JPEG', quality=88)
    return out.getvalue()


def initials(name):
    parts = name.split()
    if not parts:
        return '?'
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _font(size):
    for path in _FONTS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _initials_image(contact, size):
    """Icône de repli quand la personne n'a pas de photo : initiales sur fond coloré."""
    img = Image.new('RGB', (size, size), _COLORS[sum(map(ord, contact.phone)) % len(_COLORS)])
    draw = ImageDraw.Draw(img)
    text, font = initials(contact.name), _font(int(size * 0.4))
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((size - box[2] - box[0]) / 2, (size - box[3] - box[1]) / 2), text,
              fill='#ffffff', font=font)
    return img


def icon_png(contact, size):
    if contact.photo:
        img = Image.open(io.BytesIO(bytes(contact.photo))).convert('RGB')
        if img.size != (size, size):
            img = img.resize((size, size), Image.LANCZOS)
    else:
        img = _initials_image(contact, size)
    out = io.BytesIO()
    img.save(out, 'PNG', optimize=True)
    return out.getvalue()


def fetch_whatsapp_avatar(phone):
    """Photo de profil WhatsApp via Green API. Renvoie (octets JPEG | None, message)."""
    if not (settings.GREENAPI_INSTANCE and settings.GREENAPI_TOKEN):
        return None, 'Green API n’est pas configuré (GREENAPI_INSTANCE / GREENAPI_TOKEN).'
    try:
        resp = requests.post(_greenapi('getAvatar'), json={'chatId': f'{phone}@c.us'}, timeout=10)
    except requests.RequestException as e:
        return None, f'Green API injoignable ({e.__class__.__name__}).'
    if resp.status_code != 200:
        return None, f'Green API a répondu {resp.status_code}.'
    try:
        avatar_url = (resp.json() or {}).get('urlAvatar') or ''
    except ValueError:
        return None, 'Réponse Green API illisible.'
    if not avatar_url.startswith('https://'):
        return None, ('Pas de photo de profil visible sur WhatsApp pour ce numéro '
                      '(numéro sans WhatsApp, ou photo masquée).')
    try:
        img = requests.get(avatar_url, timeout=10)
        img.raise_for_status()
        return square_jpeg(img.content), ''
    except Exception as e:  # réseau ou image illisible
        return None, f'Photo WhatsApp illisible ({e.__class__.__name__}).'


def _greenapi(method):
    return (f'{settings.GREENAPI_URL}/waInstance{settings.GREENAPI_INSTANCE}'
            f'/{method}/{settings.GREENAPI_TOKEN}')


def fetch_whatsapp_contacts():
    """Contacts du compte WhatsApp relié à Green API (« getContacts »).

    Renvoie ([{'phone', 'name'}, …] triés par nom, message d'erreur éventuel).
    Les groupes sont écartés ; un contact sans nom porte son numéro.
    """
    if not (settings.GREENAPI_INSTANCE and settings.GREENAPI_TOKEN):
        return [], 'Green API n’est pas configuré (GREENAPI_INSTANCE / GREENAPI_TOKEN).'
    try:
        resp = requests.get(_greenapi('getContacts'), timeout=20)
    except requests.RequestException as e:
        return [], f'Green API injoignable ({e.__class__.__name__}).'
    if resp.status_code != 200:
        return [], f'Green API a répondu {resp.status_code}.'
    try:
        rows = resp.json()
    except ValueError:
        rows = None
    if not isinstance(rows, list):
        return [], 'Réponse Green API illisible.'
    people = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        chat_id = str(row.get('id') or '')
        if not chat_id.endswith('@c.us'):
            continue
        phone = chat_id[:-5]
        if not (phone.isdigit() and 8 <= len(phone) <= 15):
            continue
        name = str(row.get('contactName') or row.get('name') or '').strip()
        people[phone] = {'phone': phone, 'name': name[:60] or f'+{phone}', 'named': bool(name)}
    ordered = sorted(people.values(), key=lambda c: (not c['named'], c['name'].casefold()))
    return ordered, ''


def app_icon_png(size):
    """Icône de l'appli elle-même : combiné blanc sur fond vert."""
    img = Image.new('RGB', (size, size), '#128c7e')
    draw = ImageDraw.Draw(img)
    u = size / 100
    draw.ellipse((22 * u, 22 * u, 78 * u, 78 * u), fill='#ffffff')
    draw.ellipse((30 * u, 30 * u, 70 * u, 70 * u), fill='#128c7e')
    draw.polygon([(22 * u, 78 * u), (27 * u, 60 * u), (40 * u, 73 * u)], fill='#ffffff')
    draw.ellipse((42 * u, 42 * u, 58 * u, 58 * u), fill='#ffffff')
    out = io.BytesIO()
    img.save(out, 'PNG', optimize=True)
    return out.getvalue()
