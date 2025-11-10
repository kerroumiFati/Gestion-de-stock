#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script SIMPLE pour créer des sessions/clients
Pas besoin de serveur web !
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.contrib.auth import get_user_model
from API.models import Company, UserProfile

User = get_user_model()

def creer_session():
    """Créer une nouvelle session/client"""

    print("\n" + "="*60)
    print("       CRÉER UNE NOUVELLE SESSION / CLIENT")
    print("="*60 + "\n")

    # Demander les informations
    nom = input("Nom de l'entreprise : ")
    code = input("Code unique (ex: CLI01) : ").upper().strip()
    username = input("Nom d'utilisateur admin : ").strip()
    password = input("Mot de passe : ")

    print("\nCréation en cours...\n")

    try:
        # Vérifier si le code existe
        if Company.objects.filter(code=code).exists():
            print(f"❌ ERREUR : Le code '{code}' existe déjà !")
            print("\nCodes existants :")
            for c in Company.objects.all():
                print(f"   - {c.code}")
            return

        # Vérifier si le username existe
        if User.objects.filter(username=username).exists():
            print(f"❌ ERREUR : Le nom d'utilisateur '{username}' existe déjà !")
            return

        # Créer la company
        company = Company.objects.create(
            name=nom,
            code=code,
            is_active=True
        )
        print(f"✓ Entreprise créée : {company.name}")

        # Créer l'utilisateur
        user = User.objects.create_user(
            username=username,
            password=password,
            is_staff=True,
            is_active=True
        )
        print(f"✓ Utilisateur créé : {user.username}")

        # Créer le profil
        profile = UserProfile.objects.create(
            user=user,
            company=company,
            role='admin'
        )
        print(f"✓ Profil créé")

        print("\n" + "="*60)
        print("✅ SESSION CRÉÉE AVEC SUCCÈS !")
        print("="*60)
        print(f"\nEntreprise : {company.name}")
        print(f"Code       : {company.code}")
        print(f"\nConnexion :")
        print(f"  URL      : http://localhost:8000/")
        print(f"  Username : {username}")
        print(f"  Password : {password}")
        print("\n" + "="*60)

    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()


def lister_sessions():
    """Lister toutes les sessions existantes"""

    print("\n" + "="*60)
    print("       LISTE DES SESSIONS / CLIENTS")
    print("="*60 + "\n")

    companies = Company.objects.all().order_by('name')

    if not companies.exists():
        print("Aucune session trouvée.\n")
        return

    for i, company in enumerate(companies, 1):
        users_count = company.users.count()
        print(f"{i}. {company.name} ({company.code})")
        print(f"   Utilisateurs : {users_count}")

        # Lister les utilisateurs
        for profile in company.users.all():
            print(f"      → {profile.user.username} ({profile.role})")
        print()

    print(f"Total : {companies.count()} session(s)\n")


def menu():
    """Menu principal"""

    while True:
        print("\n" + "="*60)
        print("       GESTION DES SESSIONS / CLIENTS")
        print("="*60)
        print("\n1. Créer une nouvelle session")
        print("2. Lister les sessions existantes")
        print("3. Quitter")
        print()

        choix = input("Votre choix (1-3) : ").strip()

        if choix == '1':
            creer_session()
        elif choix == '2':
            lister_sessions()
        elif choix == '3':
            print("\nAu revoir !")
            break
        else:
            print("\n❌ Choix invalide. Tapez 1, 2 ou 3.")


if __name__ == '__main__':
    try:
        menu()
    except KeyboardInterrupt:
        print("\n\nInterrompu par l'utilisateur. Au revoir !")
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
