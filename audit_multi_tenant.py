"""
Audit complet du systeme multi-tenant
Verifie que tous les modeles et ViewSets sont correctement configures
"""
import os
import django
import inspect

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.apps import apps
from django.db import models
from rest_framework import viewsets
from API import views, distribution_views
from API.mixins import TenantFilterMixin, WarehouseRelatedTenantMixin

print("=" * 80)
print("AUDIT COMPLET DU SYSTEME MULTI-TENANT")
print("=" * 80)

# 1. VERIFIER LES MODELES
print("\n" + "=" * 80)
print("1. MODELES AVEC CHAMP 'company'")
print("=" * 80)

app_models = apps.get_app_config('API').get_models()
models_with_company = []
models_without_company = []

for model in app_models:
    if hasattr(model, '_meta'):
        fields = [f.name for f in model._meta.get_fields()]
        if 'company' in fields:
            models_with_company.append(model.__name__)
        else:
            # Verifier si c'est un modele qui devrait avoir company
            # (exclure les modeles intermediaires et de relation)
            if not model._meta.auto_created and not model.__name__.startswith('Log'):
                models_without_company.append(model.__name__)

print(f"\nModeles AVEC champ company ({len(models_with_company)}):")
for m in sorted(models_with_company):
    print(f"  ✓ {m}")

print(f"\nModeles SANS champ company ({len(models_without_company)}):")
for m in sorted(models_without_company):
    # Determiner si c'est normal ou pas
    if m in ['User', 'Group', 'Permission', 'ContentType', 'Session',
             'LogEntry', 'UserProfile', 'SystemConfig', 'Currency',
             'SyncLogMobile', 'DepenseTourneeMobile']:
        print(f"  ⚪ {m} (OK - pas besoin)")
    else:
        print(f"  ⚠️  {m} (A VERIFIER)")

# 2. VERIFIER LES VIEWSETS
print("\n" + "=" * 80)
print("2. VIEWSETS ET MIXINS")
print("=" * 80)

viewsets_with_mixin = []
viewsets_without_mixin = []

# Parcourir tous les ViewSets dans views.py
for name, obj in inspect.getmembers(views):
    if inspect.isclass(obj) and issubclass(obj, viewsets.ModelViewSet) and obj != viewsets.ModelViewSet:
        if issubclass(obj, (TenantFilterMixin, WarehouseRelatedTenantMixin)):
            viewsets_with_mixin.append(name)
        else:
            viewsets_without_mixin.append(name)

# Parcourir tous les ViewSets dans distribution_views.py
for name, obj in inspect.getmembers(distribution_views):
    if inspect.isclass(obj) and issubclass(obj, viewsets.ModelViewSet) and obj != viewsets.ModelViewSet:
        if issubclass(obj, (TenantFilterMixin, WarehouseRelatedTenantMixin)):
            viewsets_with_mixin.append(name)
        else:
            viewsets_without_mixin.append(name)

print(f"\nViewSets AVEC TenantFilterMixin ({len(viewsets_with_mixin)}):")
for v in sorted(set(viewsets_with_mixin)):
    print(f"  ✓ {v}")

print(f"\nViewSets SANS TenantFilterMixin ({len(viewsets_without_mixin)}):")
for v in sorted(set(viewsets_without_mixin)):
    # Distribution ViewSets n'utilisent pas le mixin par defaut
    if 'Distribution' in v or 'Tournee' in v or 'Livreur' in v or 'Arret' in v or 'Vente' in v:
        print(f"  ⚠️  {v} (Distribution - A VERIFIER)")
    else:
        print(f"  ❌ {v} (MANQUE LE MIXIN)")

# 3. VERIFIER PERFORM_CREATE
print("\n" + "=" * 80)
print("3. METHODE perform_create DANS LES VIEWSETS")
print("=" * 80)

viewsets_with_perform_create = []
viewsets_without_perform_create = []

for name, obj in inspect.getmembers(views):
    if inspect.isclass(obj) and issubclass(obj, viewsets.ModelViewSet) and obj != viewsets.ModelViewSet:
        if hasattr(obj, 'perform_create') and obj.perform_create != viewsets.ModelViewSet.perform_create:
            viewsets_with_perform_create.append(name)
        else:
            if not issubclass(obj, TenantFilterMixin):
                viewsets_without_perform_create.append(name)

for name, obj in inspect.getmembers(distribution_views):
    if inspect.isclass(obj) and issubclass(obj, viewsets.ModelViewSet) and obj != viewsets.ModelViewSet:
        if hasattr(obj, 'perform_create') and obj.perform_create != viewsets.ModelViewSet.perform_create:
            viewsets_with_perform_create.append(name)
        else:
            viewsets_without_perform_create.append(name)

print(f"\nViewSets avec perform_create custom ({len(viewsets_with_perform_create)}):")
for v in sorted(set(viewsets_with_perform_create)):
    print(f"  ✓ {v}")

print(f"\nViewSets SANS perform_create custom ({len(viewsets_without_perform_create)}):")
for v in sorted(set(viewsets_without_perform_create)):
    print(f"  ⚠️  {v} (Utilise le mixin ou pas de company)")

# 4. RECOMMANDATIONS
print("\n" + "=" * 80)
print("4. RECOMMANDATIONS")
print("=" * 80)

print("\nModeles Distribution a verifier:")
distribution_models = [
    'TourneeMobile', 'ArretTourneeMobile', 'VenteTourneeMobile',
    'LigneVenteTourneeMobile', 'RapportCaisseMobile', 'BonLivraisonVan',
    'LigneBonLivraisonVan', 'CommandeClient', 'LigneCommandeClient'
]

for model_name in distribution_models:
    if model_name in models_with_company:
        print(f"  ✓ {model_name} - OK")
    else:
        print(f"  ❌ {model_name} - MANQUE le champ company!")

print("\n" + "=" * 80)
print("RESUME")
print("=" * 80)

print(f"""
Modeles totaux: {len(app_models)}
  - Avec company: {len(models_with_company)}
  - Sans company: {len(models_without_company)}

ViewSets totaux: {len(set(viewsets_with_mixin + viewsets_without_mixin))}
  - Avec TenantFilterMixin: {len(set(viewsets_with_mixin))}
  - Sans TenantFilterMixin: {len(set(viewsets_without_mixin))}
""")

print("=" * 80)
