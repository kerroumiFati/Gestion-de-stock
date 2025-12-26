"""
Script pour corriger les totaux incorrects des commandes clients mobiles
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import CommandeClient
from decimal import Decimal

def corriger_commandes():
    print("=" * 80)
    print("CORRECTION DES TOTAUX DES COMMANDES")
    print("=" * 80)
    print()

    # Récupérer toutes les commandes
    commandes = CommandeClient.objects.all()
    total_commandes = commandes.count()
    commandes_corrigees = 0

    print(f"📊 {total_commandes} commande(s) à vérifier\n")

    for commande in commandes:
        # Calculer le total attendu
        lignes = commande.lignes.all()
        total_ht_attendu = sum(ligne.montant_ht for ligne in lignes)
        total_ttc_attendu = sum(ligne.montant_ttc for ligne in lignes)

        # Vérifier si correction nécessaire
        erreur_ht = abs(commande.montant_total_ht - total_ht_attendu) > Decimal('0.01')
        erreur_ttc = abs(commande.montant_total_ttc - total_ttc_attendu) > Decimal('0.01')

        if erreur_ht or erreur_ttc:
            print(f"\n🔧 Correction de {commande.reference} (ID: {commande.id})")
            print(f"   Avant: HT={commande.montant_total_ht:.2f}, TTC={commande.montant_total_ttc:.2f}")

            # Corriger
            commande.montant_total_ht = total_ht_attendu
            commande.montant_total_ttc = total_ttc_attendu
            commande.save(update_fields=['montant_total_ht', 'montant_total_ttc'])

            print(f"   Après: HT={commande.montant_total_ht:.2f}, TTC={commande.montant_total_ttc:.2f}")
            commandes_corrigees += 1

    print("\n" + "=" * 80)
    print(f"✅ TERMINÉ: {commandes_corrigees}/{total_commandes} commande(s) corrigée(s)")
    print("=" * 80)

if __name__ == '__main__':
    reponse = input("⚠️  Voulez-vous corriger les totaux incorrects? (oui/non): ")
    if reponse.lower() in ['oui', 'o', 'yes', 'y']:
        corriger_commandes()
    else:
        print("❌ Opération annulée")
