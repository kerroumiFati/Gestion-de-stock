"""Contrôles d'accès des points d'accès « argent encaissé » (liste et encaissements).

Règles :
- Un livreur ne voit et n'enregistre que l'argent de SES tournées.
- Un utilisateur du bureau ne voit que les livreurs, clients et tournées de SON entreprise.
- Les superutilisateurs voient tout (administration du logiciel).
Les données sans entreprise restent accessibles, comme dans le reste de l'application.
- Un livreur peut toujours agir sur SES commandes (livreur ou « passée par ») et sur les
  clients qui lui sont rattachés (clients assignés, planning hebdo, ses commandes, ses ventes),
  même si son entrepôt n'a pas d'entreprise ou si l'entreprise diffère : sinon l'encaissement
  répondait 404 et le paiement restait bloqué sur le téléphone. Un utilisateur du bureau
  d'une entreprise A n'accède toujours pas aux données d'une entreprise B.
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


def _client_du_livreur(livreur, client):
    """Vrai si le client est rattaché au livreur (assigné, planning, commandes ou ventes)."""
    from API.distribution_models import (ClientLivreurHebdo, CommandeClient,
                                         VenteTourneeMobile)
    from django.db.models import Q
    if livreur.clients_assignes.filter(pk=client.pk).exists():
        return True
    if ClientLivreurHebdo.objects.filter(client=client, livreur=livreur).exists():
        return True
    if CommandeClient.objects.filter(client=client).filter(
            Q(livreur=livreur) | Q(passee_par=livreur)).exists():
        return True
    return VenteTourneeMobile.objects.filter(client=client, tournee__livreur=livreur).exists()


def client_autorise(request, client):
    if client is None:
        return False
    if _meme_entreprise(request, getattr(client, 'company_id', None)):
        return True
    moi = livreur_connecte(request.user)
    return moi is not None and _client_du_livreur(moi, client)


def commande_autorisee(request, commande):
    if commande is None:
        return False
    moi = livreur_connecte(request.user)
    if moi is not None and moi.pk in (commande.livreur_id, commande.passee_par_id):
        return True
    company_id = commande.company_id or getattr(commande.client, 'company_id', None)
    return _meme_entreprise(request, company_id)
