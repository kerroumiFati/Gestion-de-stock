"""
Mixins pour gérer le multi-tenancy dans les ViewSets
"""
from rest_framework import status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


class TenantFilterMixin:
    """
    Mixin pour filtrer automatiquement les données par company (tenant).
    À utiliser avec les ViewSets DRF.

    Ce mixin :
    - Filtre automatiquement les querysets par company de l'utilisateur
    - Attache automatiquement la company lors de la création d'objets
    - Empêche l'accès aux données d'autres companies
    """

    def get_queryset(self):
        """
        Filtre le queryset par la company de l'utilisateur connecté.
        Uniquement si le modèle a un champ 'company'.
        Seul le superutilisateur voit toutes les données. Les administrateurs d'entreprise
        (is_staff) ne voient que leur entreprise — avant, is_staff voyait tout.
        """
        from .tenant import filtrer
        queryset = super().get_queryset()

        # Vérifier si l'utilisateur est authentifié
        if not self.request.user.is_authenticated:
            return queryset.none()

        # Vérifier si le modèle a un champ 'company'
        if hasattr(queryset.model, 'company'):
            # Données de l'entreprise de l'utilisateur + anciennes données sans entreprise
            queryset = filtrer(queryset, self.request)

        return queryset

    def perform_create(self, serializer):
        """
        Attache automatiquement la company lors de la création.
        """
        # Vérifier si l'utilisateur a une company (session web ou jeton du téléphone)
        from .tenant import entreprise_de
        company = entreprise_de(self.request)
        if company is not None:
            # Attacher la company à l'objet créé si le modèle a ce champ
            model_fields = [f.name for f in serializer.Meta.model._meta.get_fields()]
            if 'company' in model_fields:
                serializer.save(company=company)
            else:
                serializer.save()
        else:
            # Si pas de company, créer sans company (pour rétro-compatibilité)
            serializer.save()

    def check_company_access(self, obj):
        """
        Vérifie que l'objet appartient bien à la company de l'utilisateur.
        Utile pour les opérations update/delete.
        """
        from .tenant import entreprise_de, voit_toutes_les_entreprises
        if hasattr(obj, 'company') and not voit_toutes_les_entreprises(self.request):
            if obj.company_id is not None and obj.company != entreprise_de(self.request):
                return False
        return True


class WarehouseRelatedTenantMixin:
    """
    Mixin spécial pour les modèles liés à Warehouse (comme ProductStock, StockMove).
    Ces modèles n'ont pas de champ company direct mais héritent via warehouse.
    """

    def get_queryset(self):
        """
        Filtre le queryset par la company via le warehouse.
        Seul le superutilisateur voit toutes les données (avant : aussi is_staff).
        """
        from django.db.models import Q
        from .tenant import entreprise_de, voit_toutes_les_entreprises
        queryset = super().get_queryset()

        # Vérifier si l'utilisateur est authentifié
        if not self.request.user.is_authenticated:
            return queryset.none()

        if voit_toutes_les_entreprises(self.request):
            return queryset

        # Filtrer par warehouse.company
        model = queryset.model
        if hasattr(model, 'warehouse'):
            company = entreprise_de(self.request)
            if company is not None:
                # Afficher les données de la company de l'utilisateur + celles sans company
                queryset = queryset.filter(Q(warehouse__company=company) | Q(warehouse__company__isnull=True))
            # Si l'utilisateur n'a pas de company, afficher toutes les données (pour éviter liste vide)

        return queryset
