#!/usr/bin/env python
"""
Script pour configurer un utilisateur local avec une société
Utilisation: python manage.py shell < setup_local_user.py
OU: python setup_local_user.py
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.contrib.auth.models import User
from API.models import Company, UserProfile, Currency

print("=" * 60)
print("Configuration de l'utilisateur local pour le développement")
print("=" * 60)

# 1. Créer ou récupérer la devise par défaut
print("\n1. Vérification de la devise...")
currency, created = Currency.objects.get_or_create(
    code='DA',
    defaults={
        'name': 'Dinar Algérien',
        'symbol': 'DA',
        'is_default': True
    }
)
if created:
    print(f"   ✓ Devise créée: {currency}")
else:
    print(f"   ✓ Devise existe: {currency}")

# 2. Créer ou récupérer la société
print("\n2. Création/récupération de la société...")
company, created = Company.objects.get_or_create(
    code='DEMO',
    defaults={
        'name': 'Société de Démonstration',
        'email': 'demo@example.com',
        'telephone': '0123456789',
        'adresse': 'Alger, Algérie',
        'is_active': True
    }
)
if created:
    print(f"   ✓ Société créée: {company.name}")
else:
    print(f"   ✓ Société existe: {company.name}")

# 3. Lister les utilisateurs existants
print("\n3. Utilisateurs existants:")
users = User.objects.all()
if users.exists():
    for idx, user in enumerate(users, 1):
        has_profile = hasattr(user, 'profile')
        profile_company = user.profile.company if has_profile else None
        print(f"   {idx}. {user.username} (admin: {user.is_superuser}) - Profile: {has_profile} - Société: {profile_company}")
else:
    print("   Aucun utilisateur trouvé!")

# 4. Demander quel utilisateur configurer
print("\n4. Configuration du profil utilisateur...")
username = input("\nEntrez le nom d'utilisateur à configurer (ou appuyez sur Entrée pour créer un nouveau): ").strip()

if username:
    try:
        user = User.objects.get(username=username)
        print(f"   ✓ Utilisateur trouvé: {user.username}")
    except User.DoesNotExist:
        print(f"   ✗ Utilisateur '{username}' n'existe pas!")
        username = None

if not username:
    print("\n   Création d'un nouvel utilisateur...")
    username = input("   Nom d'utilisateur: ").strip() or "admin"
    email = input("   Email: ").strip() or "admin@example.com"
    password = input("   Mot de passe: ").strip() or "admin123"

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        user.set_password(password)
        user.save()
        print(f"   ✓ Utilisateur créé: {username} / {password}")
    else:
        print(f"   ✓ Utilisateur existe: {username}")

# 5. Créer ou mettre à jour le profil
print("\n5. Configuration du profil...")
profile, created = UserProfile.objects.get_or_create(
    user=user,
    defaults={
        'company': company,
        'role': 'admin'
    }
)

if created:
    print(f"   ✓ Profil créé pour {user.username}")
    print(f"   ✓ Société assignée: {company.name}")
else:
    if profile.company != company:
        profile.company = company
        profile.save()
        print(f"   ✓ Profil mis à jour: société changée vers {company.name}")
    else:
        print(f"   ✓ Profil existe déjà avec la bonne société")

# Résumé
print("\n" + "=" * 60)
print("✅ CONFIGURATION TERMINÉE")
print("=" * 60)
print(f"\nUtilisateur: {user.username}")
print(f"Société: {company.name} ({company.code})")
print(f"Rôle: {profile.role}")
print(f"\nVous pouvez maintenant vous connecter avec:")
print(f"  Username: {user.username}")
if username == "admin" and not User.objects.filter(username=username).first().has_usable_password():
    print(f"  Password: admin123")
print("\n✓ Les produits que vous créez seront automatiquement assignés à cette société")
print("✓ Vous ne verrez que les produits de votre société")
print("\n" + "=" * 60)
