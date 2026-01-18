#!/usr/bin/env python
"""
Script pour vérifier l'état de la commande 62
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

# Récupérer la commande
commande_id = 62
try:
    commande = CommandeClient.objects.get(id=commande_id)

    print("=" * 80)
    print(f"COMMANDE ID: {commande.id}")
    print(f"Référence: {commande.reference}")
    print(f"Montant Total HT (dans la commande): {commande.montant_total_ht}")
    print(f"Montant Total TTC (dans la commande): {commande.montant_total_ttc}")
    print("=" * 80)

    # Récupérer les lignes
    lignes = commande.lignes.all()
    print(f"\nNombre de lignes: {lignes.count()}")
    print("-" * 80)

    total_calcule_ht = 0
    total_calcule_ttc = 0

    for idx, ligne in enumerate(lignes, 1):
        print(f"\nLigne {idx}:")
        print(f"  ID: {ligne.id}")
        print(f"  Produit: {ligne.produit.designation} (ID: {ligne.produit.id})")
        print(f"  Quantité: {ligne.quantite}")
        print(f"  Prix Unitaire HT: {ligne.prix_unitaire_ht}")
        print(f"  Taux TVA: {ligne.taux_tva}%")
        print(f"  Montant HT (dans la ligne): {ligne.montant_ht}")
        print(f"  Montant TTC (dans la ligne): {ligne.montant_ttc}")

        # Calcul manuel
        calcul_ht = ligne.quantite * ligne.prix_unitaire_ht
        calcul_ttc = calcul_ht * (1 + ligne.taux_tva / 100)
        print(f"  Calcul manuel HT: {calcul_ht} (qté × prix)")
        print(f"  Calcul manuel TTC: {calcul_ttc}")

        total_calcule_ht += ligne.montant_ht
        total_calcule_ttc += ligne.montant_ttc

    print("-" * 80)
    print(f"\nTOTAUX CALCULÉS À PARTIR DES LIGNES:")
    print(f"  Total HT: {total_calcule_ht}")
    print(f"  Total TTC: {total_calcule_ttc}")

    print(f"\nCOMPARAISON:")
    print(f"  Commande HT: {commande.montant_total_ht} | Calculé: {total_calcule_ht} | Différence: {float(commande.montant_total_ht) - float(total_calcule_ht)}")
    print(f"  Commande TTC: {commande.montant_total_ttc} | Calculé: {total_calcule_ttc} | Différence: {float(commande.montant_total_ttc) - float(total_calcule_ttc)}")

    if float(commande.montant_total_ht) != float(total_calcule_ht):
        print("\n⚠️ PROBLÈME DÉTECTÉ : Les totaux de la commande ne correspondent pas aux lignes !")
        print("\nPour corriger, exécutez:")
        print(f"  commande.calculer_totaux()")
    else:
        print("\n✓ Les totaux sont corrects")

    print("=" * 80)

except CommandeClient.DoesNotExist:
    print(f"❌ Commande {commande_id} introuvable")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
