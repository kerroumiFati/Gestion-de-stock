"""
Script pour vérifier les totaux des commandes clients mobiles
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import CommandeClient, LigneCommandeClient
from decimal import Decimal

def verifier_commandes():
    print("=" * 80)
    print("VÉRIFICATION DES TOTAUX DES COMMANDES")
    print("=" * 80)
    print()

    # Récupérer toutes les commandes
    commandes = CommandeClient.objects.all().order_by('-id')[:10]  # Les 10 dernières

    if not commandes:
        print("❌ Aucune commande trouvée dans la base de données")
        return

    print(f"✅ {commandes.count()} commande(s) trouvée(s)\n")

    for commande in commandes:
        print(f"\n{'='*80}")
        print(f"COMMANDE: {commande.reference} (ID: {commande.id})")
        print(f"Client: {commande.client.nom}")
        print(f"Statut: {commande.statut}")
        print(f"Date: {commande.date_commande}")
        print(f"-" * 80)

        # Récupérer les lignes
        lignes = commande.lignes.all()
        print(f"\nNombre de lignes: {lignes.count()}")
        print()

        # Calculer les totaux manuellement
        total_ht_calcule = Decimal('0')
        total_ttc_calcule = Decimal('0')

        print(f"{'Produit':<30} {'Qté':>8} {'Prix HT':>12} {'TVA %':>8} {'Mont. HT':>12} {'Mont. TTC':>12}")
        print("-" * 90)

        for ligne in lignes:
            # Vérifier si les montants de la ligne sont corrects
            montant_ht_attendu = ligne.quantite * ligne.prix_unitaire_ht
            montant_tva_attendu = montant_ht_attendu * (ligne.taux_tva / Decimal('100'))
            montant_ttc_attendu = montant_ht_attendu + montant_tva_attendu

            # Afficher la ligne
            produit_nom = ligne.produit.designation[:28]
            print(f"{produit_nom:<30} {ligne.quantite:>8.2f} {ligne.prix_unitaire_ht:>12.2f} {ligne.taux_tva:>8.2f} {ligne.montant_ht:>12.2f} {ligne.montant_ttc:>12.2f}")

            # Vérifier si les montants stockés sont corrects
            if abs(ligne.montant_ht - montant_ht_attendu) > Decimal('0.01'):
                print(f"    ⚠️  ERREUR: Montant HT incorrect! Attendu: {montant_ht_attendu:.2f}, Stocké: {ligne.montant_ht:.2f}")

            if abs(ligne.montant_ttc - montant_ttc_attendu) > Decimal('0.01'):
                print(f"    ⚠️  ERREUR: Montant TTC incorrect! Attendu: {montant_ttc_attendu:.2f}, Stocké: {ligne.montant_ttc:.2f}")

            # Additionner pour le total
            total_ht_calcule += ligne.montant_ht
            total_ttc_calcule += ligne.montant_ttc

        print("-" * 90)
        print(f"{'TOTAL CALCULÉ:':<30} {' ':>8} {' ':>12} {' ':>8} {total_ht_calcule:>12.2f} {total_ttc_calcule:>12.2f}")
        print(f"{'TOTAL STOCKÉ:':<30} {' ':>8} {' ':>12} {' ':>8} {commande.montant_total_ht:>12.2f} {commande.montant_total_ttc:>12.2f}")

        # Vérifier si les totaux de la commande sont corrects
        if abs(commande.montant_total_ht - total_ht_calcule) > Decimal('0.01'):
            print(f"\n❌ ERREUR: Total HT de la commande incorrect!")
            print(f"   Attendu: {total_ht_calcule:.2f} DZD")
            print(f"   Stocké:  {commande.montant_total_ht:.2f} DZD")
            print(f"   Différence: {abs(commande.montant_total_ht - total_ht_calcule):.2f} DZD")
        else:
            print(f"\n✅ Total HT correct")

        if abs(commande.montant_total_ttc - total_ttc_calcule) > Decimal('0.01'):
            print(f"❌ ERREUR: Total TTC de la commande incorrect!")
            print(f"   Attendu: {total_ttc_calcule:.2f} DZD")
            print(f"   Stocké:  {commande.montant_total_ttc:.2f} DZD")
            print(f"   Différence: {abs(commande.montant_total_ttc - total_ttc_calcule):.2f} DZD")
        else:
            print(f"✅ Total TTC correct")

    print("\n" + "=" * 80)
    print("FIN DE LA VÉRIFICATION")
    print("=" * 80)

if __name__ == '__main__':
    verifier_commandes()
