import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import TourneeMobile

print("\n" + "="*70)
print("VÉRIFICATION DES DATES DES TOURNÉES")
print("="*70)

# Récupérer toutes les tournées
tournees = TourneeMobile.objects.all().order_by('date_tournee')

print(f"\nNombre total de tournées: {tournees.count()}")

if tournees.count() > 0:
    print("\nListe des tournées avec leurs dates:")
    print("-" * 70)

    for tournee in tournees:
        # Calculer le jour de la semaine
        date_obj = tournee.date_tournee
        jour_semaine = date_obj.strftime('%A')  # Nom du jour en anglais
        jour_semaine_fr = {
            'Monday': 'Lundi',
            'Tuesday': 'Mardi',
            'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi',
            'Friday': 'Vendredi',
            'Saturday': 'Samedi',
            'Sunday': 'Dimanche'
        }.get(jour_semaine, jour_semaine)

        # Calculer le numéro de semaine ISO
        year, week, _ = date_obj.isocalendar()

        print(f"\n📦 {tournee.numero_tournee}")
        print(f"   Date: {tournee.date_tournee} ({jour_semaine_fr})")
        print(f"   Semaine ISO: {year}-W{week:02d}")
        print(f"   Livreur: {tournee.livreur.nom if tournee.livreur else 'N/A'}")
        print(f"   Statut: {tournee.statut}")

    # Afficher les semaines qui ont des tournées
    print("\n" + "="*70)
    print("RÉSUMÉ PAR SEMAINE")
    print("="*70)

    semaines = {}
    for tournee in tournees:
        year, week, _ = tournee.date_tournee.isocalendar()
        semaine_key = f"{year}-W{week:02d}"
        if semaine_key not in semaines:
            semaines[semaine_key] = []
        semaines[semaine_key].append(tournee)

    for semaine_key in sorted(semaines.keys()):
        tournees_semaine = semaines[semaine_key]
        print(f"\n📅 Semaine {semaine_key}: {len(tournees_semaine)} tournée(s)")
        for t in tournees_semaine:
            print(f"   - {t.date_tournee} | {t.livreur.nom if t.livreur else 'N/A'} | {t.statut}")

    # Afficher la semaine actuelle
    print("\n" + "="*70)
    print("SEMAINE ACTUELLE")
    print("="*70)

    today = datetime.now().date()
    current_year, current_week, _ = today.isocalendar()
    print(f"\nAujourd'hui: {today} ({today.strftime('%A')})")
    print(f"Semaine ISO actuelle: {current_year}-W{current_week:02d}")

    # Tournées de cette semaine
    tournees_cette_semaine = [t for t in tournees if t.date_tournee.isocalendar()[:2] == (current_year, current_week)]
    print(f"\nTournées de cette semaine: {len(tournees_cette_semaine)}")
    for t in tournees_cette_semaine:
        print(f"   - {t.date_tournee} | {t.livreur.nom if t.livreur else 'N/A'} | {t.statut}")

print("\n" + "="*70)
