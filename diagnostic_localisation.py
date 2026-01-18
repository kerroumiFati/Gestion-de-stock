#!/usr/bin/env python
"""
Script de diagnostic de la localisation GPS
Vérifie l'état de la localisation des livreurs et clients
"""
import os
import sys
import django
from datetime import datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution
from API.models import Client, Secteur
from django.contrib.auth.models import Permission, ContentType

def main():
    print("=" * 80)
    print("DIAGNOSTIC DE LOCALISATION GPS")
    print("=" * 80)
    print()

    # 1. Vérifier les livreurs avec GPS
    print("📍 LIVREURS AVEC LOCALISATION GPS")
    print("-" * 80)
    total_livreurs = LivreurDistribution.objects.count()
    livreurs_avec_gps = LivreurDistribution.objects.filter(
        current_lat__isnull=False,
        current_lng__isnull=False
    )
    count_avec_gps = livreurs_avec_gps.count()

    print(f"Total de livreurs: {total_livreurs}")
    print(f"Livreurs avec GPS: {count_avec_gps}")
    print()

    if count_avec_gps > 0:
        print("Livreurs avec position GPS:")
        for livreur in livreurs_avec_gps:
            last_update = livreur.last_location_update
            if last_update:
                delta = datetime.now(last_update.tzinfo) - last_update
                age = f"{delta.total_seconds() / 60:.1f} minutes"
            else:
                age = "Jamais"

            print(f"  - {livreur.nom} ({livreur.matricule})")
            print(f"    Position: {livreur.current_lat}, {livreur.current_lng}")
            print(f"    Dernière MAJ: {age} ago")
            print(f"    Statut: {livreur.statut}")
            print()
    else:
        print("⚠️  AUCUN LIVREUR N'A DE POSITION GPS ENREGISTRÉE")
        print()
        print("Raisons possibles:")
        print("1. L'app mobile n'a pas envoyé de positions GPS")
        print("2. Les livreurs n'ont pas activé la localisation sur leur téléphone")
        print("3. Les livreurs n'ont pas ouvert l'app mobile récemment")
        print()

    # 2. Vérifier les clients avec GPS
    print("=" * 80)
    print("📍 CLIENTS AVEC LOCALISATION GPS")
    print("-" * 80)
    total_clients = Client.objects.count()
    clients_avec_gps = Client.objects.filter(
        lat__isnull=False,
        lng__isnull=False
    )
    count_clients_gps = clients_avec_gps.count()

    print(f"Total de clients: {total_clients}")
    print(f"Clients avec GPS: {count_clients_gps}")
    print()

    if count_clients_gps > 0:
        # Afficher quelques exemples
        print("Exemples de clients avec position GPS:")
        for client in clients_avec_gps[:5]:
            secteur = client.secteur.nom if client.secteur else "Aucun"
            print(f"  - {client.nom} {client.prenom}")
            print(f"    Position: {client.lat}, {client.lng}")
            print(f"    Secteur: {secteur}")
            print()
    else:
        print("⚠️  AUCUN CLIENT N'A DE POSITION GPS")
        print()

    # 3. Vérifier les secteurs
    print("=" * 80)
    print("📍 SECTEURS")
    print("-" * 80)
    total_secteurs = Secteur.objects.filter(is_active=True).count()
    print(f"Total de secteurs actifs: {total_secteurs}")
    print()

    for secteur in Secteur.objects.filter(is_active=True):
        clients_dans_secteur = secteur.clients.filter(lat__isnull=False, lng__isnull=False).count()
        print(f"  - {secteur.nom} ({secteur.code}): {clients_dans_secteur} clients avec GPS")
    print()

    # 4. Vérifier les permissions
    print("=" * 80)
    print("🔐 PERMISSIONS CARTE GPS")
    print("-" * 80)

    # Rechercher la permission view_carte_gps_livreurs
    try:
        perm = Permission.objects.get(codename='view_carte_gps_livreurs')
        print(f"✅ Permission trouvée: {perm.codename}")
        print(f"   Nom: {perm.name}")
        print(f"   Content Type: {perm.content_type}")

        # Compter les utilisateurs avec cette permission
        users_with_perm = perm.user_set.count()
        groups_with_perm = perm.group_set.count()
        print(f"   Utilisateurs directs: {users_with_perm}")
        print(f"   Groupes: {groups_with_perm}")

    except Permission.DoesNotExist:
        print("❌ Permission 'view_carte_gps_livreurs' NON TROUVÉE")
        print()
        print("La permission doit être créée pour accéder à la carte GPS.")
        print()
        print("Solutions:")
        print("1. Créer la permission manuellement")
        print("2. Donner les droits superuser à l'utilisateur")
        print()

    # 5. URL d'accès
    print("=" * 80)
    print("🌐 ACCÈS À LA CARTE")
    print("-" * 80)
    print("URL: /admindash/livreurs-map/")
    print()
    print("Accessible depuis le menu:")
    print("  Distribution > Carte GPS Livreurs")
    print()

    # 6. Recommandations
    print("=" * 80)
    print("💡 RECOMMANDATIONS")
    print("-" * 80)

    if count_avec_gps == 0:
        print("⚠️  PROBLÈME PRINCIPAL: Aucun livreur n'a de position GPS")
        print()
        print("Actions à entreprendre:")
        print("1. Vérifier que les livreurs ont l'app mobile installée")
        print("2. S'assurer qu'ils ont activé les permissions de localisation")
        print("3. Vérifier qu'ils sont connectés à l'app mobile")
        print("4. Vérifier les logs de l'app mobile pour voir si les positions sont envoyées")
        print()
        print("Pour tester localement:")
        print("  - Ouvrir l'app mobile")
        print("  - Se connecter en tant que livreur")
        print("  - L'app devrait envoyer la position GPS toutes les 30 secondes")
        print()
    else:
        print("✅ La localisation GPS fonctionne correctement")
        print(f"   {count_avec_gps} livreur(s) avec position GPS active")
        print(f"   {count_clients_gps} client(s) avec coordonnées GPS")
        print()

    if count_clients_gps < total_clients * 0.5:
        print("⚠️  Moins de 50% des clients ont des coordonnées GPS")
        print("   Recommandation: Ajouter les coordonnées GPS des clients")
        print("   depuis la page Clients > Modifier > Localisation")
        print()

    print("=" * 80)
    print("FIN DU DIAGNOSTIC")
    print("=" * 80)

if __name__ == '__main__':
    main()
