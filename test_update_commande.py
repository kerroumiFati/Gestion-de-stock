#!/usr/bin/env python
"""
Script pour tester la mise à jour de la commande 62
"""
import os
import sys
import django

# Ajouter le répertoire du projet au path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import CommandeClient, LigneCommandeClient
from API.distribution_serializers import CommandeClientCreateSerializer

# Récupérer la commande
commande_id = 62
commande = CommandeClient.objects.get(id=commande_id)

print("=" * 80)
print("AVANT LA MISE À JOUR:")
print(f"Commande ID: {commande.id}")
print(f"Montant Total HT: {commande.montant_total_ht}")
print(f"Montant Total TTC: {commande.montant_total_ttc}")

lignes = commande.lignes.all()
for idx, ligne in enumerate(lignes, 1):
    print(f"  Ligne {idx}: Qté={ligne.quantite}, Prix HT={ligne.prix_unitaire_ht}, Montant HT={ligne.montant_ht}")

print("=" * 80)

# Données de test (simuler ce qui vient du frontend)
data = {
    'date_livraison_souhaitee': '2026-01-07',
    'type_paiement': 'non_paye',
    'notes': '',
    'lignes': [
        {
            'produit': 11,  # ID du produit
            'quantite': 1,   # CHANGÉ de 2 à 1
            'prix_unitaire_ht': 90,
            'taux_tva': 0
        }
    ]
}

print("\nDATA À ENVOYER:")
print(data)
print("=" * 80)

# Tester la mise à jour avec le serializer
print("\nAPPEL DU SERIALIZER UPDATE...")
serializer = CommandeClientCreateSerializer(commande, data=data, partial=True)

if serializer.is_valid():
    print("✓ Validation OK")
    print(f"  Validated data: {serializer.validated_data}")

    print("\n  Appel de serializer.save()...")
    updated_commande = serializer.save()

    print(f"✓ Save terminé, instance retournée: {updated_commande.id}")
else:
    print("❌ Erreurs de validation:")
    print(serializer.errors)
    sys.exit(1)

print("=" * 80)

# Recharger depuis la DB
commande.refresh_from_db()

print("\nAPRÈS LA MISE À JOUR:")
print(f"Commande ID: {commande.id}")
print(f"Montant Total HT: {commande.montant_total_ht}")
print(f"Montant Total TTC: {commande.montant_total_ttc}")

lignes = commande.lignes.all()
print(f"Nombre de lignes: {lignes.count()}")
for idx, ligne in enumerate(lignes, 1):
    print(f"  Ligne {idx}: ID={ligne.id}, Qté={ligne.quantite}, Prix HT={ligne.prix_unitaire_ht}, Montant HT={ligne.montant_ht}")

print("=" * 80)

# Vérifier le résultat
if lignes.count() == 1 and float(lignes[0].quantite) == 1.0:
    print("\n✅ SUCCÈS ! La quantité a été mise à jour à 1")
    if float(commande.montant_total_ht) == 90.0:
        print("✅ Les totaux ont été correctement recalculés (90 DA)")
    else:
        print(f"⚠️ Les totaux sont incorrects: {commande.montant_total_ht} au lieu de 90")
else:
    print("\n❌ ÉCHEC ! La quantité n'a pas été mise à jour")
    print(f"   Quantité actuelle: {lignes[0].quantite if lignes.count() > 0 else 'N/A'}")

print("=" * 80)
