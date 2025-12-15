#!/usr/bin/env python
"""
Script pour créer un LivreurDistribution et lui assigner un van
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution
from API.models import Warehouse, User
from django.contrib.auth.hashers import make_password

print("\n" + "="*60)
print("CONFIGURATION LIVREUR DISTRIBUTION + VAN")
print("="*60 + "\n")

# Vérifier s'il y a des entrepôts/vans disponibles
vans = Warehouse.objects.filter(is_active=True)
print(f"📦 Entrepôts/Vans disponibles: {vans.count()}")

if vans.count() == 0:
    print("❌ Aucun van disponible! Créez d'abord un van.")
    exit(1)

# Utiliser le premier van disponible
van = vans.first()
print(f"✅ Van sélectionné: {van.name} (Code: {van.code}, ID: {van.id})")

# Vérifier s'il existe déjà des livreurs distribution
livreurs_existants = LivreurDistribution.objects.all()
print(f"\n👤 Livreurs Distribution existants: {livreurs_existants.count()}")

if livreurs_existants.count() == 0:
    # Créer un user pour le livreur
    username = "livreur1"
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': 'livreur1@nextgate.dz',
            'first_name': 'Ahmed',
            'last_name': 'Benali',
            'password': make_password('livreur123')  # Mot de passe: livreur123
        }
    )

    if created:
        print(f"\n✅ User créé: {user.username}")
    else:
        print(f"\nℹ️  User existant: {user.username}")

    # Créer le livreur distribution
    livreur = LivreurDistribution.objects.create(
        user=user,
        matricule="LIV001",
        nom="Ahmed Benali",
        telephone="0555123456",
        email="livreur1@nextgate.dz",
        vehicule_immatriculation="16-12345-AL",
        vehicule_marque="Renault Kangoo",
        entrepot=van,  # ASSIGNER LE VAN!
        statut='actif'
    )
    print(f"\n✅ LivreurDistribution créé:")
    print(f"   - ID: {livreur.id}")
    print(f"   - Matricule: {livreur.matricule}")
    print(f"   - Nom: {livreur.nom}")
    print(f"   - Van assigné: {van.name} ({van.code})")
    print(f"   - User: {username}")
    print(f"   - Mot de passe: livreur123")
else:
    # Assigner le van au premier livreur s'il n'en a pas
    livreur = livreurs_existants.first()

    if not livreur.entrepot:
        livreur.entrepot = van
        livreur.save()
        print(f"\n✅ Van assigné au livreur existant:")
        print(f"   - ID: {livreur.id}")
        print(f"   - Matricule: {livreur.matricule}")
        print(f"   - Nom: {livreur.nom}")
        print(f"   - Van: {van.name} ({van.code})")
    else:
        print(f"\nℹ️  Le livreur {livreur.nom} a déjà un van: {livreur.entrepot.name}")
        print(f"   - ID Livreur: {livreur.id}")
        print(f"   - Van actuel: {livreur.entrepot.name} ({livreur.entrepot.code})")

print("\n" + "="*60)
print("✅ CONFIGURATION TERMINÉE")
print("="*60)
print("\nVous pouvez maintenant:")
print("1. Vous connecter avec:")
print("   - Username: livreur1")
print("   - Password: livreur123")
print("2. Utiliser l'app mobile pour synchroniser le stock van")
print(f"3. L'endpoint stock_van utilisera le livreur ID: {livreur.id}")
print()
