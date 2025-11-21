"""
Script pour tester les endpoints de l'API
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Warehouse, Client
from API.distribution_models import TourneeMobile

print("=" * 70)
print("TEST DES DONNEES DE L'API")
print("=" * 70)

# Test 1: Entrepots
print("\n1. ENTREPOTS")
print("-" * 70)
entrepots = Warehouse.objects.all()
print(f"Total entrepots dans la DB: {entrepots.count()}")
print(f"Entrepots:")
for e in entrepots[:15]:
    print(f"  - {e.id}: {e.code} - {e.name}")

# Test 2: Clients
print("\n2. CLIENTS")
print("-" * 70)
clients = Client.objects.all()
print(f"Total clients dans la DB: {clients.count()}")
if clients.count() > 0:
    print(f"Premiers clients:")
    for c in clients[:10]:
        print(f"  - {c.id}: {c.nom} {c.prenom}")
else:
    print("  Aucun client dans la base!")

# Test 3: Tournees
print("\n3. TOURNEES")
print("-" * 70)
tournees = TourneeMobile.objects.all()
print(f"Total tournees dans la DB: {tournees.count()}")
if tournees.count() > 0:
    print(f"\nDerniere tournee:")
    derniere = tournees.last()
    print(f"  - ID: {derniere.id}")
    print(f"  - Numero: {derniere.numero_tournee}")
    print(f"  - Date: {derniere.date_tournee}")
    print(f"  - Livreur: {derniere.livreur.nom}")
    print(f"  - Statut: {derniere.statut}")
    print(f"  - Nombre d'arrets: {derniere.arrets.count()}")

    if derniere.arrets.count() > 0:
        print(f"\n  Arrets:")
        for arret in derniere.arrets.all():
            print(f"    - #{arret.ordre_passage}: {arret.client.nom} - {arret.statut}")

    # Verifier le rapport de caisse
    try:
        rapport = derniere.rapport_caisse
        print(f"\n  Rapport de caisse: OUI")
        print(f"    - Total encaissements: {rapport.total_encaissements}")
    except:
        print(f"\n  Rapport de caisse: NON")

print("\n" + "=" * 70)
print("VERIFICATION DE LA CONFIGURATION DES VIEWSETS")
print("=" * 70)

# Verifier la pagination par defaut
from rest_framework.settings import api_settings
print(f"\nPagination par defaut DRF:")
print(f"  - PAGE_SIZE: {api_settings.PAGE_SIZE}")
print(f"  - Default pagination class: {api_settings.DEFAULT_PAGINATION_CLASS}")

print("\n" + "=" * 70)
