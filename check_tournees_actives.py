import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import TourneeMobile, LivreurDistribution

print("\n" + "="*70)
print("VÉRIFICATION DES TOURNÉES ACTIVES")
print("="*70)

# Compter les tournées par statut
tournees_planifiees = TourneeMobile.objects.filter(statut='planifiee').count()
tournees_en_cours = TourneeMobile.objects.filter(statut='en_cours').count()
tournees_terminees = TourneeMobile.objects.filter(statut='terminee').count()
tournees_annulees = TourneeMobile.objects.filter(statut='annulee').count()

print(f"\nStatistiques des tournées:")
print(f"  - Planifiées: {tournees_planifiees}")
print(f"  - En cours: {tournees_en_cours}")
print(f"  - Terminées: {tournees_terminees}")
print(f"  - Annulées: {tournees_annulees}")

# Afficher les tournées actives (planifiées + en cours)
print("\n" + "="*70)
print("TOURNÉES ACTIVES (Planifiées + En cours)")
print("="*70)

tournees_actives = TourneeMobile.objects.filter(statut__in=['planifiee', 'en_cours']).select_related('livreur')

if tournees_actives.count() == 0:
    print("\n⚠️  Aucune tournée active trouvée!")
    print("   C'est pourquoi tous les livreurs apparaissent comme 'Disponibles'")
else:
    for tournee in tournees_actives:
        print(f"\n📦 Tournée: {tournee.numero_tournee}")
        print(f"   Livreur: {tournee.livreur.nom}")
        print(f"   Date: {tournee.date_tournee}")
        print(f"   Statut: {tournee.statut}")
        if tournee.heure_debut:
            print(f"   Heure début: {tournee.heure_debut}")

# Afficher les livreurs et leur statut de disponibilité
print("\n" + "="*70)
print("STATUT DES LIVREURS")
print("="*70)

livreurs = LivreurDistribution.objects.all()

for livreur in livreurs:
    tournees_actives_count = livreur.tournees_actives().count()
    is_disponible = livreur.statut == 'actif' and tournees_actives_count == 0

    print(f"\n👤 {livreur.nom}")
    print(f"   Statut: {livreur.statut}")
    print(f"   Tournées actives: {tournees_actives_count}")

    if livreur.statut != 'actif':
        print(f"   📊 Statut: INACTIF")
    elif is_disponible:
        print(f"   ✅ Statut: DISPONIBLE")
    else:
        print(f"   🚚 Statut: EN TOURNÉE")

print("\n" + "="*70)
