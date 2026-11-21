"""Contrôles d'accès des points d'accès « argent encaissé » (liste et encaissements).

Règles :
- Un livreur ne voit et n'enregistre que l'argent de SES tournées.
- Un utilisateur du bureau ne voit que les livreurs, clients et tournées de SON entreprise.
- Les superutilisateurs voient tout (administration du logiciel).
Les données sans entreprise restent accessibles, comme dans le reste de l'application.
"""


def company_connectee(request):
    from API.models import SystemConfig
    return getattr(request, 'company', None) or SystemConfig.company_of_user(request.user)


def livreur_connecte(user):
    if not getattr(user, 'is_authenticated', False):
        return None
    try:
        return user.livreur_distribution_profile
    except Exception:
        return None


def _est_superutilisateur(user):
    return bool(getattr(user, 'is_superuser', False))


def _meme_entreprise(request, company_id):
    """Vrai si la donnée (company_id) est visible par l'entreprise de l'utilisateur."""
    if _est_superutilisateur(request.user):
        return True
    if company_id is None:
        return True
    company = company_connectee(request)
    return company is not None and company.pk == company_id


def company_id_du_livreur(livreur):
    entrepot = getattr(livreur, 'entrepot', None)
    return getattr(entrepot, 'company_id', None)


def livreur_autorise(request, livreur):
    """Le livreur connecté lui-même, ou un livreur de l'entreprise de l'utilisateur du bureau."""
    if livreur is None:
        return False
    if _est_superutilisateur(request.user):
        return True
    moi = livreur_connecte(request.user)
    if moi is not None:
        return moi.pk == livreur.pk
    return _meme_entreprise(request, company_id_du_livreur(livreur))


def tournee_autorisee(request, tournee):
    """La tournée doit appartenir au livreur connecté (ou à l'entreprise pour le bureau)."""
    if tournee is None:
        return True
    return livreur_autorise(request, tournee.livreur)


def client_autorise(request, client):
    return client is not None and _meme_entreprise(request, getattr(client, 'company_id', None))


def commande_autorisee(request, commande):
    if commande is None:
        return False
    company_id = commande.company_id or getattr(commande.client, 'company_id', None)
    return _meme_entreprise(request, company_id)
