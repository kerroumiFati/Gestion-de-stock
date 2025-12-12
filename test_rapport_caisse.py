"""
Script pour ajouter un rapport de caisse avec détail des billets à une tournée
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import TourneeMobile, RapportCaisseMobile
from decimal import Decimal

# Récupérer une tournée terminée
tournee = TourneeMobile.objects.filter(statut='terminee').first()

if not tournee:
    print("❌ Aucune tournée terminée trouvée!")
    print("Création d'une tournée terminée pour le test...")

    # Créer une tournée terminée si aucune n'existe
    from API.distribution_models import LivreurDistribution
    from datetime import date

    livreur = LivreurDistribution.objects.first()
    if not livreur:
        print("❌ Aucun livreur trouvé!")
        exit(1)

    tournee = TourneeMobile.objects.create(
        livreur=livreur,
        date_tournee=date.today(),
        numero_tournee=f"TEST-{date.today().strftime('%Y%m%d')}",
        statut='terminee'
    )
    print(f"✅ Tournée créée: {tournee.numero_tournee}")

# Vérifier si un rapport existe déjà
if hasattr(tournee, 'rapport_caisse') and tournee.rapport_caisse:
    print(f"⚠️  Un rapport existe déjà pour la tournée {tournee.numero_tournee}")
    rapport = tournee.rapport_caisse
else:
    # Créer un nouveau rapport
    rapport = RapportCaisseMobile.objects.create(tournee=tournee)
    print(f"✅ Rapport de caisse créé pour la tournée {tournee.numero_tournee}")

# Remplir les données du rapport
rapport.fonds_depart = Decimal('50000.00')  # 50 000 DA de départ
rapport.total_especes = Decimal('125000.00')  # 125 000 DA encaissés en espèces
rapport.total_cartes = Decimal('35000.00')  # 35 000 DA en cartes
rapport.total_cheques = Decimal('20000.00')  # 20 000 DA en chèques
rapport.total_credits = Decimal('15000.00')  # 15 000 DA à crédit

# Dépenses
rapport.carburant = Decimal('3000.00')  # 3 000 DA de carburant
rapport.reparations = Decimal('5000.00')  # 5 000 DA de réparations
rapport.autres_depenses = Decimal('2000.00')  # 2 000 DA autres

# Détail des billets retournés (espèces)
detail_billets = {
    "2000": 50,  # 50 billets de 2000 DA = 100 000 DA
    "1000": 15,  # 15 billets de 1000 DA = 15 000 DA
    "500": 12,   # 12 billets de 500 DA = 6 000 DA
    "200": 10,   # 10 billets de 200 DA = 2 000 DA
    "100": 15,   # 15 billets de 100 DA = 1 500 DA
    "50": 5,     # 5 pièces de 50 DA = 250 DA
    "20": 5,     # 5 pièces de 20 DA = 100 DA
    "10": 10,    # 10 pièces de 10 DA = 100 DA
    "5": 10      # 10 pièces de 5 DA = 50 DA
}
# Total = 125 000 DA (correspond au total_especes)

rapport.detail_billets = detail_billets
rapport.statut = 'valide'

# Calculer les totaux
rapport.calculer_totaux()

# Ajouter un petit écart pour le test (50 DA en trop)
rapport.solde_final_reel = rapport.solde_final_theorique + Decimal('50.00')
rapport.ecart = rapport.solde_final_reel - rapport.solde_final_theorique
rapport.justification_ecart = "Client a donné 50 DA de plus par erreur"

rapport.save()

print("\n" + "="*60)
print("✅ RAPPORT DE CAISSE CRÉÉ AVEC SUCCÈS!")
print("="*60)
print(f"\n📊 Tournée: {tournee.numero_tournee}")
print(f"📅 Date: {tournee.date_tournee}")
print(f"👤 Livreur: {tournee.livreur.nom}")
print(f"\n💰 Fonds de départ: {rapport.fonds_depart:,.2f} DA")
print(f"\n💵 ENCAISSEMENTS:")
print(f"   - Espèces: {rapport.total_especes:,.2f} DA")
print(f"   - Cartes: {rapport.total_cartes:,.2f} DA")
print(f"   - Chèques: {rapport.total_cheques:,.2f} DA")
print(f"   - À crédit: {rapport.total_credits:,.2f} DA")
print(f"   - TOTAL: {rapport.total_encaissements:,.2f} DA")
print(f"\n🔧 DÉPENSES:")
print(f"   - Carburant: {rapport.carburant:,.2f} DA")
print(f"   - Réparations: {rapport.reparations:,.2f} DA")
print(f"   - Autres: {rapport.autres_depenses:,.2f} DA")
print(f"   - TOTAL: {rapport.total_depenses:,.2f} DA")
print(f"\n💼 SOLDE FINAL:")
print(f"   - Théorique: {rapport.solde_final_theorique:,.2f} DA")
print(f"   - Réel: {rapport.solde_final_reel:,.2f} DA")
print(f"   - Écart: {rapport.ecart:,.2f} DA")
print(f"\n💸 DÉTAIL DES BILLETS RETOURNÉS:")
total_billets = 0
for denom, qty in sorted(detail_billets.items(), key=lambda x: int(x[0]), reverse=True):
    if qty > 0:
        total = int(denom) * qty
        total_billets += total
        print(f"   - {qty:2d} × {int(denom):5,d} DA = {total:8,d} DA")
print(f"   {'='*40}")
print(f"   TOTAL: {total_billets:,d} DA")
print("\n" + "="*60)
print("🌐 Testez maintenant sur: http://localhost:8000/page/historique_tournees")
print("="*60)
