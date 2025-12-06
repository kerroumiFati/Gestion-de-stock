#!/usr/bin/env python
"""
Script pour vérifier et créer un utilisateur administrateur
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.contrib.auth.models import User
from API.models import Company, UserProfile

print("=" * 80)
print("VÉRIFICATION DES UTILISATEURS".center(80))
print("=" * 80)

# Lister tous les utilisateurs
users = User.objects.all()
print(f"\n📊 Nombre total d'utilisateurs : {users.count()}\n")

if users.exists():
    print("👥 Liste des utilisateurs :\n")
    for user in users:
        is_super = "🔑 SUPERADMIN" if user.is_superuser else "👤 Utilisateur"
        is_active = "✓ Actif" if user.is_active else "✗ Inactif"
        print(f"  {is_super} - {user.username}")
        print(f"     Email: {user.email or 'Non défini'}")
        print(f"     Statut: {is_active}")
        print(f"     Staff: {'Oui' if user.is_staff else 'Non'}")

        # Vérifier le profil
        try:
            profile = UserProfile.objects.get(user=user)
            print(f"     Entreprise: {profile.company.name}")
            print(f"     Rôle: {profile.get_role_display()}")
        except UserProfile.DoesNotExist:
            print(f"     ⚠️ Pas de profil associé")
        print()

print("=" * 80)
print("\n💡 RECOMMANDATIONS :\n")

# Vérifier si test_admin existe
test_admin = User.objects.filter(username='test_admin').first()
if test_admin:
    print("✓ L'utilisateur 'test_admin' existe")
    print("  Username: test_admin")
    print("  Password: test123")
    print()

# Vérifier s'il y a un superutilisateur
superusers = User.objects.filter(is_superuser=True)
if superusers.exists():
    print(f"✓ {superusers.count()} superutilisateur(s) trouvé(s)")
else:
    print("⚠️ Aucun superutilisateur trouvé")
    print("\n🔧 Création d'un superutilisateur...")

    # Créer un superutilisateur
    admin_user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123',
        first_name='Admin',
        last_name='System'
    )
    print("✓ Superutilisateur créé avec succès !")
    print("\n🔐 IDENTIFIANTS DE CONNEXION :")
    print("   Username: admin")
    print("   Password: admin123")

    # Créer une entreprise par défaut si nécessaire
    company, created = Company.objects.get_or_create(
        code='DEFAULT',
        defaults={
            'name': 'Entreprise par défaut',
            'email': 'contact@default.com',
            'is_active': True
        }
    )
    if created:
        print(f"\n✓ Entreprise '{company.name}' créée")

    # Créer le profil utilisateur
    profile, created = UserProfile.objects.get_or_create(
        user=admin_user,
        defaults={
            'company': company,
            'role': 'admin'
        }
    )
    if created:
        print(f"✓ Profil utilisateur créé pour l'entreprise '{company.name}'")

print("\n" + "=" * 80)
print("RÉSUMÉ DES COMPTES DISPONIBLES".center(80))
print("=" * 80 + "\n")

all_users = User.objects.filter(is_active=True)
for user in all_users:
    if user.is_superuser:
        print(f"🔑 SUPERADMIN: {user.username}")
        if user.username == 'admin':
            print(f"   Password: admin123")
        elif user.username == 'test_admin':
            print(f"   Password: test123")
        print()

print("=" * 80)
