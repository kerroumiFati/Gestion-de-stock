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
        """
        queryset = super().get_queryset()

        # Vérifier si l'utilisateur est authentifié et a une company
        if not self.request.user.is_authenticated:
            return queryset.none()

        # Vérifier si l'utilisateur a un profil avec une company
        if not hasattr(self.request, 'company') or self.request.company is None:
            # Si l'utilisateur n'a pas de company, ne retourner aucune donnée
            return queryset.none()

        # Vérifier si le modèle a un champ 'company'
        model = queryset.model
        if hasattr(model, 'company'):
            # Filtrer par company de l'utilisateur
            queryset = queryset.filter(company=self.request.company)

        return queryset

    def perform_create(self, serializer):
        """
        Attache automatiquement la company lors de la création.
        """
        # Vérifier si l'utilisateur a une company
        if hasattr(self.request, 'company') and self.request.company is not None:
            # Vérifier si le modèle a un champ 'company'
            model = serializer.Meta.model
            field_names = [f.name for f in model._meta.get_fields()]
            if 'company' in field_names:
                serializer.save(company=self.request.company)
            else:
                serializer.save()
        else:
            # Si pas de company, sauvegarder sans company (pour compatibilité)
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
        """
        queryset = super().get_queryset()

        # Vérifier si l'utilisateur est authentifié et a une company
        if not self.request.user.is_authenticated:
            return queryset.none()

        if not hasattr(self.request, 'company') or self.request.company is None:
            return queryset.none()

        # Filtrer par warehouse.company
        model = queryset.model
        if hasattr(model, 'warehouse'):
            queryset = queryset.filter(warehouse__company=self.request.company)

        return queryset
