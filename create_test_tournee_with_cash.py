"""
Script pour créer une tournée de test avec rapport de caisse et détail des billets
"""
import os
import django
import json
from decimal import Decimal
from datetime import date, time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import (
    LivreurDistribution, TourneeMobile, ArretTourneeMobile, RapportCaisseMobile
)
from API.models import Client

print("=" * 70)
print("CRÉATION D'UNE TOURNÉE DE TEST AVEC RAPPORT DE CAISSE")
print("=" * 70)

# Récupérer ou créer un livreur
try:
    livreur = LivreurDistribution.objects.filter(statut='actif').first()
    if not livreur:
        print("\n❌ Aucun livreur actif trouvé. Veuillez d'abord créer un livreur.")
        exit(1)
    print(f"\n✓ Livreur: {livreur.nom} (Matricule: {livreur.matricule})")
except Exception as e:
    print(f"\n❌ Erreur lors de la récupération du livreur: {e}")
    exit(1)

# Créer une tournée de test
tournee_numero = f"TOURNEE-TEST-{date.today().strftime('%Y%m%d')}-001"
tournee, created = TourneeMobile.objects.get_or_create(
    numero_tournee=tournee_numero,
    defaults={
        'livreur': livreur,
        'date_tournee': date.today(),
        'statut': 'terminee',
        'heure_debut': time(8, 0),
        'heure_fin': time(17, 30),
        'distance_km': Decimal('125.50'),
        'argent_depart': Decimal('5000.00'),
        'notes': 'Tournée de test avec rapport de caisse détaillé'
    }
)

if created:
    print(f"\n✓ Tournée créée: {tournee.numero_tournee}")
else:
    print(f"\n✓ Tournée existante: {tournee.numero_tournee}")

# Récupérer des clients pour créer des arrêts
clients = Client.objects.all()[:5]
if not clients:
    print("\n⚠️ Aucun client trouvé. Création d'arrêts non possible.")
else:
    print(f"\n✓ {len(clients)} clients trouvés pour créer des arrêts")

    # Créer des arrêts de test
    for idx, client in enumerate(clients, start=1):
        # Alterner entre livré et échec
        if idx <= 3:
            statut = 'livre'
        elif idx == 4:
            statut = 'echec'
        else:
            statut = 'en_attente'

        arret, created = ArretTourneeMobile.objects.get_or_create(
            tournee=tournee,
            client=client,
            ordre_passage=idx,
            defaults={
                'statut': statut,
                'heure_prevue': time(8 + idx, 0),
                'nom_receptionnaire': f'Réceptionnaire {idx}' if statut == 'livre' else '',
                'motif_echec': 'Client absent' if statut == 'echec' else ''
            }
        )

        if created:
            print(f"  - Arrêt #{idx}: {client.nom} - {statut}")

# Créer le rapport de caisse avec détail des billets
print("\n📊 Création du rapport de caisse...")

# Détail des billets (exemple avec des billets algériens)
detail_billets = {
    "2000": 10,  # 10 billets de 2000 DA = 20,000 DA
    "1000": 15,  # 15 billets de 1000 DA = 15,000 DA
    "500": 8,    # 8 billets de 500 DA = 4,000 DA
    "200": 20,   # 20 billets de 200 DA = 4,000 DA
    "100": 10,   # 10 billets de 100 DA = 1,000 DA
    "50": 5,     # 5 billets de 50 DA = 250 DA
}

# Calculer le total des espèces à partir du détail des billets
total_especes = sum(int(valeur) * quantite for valeur, quantite in detail_billets.items())
print(f"  Total espèces (calculé depuis détail billets): {total_especes:.2f} DA")

rapport, created = RapportCaisseMobile.objects.get_or_create(
    tournee=tournee,
    defaults={
        'fonds_depart': Decimal('5000.00'),
        'total_especes': Decimal(str(total_especes)),
        'total_cartes': Decimal('8500.00'),
        'total_cheques': Decimal('2500.00'),
        'total_credits': Decimal('1500.00'),
        'carburant': Decimal('450.00'),
        'reparations': Decimal('0.00'),
        'autres_depenses': Decimal('50.00'),
        'solde_final_reel': Decimal(str(5000 + total_especes - 500)),  # fonds_depart + espèces - dépenses
        'detail_billets_json': json.dumps(detail_billets),
        'statut': 'valide'
    }
)

# Recalculer les totaux
rapport.calculer_totaux()

if created:
    print(f"\n✅ Rapport de caisse créé avec succès!")
else:
    print(f"\n✅ Rapport de caisse mis à jour!")

print(f"\n📋 Résumé du rapport:")
print(f"  - Fonds de départ: {rapport.fonds_depart:.2f} DA")
print(f"  - Total encaissements: {rapport.total_encaissements:.2f} DA")
print(f"    * Espèces: {rapport.total_especes:.2f} DA")
print(f"    * Cartes: {rapport.total_cartes:.2f} DA")
print(f"    * Chèques: {rapport.total_cheques:.2f} DA")
print(f"    * À crédit: {rapport.total_credits:.2f} DA")
print(f"  - Total dépenses: {rapport.total_depenses:.2f} DA")
print(f"  - Solde final théorique: {rapport.solde_final_theorique:.2f} DA")
print(f"  - Solde final réel: {rapport.solde_final_reel:.2f} DA")
print(f"  - Écart: {rapport.ecart:.2f} DA")

print(f"\n💵 Détail des billets:")
for valeur, quantite in detail_billets.items():
    sous_total = int(valeur) * quantite
    print(f"  - {valeur} DA × {quantite} = {sous_total:.2f} DA")

print("\n" + "=" * 70)
print("✅ Données de test créées avec succès!")
print("=" * 70)
print(f"\nVous pouvez maintenant consulter la tournée '{tournee.numero_tournee}' dans l'interface web.")
print("Le rapport de caisse inclut le détail des billets par dénomination.")
print("\n💡 Pour voir les détails, allez dans 'Gestion des Tournées' et cliquez sur 'Voir les détails'.")
