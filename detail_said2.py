#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution, TourneeMobile

print("=" * 80)
print("DÉTAILS COMPLETS POUR LE LIVREUR 'SAID2'")
print("=" * 80)

livreur = LivreurDistribution.objects.get(id=6)

print(f"\n📋 INFORMATIONS DU LIVREUR")
print(f"   ID: {livreur.id}")
print(f"   Nom: {livreur.nom}")
print(f"   Matricule: {livreur.matricule}")
print(f"   Username: {livreur.user.username if livreur.user else 'Pas de user'}")
print(f"   Email: {livreur.email}")
print(f"   Téléphone: {livreur.telephone}")
print(f"   Statut: {livreur.statut}")

print(f"\n👥 CLIENTS ASSIGNÉS ({livreur.clients_assignes.count()})")
clients = livreur.clients_assignes.all()
if clients.exists():
    for i, client in enumerate(clients, 1):
        print(f"   {i}. ID: {client.id}")
        print(f"      Nom: {client.nom} {client.prenom}")
        print(f"      Téléphone: {client.telephone}")
        print(f"      Email: {client.email or 'Non défini'}")
        print(f"      Adresse: {client.adresse}")
        print()
else:
    print("   ❌ Aucun client assigné")

print(f"\n🚚 TOURNÉES ({TourneeMobile.objects.filter(livreur=livreur).count()})")
tournees = TourneeMobile.objects.filter(livreur=livreur).order_by('-date_tournee')
if tournees.exists():
    for i, tournee in enumerate(tournees, 1):
        print(f"   {i}. Numéro: {tournee.numero_tournee}")
        print(f"      ID: {tournee.id}")
        print(f"      Date: {tournee.date_tournee}")
        print(f"      Statut: {tournee.statut}")
        print(f"      Argent de départ: {tournee.argent_depart} MAD")
        print(f"      Heure début: {tournee.heure_debut or 'Non démarré'}")
        print(f"      Heure fin: {tournee.heure_fin or 'Non terminé'}")
        print(f"      Distance: {tournee.distance_km or 0} km")
        print(f"      Clôturée: {'Oui' if tournee.est_cloturee else 'Non'}")

        arrets = tournee.arrets.all().order_by('ordre_passage')
        print(f"      Arrêts: {arrets.count()}")

        if arrets.exists():
            for j, arret in enumerate(arrets, 1):
                print(f"         {j}. Ordre: {arret.ordre_passage}")
                print(f"            Client: {arret.client.nom if arret.client else 'Client supprimé'}")
                print(f"            Adresse: {arret.client.adresse if arret.client else 'N/A'}")
                print(f"            Statut: {arret.statut}")
                print(f"            Heure prévue: {arret.heure_prevue or 'Non défini'}")
                print(f"            Heure arrivée: {arret.heure_arrivee or 'Pas encore arrivé'}")
        else:
            print(f"         ⚠️ Aucun arrêt défini")
        print()
else:
    print("   ❌ Aucune tournée")

print("=" * 80)

# Test de l'endpoint API
print("\n🔍 TEST API ENDPOINT")
print(f"   URL à utiliser: /API/distribution/livreurs/{livreur.id}/clients_assignes/")
print(f"   Nombre de clients attendus: {livreur.clients_assignes.count()}")
