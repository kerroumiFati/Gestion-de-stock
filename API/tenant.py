"""Isolement des données par entreprise (multi-tenant) : outils communs.

Règles :
- l'entreprise de l'utilisateur vient de son profil (TenantMiddleware la pose dans
  request.company pour les sessions web ; pour le téléphone, authentifié par jeton JWT au niveau
  de DRF, le middleware ne voit pas l'utilisateur : on relit alors le profil) ;
- seul le superutilisateur (propriétaire de la plateforme) voit toutes les entreprises.
  Les administrateurs d'entreprise sont « is_staff » : ils ne voient que leur entreprise ;
- les anciennes données sans entreprise (company vide) restent visibles par tous.
"""
from django.db.models import Q


def entreprise_de(request):
    """Entreprise de l'utilisateur de la requête (ou None)."""
    if request is None:
        return None
    company = getattr(request, 'company', None)
    if company is not None:
        return company
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return None
    profil = getattr(user, 'profile', None)
    return getattr(profil, 'company', None)


def voit_toutes_les_entreprises(request):
    user = getattr(request, 'user', None)
    return bool(user is not None and user.is_authenticated and user.is_superuser)


def filtrer(queryset, request, champ='company'):
    """Données de l'entreprise de l'utilisateur + anciennes données sans entreprise.
    champ : chemin vers l'entreprise (ex. 'produit__company')."""
    if voit_toutes_les_entreprises(request):
        return queryset
    company = entreprise_de(request)
    if company is None:
        return queryset.filter(**{f'{champ}__isnull': True})
    return queryset.filter(Q(**{champ: company}) | Q(**{f'{champ}__isnull': True}))


def q_livreurs(company):
    """Livreurs d'une entreprise : via leur entrepôt ou leur compte. Les anciennes fiches sans
    entrepôt ni compte ne sont rattachées à aucune entreprise : visibles par tous."""
    return (Q(entrepot__company=company) | Q(user__profile__company=company)
            | Q(entrepot__company__isnull=True, user__profile__company__isnull=True))


def filtrer_livreurs(queryset, request):
    if voit_toutes_les_entreprises(request):
        return queryset
    company = entreprise_de(request)
    # Le livreur du compte connecté reste toujours visible (téléphone sans profil d'entreprise)
    moi = Q(user=request.user) if getattr(request, 'user', None) is not None and request.user.is_authenticated else Q(pk__in=[])
    if company is None:
        return queryset.filter(Q(entrepot__company__isnull=True, user__profile__company__isnull=True) | moi).distinct()
    return queryset.filter(q_livreurs(company) | moi).distinct()
