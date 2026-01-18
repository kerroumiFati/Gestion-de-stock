#!/usr/bin/env python
"""
Script pour activer la localisation GPS pour les tests
Met à jour les positions GPS des livreurs avec des coordonnées récentes
"""
import os
import sys
import django
from datetime import datetime
from django.utils import timezone

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution
from API.models import Client

def main():
    print("=" * 80)
    print("ACTIVATION DE LA LOCALISATION GPS POUR LES TESTS")
    print("=" * 80)
    print()

    # Coordonnées de test (Alger, Oran, etc.)
    positions_test = [
        {"lat": 36.7538, "lng": 3.0588, "ville": "Alger Centre"},
        {"lat": 36.7135, "lng": 3.2111, "ville": "Alger Est"},
        {"lat": 36.7907, "lng": 3.0580, "ville": "Alger Nord"},
        {"lat": 35.6987, "lng": -0.6183, "ville": "Oran Centre"},
        {"lat": 35.7057, "lng": -0.6336, "ville": "Oran Ouest"},
    ]

    # 1. Mettre à jour les positions des livreurs
    print("📍 MISE À JOUR DES POSITIONS DES LIVREURS")
    print("-" * 80)

    livreurs = LivreurDistribution.objects.filter(statut='actif')
    updated_count = 0

    for i, livreur in enumerate(livreurs):
        # Utiliser une position différente pour chaque livreur
        pos = positions_test[i % len(positions_test)]

        # Ajouter une légère variation pour que tous ne soient pas au même endroit
        variation_lat = (i * 0.001) - 0.002
        variation_lng = (i * 0.001) - 0.002

        new_lat = pos['lat'] + variation_lat
        new_lng = pos['lng'] + variation_lng

        livreur.current_lat = new_lat
        livreur.current_lng = new_lng
        livreur.last_location_update = timezone.now()
        livreur.save()

        updated_count += 1
        print(f"✅ {livreur.nom} ({livreur.matricule})")
        print(f"   Position: {new_lat:.6f}, {new_lng:.6f} ({pos['ville']})")
        print(f"   Dernière MAJ: {livreur.last_location_update}")
        print()

    print(f"Total de livreurs mis à jour: {updated_count}")
    print()

    # 2. Mettre à jour quelques clients si nécessaire
    print("=" * 80)
    print("📍 VÉRIFICATION DES CLIENTS")
    print("-" * 80)

    clients_sans_gps = Client.objects.filter(lat__isnull=True)
    count_sans_gps = clients_sans_gps.count()

    if count_sans_gps > 0:
        print(f"⚠️  {count_sans_gps} clients sans coordonnées GPS")
        print()
        print("Pour ajouter des coordonnées GPS aux clients:")
        print("1. Aller dans Clients > Modifier un client")
        print("2. Cliquer sur 'Localisation' ")
        print("3. Cliquer sur la carte pour définir la position")
        print("   OU entrer manuellement lat/lng")
        print()
    else:
        print("✅ Tous les clients ont des coordonnées GPS")
        print()

    # 3. Résumé et prochaines étapes
    print("=" * 80)
    print("✅ LOCALISATION GPS ACTIVÉE")
    print("=" * 80)
    print()
    print(f"✔️  {updated_count} livreurs avec position GPS actuelle")
    print()
    print("ACCÈS À LA CARTE GPS:")
    print("-" * 80)
    print("1. Se connecter au logiciel web")
    print("2. Aller dans le menu: Distribution > Carte GPS Livreurs")
    print("   OU accéder directement: /admindash/livreurs-map/")
    print()
    print("REMARQUES:")
    print("-" * 80)
    print("⚠️  Ces positions sont pour les TESTS uniquement")
    print()
    print("En production, les positions seront automatiquement")
    print("mises à jour par l'app mobile toutes les 30 secondes.")
    print()
    print("ACTIVATION EN PRODUCTION:")
    print("-" * 80)
    print("1. Les livreurs doivent:")
    print("   - Installer l'app mobile 'UltraThink'")
    print("   - Se connecter avec leurs identifiants")
    print("   - Autoriser la localisation GPS")
    print()
    print("2. L'app mobile enverra automatiquement:")
    print("   - La position GPS toutes les 30 secondes")
    print("   - Les positions sont sauvegardées localement si pas de connexion")
    print("   - Synchronisation automatique quand la connexion revient")
    print()
    print("=" * 80)

if __name__ == '__main__':
    main()
