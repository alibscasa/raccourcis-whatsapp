import hmac
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import IntegrityError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .models import Contact

MAX_UPLOAD = 8 * 1024 * 1024
MAX_TRIES, LOCK_SECONDS = 8, 15 * 60


def healthz(request):
    return HttpResponse('OK', content_type='text/plain')


# ─── Accès à l'écran de gestion : un mot de passe unique ──────────

def gestion(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('gestion'):
            return redirect('connexion')
        return view(request, *args, **kwargs)
    return wrapper


def connexion(request):
    if request.session.get('gestion'):
        return redirect('liste')
    error = ''
    if not settings.APP_PASSWORD:
        error = 'Le mot de passe n’est pas configuré (variable APP_PASSWORD).'
    elif request.method == 'POST':
        key = f'essais:{request.META.get("REMOTE_ADDR", "")}'
        if cache.get(key, 0) >= MAX_TRIES:
            error = 'Trop d’essais. Réessayez dans un quart d’heure.'
        elif hmac.compare_digest(request.POST.get('password', '').encode(),
                                 settings.APP_PASSWORD.encode()):
            cache.delete(key)
            request.session.cycle_key()
            request.session['gestion'] = True
            return redirect('liste')
        else:
            cache.set(key, cache.get(key, 0) + 1, LOCK_SECONDS)
            error = 'Mot de passe incorrect.'
    return render(request, 'contacts/connexion.html', {'error': error})


@require_POST
def deconnexion(request):
    request.session.flush()
    return redirect('connexion')


# ─── Gestion des personnes ────────────────────────────────────────

@gestion
def liste(request):
    return render(request, 'contacts/liste.html', {'contacts': Contact.objects.all()})


@gestion
def fiche(request, pk=None):
    contact = get_object_or_404(Contact, pk=pk) if pk else Contact()
    error = ''
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()[:60]
        phone = services.normalize_phone(request.POST.get('phone'))
        action = request.POST.get('action') or Contact.CALL
        upload = request.FILES.get('photo')
        jpeg = None
        if not name:
            error = 'Le nom est obligatoire.'
        elif not phone:
            error = 'Numéro invalide. Exemple : 06 61 23 45 67 ou +212 661 234567.'
        elif action not in dict(Contact.ACTIONS):
            error = 'Action inconnue.'
        elif Contact.objects.filter(phone=phone).exclude(pk=contact.pk).exists():
            error = 'Ce numéro est déjà dans la liste.'
        elif upload:
            if upload.size > MAX_UPLOAD:
                error = 'Photo trop lourde (8 Mo maximum).'
            else:
                try:
                    jpeg = services.square_jpeg(upload.read())
                except Exception:
                    error = 'Fichier photo illisible.'
        contact.name, contact.action = name, action
        if not error:
            phone_changed = contact.phone != phone
            contact.phone = phone
            note = ''
            if jpeg:
                contact.photo, contact.photo_source = jpeg, 'import'
            elif phone_changed and contact.photo_source != 'import':
                # Nouveau numéro : on lit sa photo WhatsApp ; l'ancienne ne vaut plus.
                wa, note = services.fetch_whatsapp_avatar(phone)
                contact.photo, contact.photo_source = wa, ('whatsapp' if wa else '')
            contact.version += 1
            try:
                contact.save()
            except IntegrityError:
                error = 'Ce numéro est déjà dans la liste.'
            else:
                messages.success(request, f'{contact.name} est enregistré.')
                if note:
                    messages.warning(request, f'{note} Vous pouvez importer une photo à la place.')
                return redirect('liste')
        else:
            contact.phone = request.POST.get('phone', '')
    return render(request, 'contacts/fiche.html', {
        'c': contact, 'error': error, 'actions': Contact.ACTIONS})


@gestion
@require_POST
def relire_photo(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    jpeg, note = services.fetch_whatsapp_avatar(contact.phone)
    if jpeg:
        contact.photo, contact.photo_source = jpeg, 'whatsapp'
        contact.version += 1
        contact.save()
        messages.success(request, f'Photo WhatsApp de {contact.name} mise à jour.')
    else:
        messages.warning(request, note)
    return redirect('liste')


@gestion
@require_POST
def supprimer(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    contact.delete()
    messages.success(request, f'{contact.name} est retiré. Son icône ne fonctionnera plus.')
    return redirect('liste')


# ─── Pages d'appel (sans mot de passe) ────────────────────────────

def _private(response):
    response['X-Robots-Tag'] = 'noindex, nofollow'
    response['Referrer-Policy'] = 'no-referrer'
    return response


def appel(request, token):
    contact = get_object_or_404(Contact, token=token)
    response = render(request, 'contacts/appel.html', {
        'c': contact, 'setup': request.GET.get('installer') == '1'})
    response['Cache-Control'] = 'no-store'
    return _private(response)


def manifest(request, token):
    """Manifeste propre à la personne : il donne son nom et sa photo à l'icône."""
    contact = get_object_or_404(Contact, token=token)
    base = f'/a/{contact.token}/'
    # iOS : « browser » garde l'ouverture dans Safari, qui sait passer la main à WhatsApp.
    ua = request.META.get('HTTP_USER_AGENT', '')
    ios = any(k in ua for k in ('iPhone', 'iPad', 'iPod'))
    icons = [{'src': f'{base}icon-{size}.png?v={contact.version}', 'sizes': f'{size}x{size}',
              'type': 'image/png', 'purpose': purpose}
             for size in (192, 512) for purpose in ('any', 'maskable')]
    response = JsonResponse({
        'id': base, 'name': contact.name, 'short_name': contact.first_name[:12],
        'start_url': base, 'scope': base,
        'display': 'browser' if ios else 'standalone',
        'background_color': '#ffffff', 'theme_color': '#128c7e',
        'lang': 'fr', 'icons': icons,
    }, content_type='application/manifest+json')
    response['Cache-Control'] = 'no-cache'
    return _private(response)


def icone(request, token, size):
    if size not in services.ICON_SIZES:
        raise Http404
    contact = get_object_or_404(Contact, token=token)
    response = HttpResponse(services.icon_png(contact, size), content_type='image/png')
    # L'adresse porte ?v=<version> : une nouvelle photo change l'adresse.
    response['Cache-Control'] = 'public, max-age=86400'
    return _private(response)
