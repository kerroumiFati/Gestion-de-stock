#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution, TourneeMobile
from django.contrib.auth.models import User

print("=" * 80)
print("RECHERCHE DE 'said2'")
print("=" * 80)

# Chercher tous les users qui contiennent "said"
users_said = User.objects.filter(username__icontains='said')
print(f"\n[1] Users contenant 'said': {users_said.count()}")
for user in users_said:
    print(f"    - Username: {user.username}, ID: {user.id}")

# Chercher tous les livreurs
print(f"\n[2] Tous les livreurs disponibles:")
livreurs = LivreurDistribution.objects.all()
print(f"    Total: {livreurs.count()} livreurs")
for liv in livreurs:
    username = liv.user.username if liv.user else "Pas de user"
    print(f"    - ID: {liv.id}, Nom: {liv.nom}, Username: {username}, Matricule: {liv.matricule}")

# Chercher un livreur avec nom contenant "said"
livreurs_said = LivreurDistribution.objects.filter(nom__icontains='said')
print(f"\n[3] Livreurs avec nom contenant 'said': {livreurs_said.count()}")
for liv in livreurs_said:
    username = liv.user.username if liv.user else "Pas de user"
    print(f"    - ID: {liv.id}, Nom: {liv.nom}, Username: {username}")

    # Vérifier les clients assignés
    clients = liv.clients_assignes.all()
    print(f"      Clients assignés: {clients.count()}")
    for client in clients:
        print(f"        * {client.nom} {client.prenom} - {client.telephone}")

    # Vérifier les tournées
    tournees = TourneeMobile.objects.filter(livreur=liv)
    print(f"      Tournées: {tournees.count()}")
    for tournee in tournees:
        print(f"        * {tournee.numero_tournee} - {tournee.date_tournee} - Statut: {tournee.statut}")
        print(f"          Arrêts: {tournee.arrets.count()}")

print("\n" + "=" * 80)
