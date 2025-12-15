#!/usr/bin/env python
"""
Script pour vérifier les livreurs et leurs vans assignés
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Livreur, Warehouse

print("\n" + "="*60)
print("VÉRIFICATION DES LIVREURS ET LEURS VANS")
print("="*60 + "\n")

# Lister tous les livreurs
livreurs = Livreur.objects.all()
print(f"📦 Total de livreurs: {livreurs.count()}\n")

if livreurs.count() == 0:
    print("⚠️ Aucun livreur trouvé dans la base de données!\n")
else:
    for livreur in livreurs:
        print(f"👤 Livreur: {livreur.get_full_name()} (ID: {livreur.id})")
        print(f"   Téléphone: {livreur.telephone}")
        print(f"   Véhicule: {livreur.vehicule_marque or 'N/A'}")

        if livreur.entrepot:
            print(f"   ✅ Van assigné: {livreur.entrepot.name} (Code: {livreur.entrepot.code})")
            print(f"      - ID Entrepot: {livreur.entrepot.id}")
        else:
            print(f"   ❌ PAS DE VAN ASSIGNÉ")
        print()

# Lister tous les entrepôts/vans disponibles
print("\n" + "-"*60)
print("ENTREPÔTS/VANS DISPONIBLES")
print("-"*60 + "\n")

entrepots = Warehouse.objects.all()
print(f"📦 Total d'entrepôts: {entrepots.count()}\n")

for entrepot in entrepots:
    print(f"🏢 Entrepôt: {entrepot.name} (Code: {entrepot.code})")
    print(f"   ID: {entrepot.id}")
    print(f"   Actif: {'Oui' if entrepot.is_active else 'Non'}")

    # Vérifier si assigné à un livreur
    livreurs_assignes = Livreur.objects.filter(entrepot=entrepot)
    if livreurs_assignes.exists():
        print(f"   ✅ Assigné à: {', '.join([l.nom for l in livreurs_assignes])}")
    else:
        print(f"   ⚠️ Non assigné à un livreur")
    print()

print("="*60)
