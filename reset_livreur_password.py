#!/usr/bin/env python
"""
Script pour réinitialiser le mot de passe d'un livreur
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution
from django.contrib.auth.hashers import make_password

print("\n" + "="*70)
print("RÉINITIALISATION DU MOT DE PASSE DU LIVREUR")
print("="*70 + "\n")

# Chercher un livreur avec un van assigné
livreur = LivreurDistribution.objects.filter(
    entrepot__isnull=False,  # Doit avoir un van
    user__isnull=False       # Doit avoir un user
).first()

if not livreur:
    print("❌ Aucun livreur avec van et user trouvé!")
    exit(1)

print(f"✅ Livreur sélectionné:")
print(f"   - Nom: {livreur.nom}")
print(f"   - Matricule: {livreur.matricule}")
print(f"   - Username: {livreur.user.username}")
print(f"   - Van: {livreur.entrepot.name} ({livreur.entrepot.code})")

# Réinitialiser le mot de passe
nouveau_password = "livreur123"
livreur.user.password = make_password(nouveau_password)
livreur.user.save()

print(f"\n✅ Mot de passe réinitialisé!")
print(f"\n{'='*70}")
print("INFORMATIONS DE CONNEXION")
print(f"{'='*70}")
print(f"Username: {livreur.user.username}")
print(f"Password: {nouveau_password}")
print(f"ID Livreur: {livreur.id}")
print(f"Van: {livreur.entrepot.name} ({livreur.entrepot.code})")
print(f"{'='*70}\n")
