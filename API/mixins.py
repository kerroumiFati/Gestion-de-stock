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
        Les superusers et staff voient toutes les données.
        """
        from django.db.models import Q
        queryset = super().get_queryset()

        # Vérifier si l'utilisateur est authentifié
        if not self.request.user.is_authenticated:
            return queryset.none()

        # Les superusers et staff voient toutes les données
        if self.request.user.is_superuser or self.request.user.is_staff:
            return queryset

        # Vérifier si le modèle a un champ 'company'
        model = queryset.model
        if hasattr(model, 'company'):
            # Filtrer par la company de l'utilisateur OU données sans company (null)
            if hasattr(self.request, 'company') and self.request.company is not None:
                # Afficher les données de la company de l'utilisateur + celles sans company
                queryset = queryset.filter(Q(company=self.request.company) | Q(company__isnull=True))
            else:
                # Si l'utilisateur n'a pas de company, afficher uniquement les données sans company
                queryset = queryset.filter(company__isnull=True)

        return queryset

    def perform_create(self, serializer):
        """
        Attache automatiquement la company lors de la création.
        """
        # Vérifier si l'utilisateur a une company
        if hasattr(self.request, 'company') and self.request.company is not None:
            # Attacher la company à l'objet créé si le modèle a ce champ
            model_fields = [f.name for f in serializer.Meta.model._meta.get_fields()]
            if 'company' in model_fields:
                serializer.save(company=self.request.company)
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
        if hasattr(obj, 'company'):
            if obj.company != self.request.company:
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
        Les superusers et staff voient toutes les données.
        """
        from django.db.models import Q
        queryset = super().get_queryset()

        # Vérifier si l'utilisateur est authentifié
        if not self.request.user.is_authenticated:
            return queryset.none()

        # Les superusers et staff voient toutes les données
        if self.request.user.is_superuser or self.request.user.is_staff:
            return queryset

        # Filtrer par warehouse.company
        model = queryset.model
        if hasattr(model, 'warehouse'):
            if hasattr(self.request, 'company') and self.request.company is not None:
                # Afficher les données de la company de l'utilisateur + celles sans company
                queryset = queryset.filter(Q(warehouse__company=self.request.company) | Q(warehouse__company__isnull=True))
            else:
                # Si l'utilisateur n'a pas de company, afficher les données sans company
                queryset = queryset.filter(warehouse__company__isnull=True)

        return queryset
