"""
Script pour créer une tournée de test pour aujourd'hui
"""
import os
import django
from datetime import date, time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution, TourneeMobile, ArretTourneeMobile
from API.models import Client

print("=" * 80)
print("CRÉATION D'UNE TOURNÉE DE TEST POUR AUJOURD'HUI")
print("=" * 80)

# 1. Vérifier qu'il y a un livreur avec compte utilisateur
livreurs_avec_user = LivreurDistribution.objects.filter(user__isnull=False, statut='actif')

if not livreurs_avec_user.exists():
    print("\n❌ ERREUR : Aucun livreur actif avec compte utilisateur !")
    print("   Créez d'abord un compte pour un livreur.")
    exit(1)

livreur = livreurs_avec_user.first()
print(f"\n✅ Livreur sélectionné : {livreur.nom} ({livreur.matricule})")
print(f"   Username: {livreur.user.username}")

# 2. Vérifier qu'il y a des clients
clients = Client.objects.all()
if not clients.exists():
    print("\n❌ ERREUR : Aucun client dans la base !")
    print("   Créez d'abord des clients via Django Admin ou l'API.")
    exit(1)

print(f"\n✅ {clients.count()} client(s) trouvé(s)")

# 3. Créer la tournée pour aujourd'hui
today = date.today()
print(f"\n📅 Création de la tournée pour {today}...")

tournee = TourneeMobile.objects.create(
    livreur=livreur,
    date_tournee=today,
    numero_tournee=f"T-TEST-{today.strftime('%Y%m%d')}",
    statut='planifiee',
    heure_debut=time(8, 0),
    heure_fin=time(17, 0),
    argent_depart=500.00,
    notes="Tournée de test créée automatiquement"
)

print(f"✅ Tournée créée : {tournee.numero_tournee}")
print(f"   ID: {tournee.id}")
print(f"   Statut: {tournee.statut}")
print(f"   Argent de départ: {tournee.argent_depart} DA")

# 4. Ajouter des arrêts
print(f"\n📍 Ajout d'arrêts...")

# Prendre les 3 premiers clients
for i, client in enumerate(clients[:3], 1):
    arret = ArretTourneeMobile.objects.create(
        tournee=tournee,
        client=client,
        ordre_passage=i,
        statut='en_attente',
        heure_prevue=time(9 + i, 0)
    )
    print(f"   ✅ Arrêt {i} : {client.prenom} {client.nom}")

print(f"\n✅ {tournee.arrets.count()} arrêt(s) ajouté(s)")

# 5. Résumé
print("\n" + "=" * 80)
print("RÉSUMÉ")
print("=" * 80)
print(f"\n✅ Tournée créée avec succès !")
print(f"\n📱 Dans l'app mobile :")
print(f"   - Connectez-vous avec : {livreur.user.username}")
print(f"   - Vous verrez cette tournée dans la liste")
print(f"   - Date : {today}")
print(f"   - Arrêts : {tournee.arrets.count()}")
print(f"   - Argent de départ : {tournee.argent_depart} DA")

print("\n💡 Commandes utiles :")
print(f"   - Voir la tournée : GET /API/distribution/tournees/{tournee.id}/")
print(f"   - Démarrer : POST /API/distribution/tournees/{tournee.id}/demarrer/")
print(f"   - Terminer : POST /API/distribution/tournees/{tournee.id}/terminer/")

print("\n")
