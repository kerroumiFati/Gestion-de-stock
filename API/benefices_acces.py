"""
Protection du tableau de bord des benefices.

Regles :
- reserve aux administrateurs de l'entreprise (UserProfile.role == 'admin') ;
- un code PIN commun par entreprise, choisi par un administrateur, stocke chiffre ;
- une fois le PIN saisi, l'acces reste ouvert DUREE_DEVERROUILLAGE dans la session
  de ce navigateur (puis le PIN est redemande) ; « Verrouiller » le referme tout de suite ;
- apres MAX_ECHECS PIN incorrects, l'acces est bloque BLOCAGE pour toute l'entreprise.
"""
import re
from datetime import datetime, timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

DUREE_DEVERROUILLAGE = timedelta(minutes=15)
MAX_ECHECS = 5
BLOCAGE = timedelta(minutes=15)
SESSION_KEY = 'benefices_deverrouille'
PIN_RE = re.compile(r'^\d{4,8}$')


class AccesRefuse(Exception):
    """`code` = statut HTTP, `raison` = code court pour l'interface."""

    def __init__(self, message, code=403, raison='refuse'):
        super().__init__(message)
        self.message = message
        self.code = code
        self.raison = raison


def profil_admin(user):
    """Profil de l'utilisateur s'il est administrateur de son entreprise, sinon None."""
    if not (user and user.is_authenticated and user.is_active):
        return None
    profil = getattr(user, 'profile', None)
    try:
        if profil is not None and profil.role == 'admin' and profil.company_id:
            return profil
    except Exception:
        return None
    return None


def est_admin(user):
    return profil_admin(user) is not None


def _acces(company):
    from .models import AccesTableauBenefices
    acces, _ = AccesTableauBenefices.objects.get_or_create(company=company)
    return acces


def _maintenant():
    return timezone.now()


def etat(request):
    """Etat affiche par la page : admin ? PIN defini ? deverrouille ? bloque ?"""
    profil = profil_admin(request.user)
    if profil is None:
        return {'admin': False}
    acces = _acces(profil.company)
    fin = _fin_deverrouillage(request, profil)
    bloque = acces.bloque_jusqua if acces.bloque_jusqua and acces.bloque_jusqua > _maintenant() else None
    return {
        'admin': True,
        'entreprise': profil.company.name,
        'pin_defini': bool(acces.pin_hash),
        'deverrouille': fin is not None,
        'expire_le': fin.isoformat() if fin else None,
        'bloque_jusqua': bloque.isoformat() if bloque else None,
        'duree_minutes': int(DUREE_DEVERROUILLAGE.total_seconds() // 60),
    }


def _fin_deverrouillage(request, profil):
    data = request.session.get(SESSION_KEY) or {}
    if data.get('company') != profil.company_id or data.get('user') != request.user.pk:
        return None
    try:
        fin = datetime.fromisoformat(data.get('jusqua'))
    except (TypeError, ValueError):
        return None
    return fin if fin > _maintenant() else None


def verifier_acces(request):
    """Leve AccesRefuse si l'utilisateur ne peut pas voir les benefices maintenant.
    Retourne l'entreprise (les donnees sont limitees a celle-ci)."""
    profil = profil_admin(request.user)
    if profil is None:
        raise AccesRefuse("Le tableau de bord des bénéfices est réservé à l'administrateur de l'entreprise.",
                          code=403, raison='non_admin')
    if _fin_deverrouillage(request, profil) is None:
        raise AccesRefuse('Saisissez le code PIN pour ouvrir le tableau de bord des bénéfices.',
                          code=403, raison='pin_requis')
    return profil.company


def valider_format(pin):
    if not isinstance(pin, str) or not PIN_RE.match(pin):
        raise AccesRefuse('Le code PIN doit contenir de 4 à 8 chiffres.', code=400, raison='format')


def definir_pin(request, nouveau, confirmation, actuel=None):
    """Premier PIN de l'entreprise, ou changement (le PIN actuel est alors exige)."""
    profil = profil_admin(request.user)
    if profil is None:
        raise AccesRefuse("Réservé à l'administrateur de l'entreprise.", code=403, raison='non_admin')
    acces = _acces(profil.company)
    if acces.pin_hash:
        _controler_pin(request, acces, actuel)
    valider_format(nouveau)
    if nouveau != confirmation:
        raise AccesRefuse('Les deux codes PIN ne sont pas identiques.', code=400, raison='confirmation')
    acces.pin_hash = make_password(nouveau)
    acces.echecs = 0
    acces.bloque_jusqua = None
    acces.modifie_par = request.user
    acces.save()
    _ouvrir(request, profil)
    return etat(request)


def deverrouiller(request, pin):
    profil = profil_admin(request.user)
    if profil is None:
        raise AccesRefuse("Réservé à l'administrateur de l'entreprise.", code=403, raison='non_admin')
    acces = _acces(profil.company)
    if not acces.pin_hash:
        raise AccesRefuse("Aucun code PIN n'est encore défini : choisissez-en un.", code=400, raison='pin_absent')
    _controler_pin(request, acces, pin)
    _ouvrir(request, profil)
    return etat(request)


def verrouiller(request):
    request.session.pop(SESSION_KEY, None)
    return etat(request)


def _ouvrir(request, profil):
    request.session[SESSION_KEY] = {
        'company': profil.company_id,
        'user': request.user.pk,
        'jusqua': (_maintenant() + DUREE_DEVERROUILLAGE).isoformat(),
    }


def _controler_pin(request, acces, pin):
    """Verifie le PIN avec blocage apres MAX_ECHECS erreurs (compteur par entreprise)."""
    from django.db import transaction
    from .models import AccesTableauBenefices

    # Le refus est leve APRES la transaction : lever dedans annulerait l'enregistrement
    # du compteur d'echecs.
    refus = None
    with transaction.atomic():
        acces = AccesTableauBenefices.objects.select_for_update().get(pk=acces.pk)
        if acces.bloque_jusqua and acces.bloque_jusqua > _maintenant():
            minutes = max(1, int((acces.bloque_jusqua - _maintenant()).total_seconds() // 60) + 1)
            refus = AccesRefuse(f'Trop d’essais incorrects : réessayez dans {minutes} minute(s).',
                                code=429, raison='bloque')
        elif isinstance(pin, str) and pin and check_password(pin, acces.pin_hash):
            if acces.echecs or acces.bloque_jusqua:
                acces.echecs = 0
                acces.bloque_jusqua = None
                acces.save(update_fields=['echecs', 'bloque_jusqua', 'updated_at'])
        else:
            acces.echecs += 1
            restants = MAX_ECHECS - acces.echecs
            if restants <= 0:
                acces.echecs = 0
                acces.bloque_jusqua = _maintenant() + BLOCAGE
                refus = AccesRefuse(
                    f'Code PIN incorrect. Accès bloqué pendant {int(BLOCAGE.total_seconds() // 60)} minutes.',
                    code=429, raison='bloque')
            else:
                refus = AccesRefuse(f'Code PIN incorrect. Il reste {restants} essai(s).',
                                    code=403, raison='pin_incorrect')
            acces.save(update_fields=['echecs', 'bloque_jusqua', 'updated_at'])
    if refus is not None:
        raise refus
