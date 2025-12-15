import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import TourneeMobile, RapportCaisseMobile, LivreurDistribution
from decimal import Decimal
from datetime import date

# Recuperer une tournee terminee ou en creer une
tournee = TourneeMobile.objects.filter(statut='terminee').first()

if not tournee:
    livreur = LivreurDistribution.objects.first()
    if livreur:
        tournee = TourneeMobile.objects.create(
            livreur=livreur,
            date_tournee=date.today(),
            numero_tournee=f"TEST-{date.today().strftime('%Y%m%d')}",
            statut='terminee'
        )
        print(f"Tournee creee: {tournee.numero_tournee}")

if tournee:
    # Creer ou recuperer le rapport
    rapport, created = RapportCaisseMobile.objects.get_or_create(
        tournee=tournee,
        defaults={
            'fonds_depart': Decimal('50000.00'),
            'total_especes': Decimal('125000.00'),
            'total_cartes': Decimal('35000.00'),
            'total_cheques': Decimal('20000.00'),
            'total_credits': Decimal('15000.00'),
            'carburant': Decimal('3000.00'),
            'reparations': Decimal('5000.00'),
            'autres_depenses': Decimal('2000.00'),
            'statut': 'valide'
        }
    )

    # Ajouter les details des billets
    rapport.detail_billets = {
        "2000": 50,
        "1000": 15,
        "500": 12,
        "200": 10,
        "100": 15,
        "50": 5,
        "20": 5,
        "10": 10,
        "5": 10
    }

    rapport.calculer_totaux()
    rapport.solde_final_reel = rapport.solde_final_theorique + Decimal('50.00')
    rapport.ecart = rapport.solde_final_reel - rapport.solde_final_theorique
    rapport.justification_ecart = "Client a donne 50 DA de plus par erreur"
    rapport.save()

    print("\n" + "="*60)
    print("RAPPORT DE CAISSE CREE AVEC SUCCES!")
    print("="*60)
    print(f"\nTournee: {tournee.numero_tournee}")
    print(f"Livreur: {tournee.livreur.nom}")
    print(f"\nEncaissements:")
    print(f"   - Especes: {rapport.total_especes} DA")
    print(f"   - Cartes: {rapport.total_cartes} DA")
    print(f"   - Cheques: {rapport.total_cheques} DA")
    print(f"\nSolde final:")
    print(f"   - Theorique: {rapport.solde_final_theorique} DA")
    print(f"   - Reel: {rapport.solde_final_reel} DA")
    print(f"   - Ecart: {rapport.ecart} DA")
    print(f"\nDETAIL DES BILLETS RETOURNES:")
    total = 0
    for denom, qty in sorted(rapport.detail_billets.items(), key=lambda x: int(x[0]), reverse=True):
        if qty > 0:
            subtotal = int(denom) * qty
            total += subtotal
            print(f"   - {qty:2d} x {int(denom):5,d} DA = {subtotal:8,d} DA")
    print(f"   {'='*40}")
    print(f"   TOTAL: {total:,d} DA")
    print("\nAccedez a: http://localhost:8000/page/historique_tournees")
else:
    print("Aucun livreur trouve. Creez d'abord un livreur.")
