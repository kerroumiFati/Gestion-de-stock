#!/usr/bin/env python
"""
Script pour créer un livreur et lui assigner un van
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Livreur, Warehouse, User, Company
from django.contrib.auth.hashers import make_password

print("\n" + "="*60)
print("CONFIGURATION LIVREUR + VAN")
print("="*60 + "\n")

# Récupérer ou créer une company par défaut
company, created = Company.objects.get_or_create(
    name="NextGate",
    defaults={
        'code': 'NEXTGATE',
        'adresse': 'Algérie',
        'telephone': '0000000000',
        'email': 'contact@nextgate.dz'
    }
)
if created:
    print(f"✅ Company créée: {company.name}")
else:
    print(f"ℹ️  Company existante: {company.name}")

# Vérifier s'il y a des entrepôts/vans disponibles
vans = Warehouse.objects.filter(is_active=True)
print(f"\n📦 Entrepôts/Vans disponibles: {vans.count()}")

if vans.count() == 0:
    # Créer un van pour le livreur
    van = Warehouse.objects.create(
        company=company,
        name="Van Livreur 1",
        code="VAN-001",
        is_active=True
    )
    print(f"✅ Van créé: {van.name} (Code: {van.code})")
else:
    # Utiliser le premier van disponible
    van = vans.first()
    print(f"ℹ️  Van existant sélectionné: {van.name} (Code: {van.code})")

# Vérifier s'il existe déjà des livreurs
livreurs_existants = Livreur.objects.all()
print(f"\n👤 Livreurs existants: {livreurs_existants.count()}")

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
        print(f"✅ User créé: {user.username}")
    else:
        print(f"ℹ️  User existant: {user.username}")

    # Créer le livreur
    livreur = Livreur.objects.create(
        company=company,
        nom="Benali",
        prenom="Ahmed",
        telephone="0555123456",
        email="livreur1@nextgate.dz",
        vehicule_type="Camionnette",
        vehicule_marque="Renault Kangoo",
        immatriculation="16-12345-AL",
        capacite_charge=500,
        entrepot=van,  # ASSIGNER LE VAN!
        is_active=True,
        is_disponible=True
    )
    print(f"✅ Livreur créé: {livreur.get_full_name()}")
    print(f"   - ID: {livreur.id}")
    print(f"   - Van assigné: {van.name} ({van.code})")
    print(f"   - Username: {username}")
    print(f"   - Mot de passe: livreur123")
else:
    # Assigner le van au premier livreur s'il n'en a pas
    livreur = livreurs_existants.first()

    if not livreur.entrepot:
        livreur.entrepot = van
        livreur.save()
        print(f"✅ Van assigné au livreur existant: {livreur.get_full_name()}")
        print(f"   - ID: {livreur.id}")
        print(f"   - Van: {van.name} ({van.code})")
    else:
        print(f"ℹ️  Le livreur {livreur.get_full_name()} a déjà un van: {livreur.entrepot.name}")

print("\n" + "="*60)
print("✅ CONFIGURATION TERMINÉE")
print("="*60)
print("\nVous pouvez maintenant:")
print("1. Vous connecter avec:")
print("   - Username: livreur1")
print("   - Password: livreur123")
print("2. Utiliser l'app mobile pour synchroniser le stock van")
print()
