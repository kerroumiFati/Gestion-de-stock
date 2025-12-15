#!/usr/bin/env python
"""
Script pour lister tous les livreurs et leurs users associés
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution

print("\n" + "="*70)
print("LISTE DES LIVREURS DISTRIBUTION ET LEURS USERS")
print("="*70 + "\n")

livreurs = LivreurDistribution.objects.all()
print(f"📦 Total de livreurs: {livreurs.count()}\n")

for livreur in livreurs:
    print(f"👤 Livreur: {livreur.nom} (Matricule: {livreur.matricule})")
    print(f"   ID: {livreur.id}")
    print(f"   Téléphone: {livreur.telephone}")
    print(f"   Email: {livreur.email}")
    print(f"   Statut: {livreur.statut}")

    if livreur.user:
        print(f"   ✅ User associé:")
        print(f"      - Username: {livreur.user.username}")
        print(f"      - Email: {livreur.user.email}")
        print(f"      - Actif: {'Oui' if livreur.user.is_active else 'Non'}")
    else:
        print(f"   ❌ PAS DE USER ASSOCIÉ")

    if livreur.entrepot:
        print(f"   ✅ Van assigné: {livreur.entrepot.name} (Code: {livreur.entrepot.code}, ID: {livreur.entrepot.id})")
    else:
        print(f"   ❌ PAS DE VAN ASSIGNÉ")

    print()

print("="*70)
