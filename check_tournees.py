"""
Script de diagnostic pour vérifier les tournées et les livreurs
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution, TourneeMobile, ArretTourneeMobile
from django.contrib.auth.models import User
from datetime import date

print("=" * 80)
print("DIAGNOSTIC DES TOURNÉES ET LIVREURS")
print("=" * 80)

# 1. Vérifier les livreurs
print("\n📦 LIVREURS :")
livreurs = LivreurDistribution.objects.all()
print(f"Total : {livreurs.count()}")

if livreurs.exists():
    for livreur in livreurs:
        print(f"\n  • ID: {livreur.id}")
        print(f"    Nom: {livreur.nom}")
        print(f"    Matricule: {livreur.matricule}")
        print(f"    Statut: {livreur.statut}")

        # Vérifier le compte utilisateur
        if livreur.user:
            print(f"    ✅ Compte utilisateur: {livreur.user.username}")
        else:
            print(f"    ❌ PAS de compte utilisateur lié !")

        # Compter les tournées
        nb_tournees = livreur.tournees.count()
        print(f"    Tournées: {nb_tournees}")
else:
    print("  ❌ AUCUN livreur trouvé !")
    print("\n  💡 Solution : Créer un livreur via Django Admin ou l'API")

# 2. Vérifier les tournées
print("\n\n🚚 TOURNÉES :")
tournees = TourneeMobile.objects.all()
print(f"Total : {tournees.count()}")

if tournees.exists():
    today = date.today()
    tournees_aujourdhui = tournees.filter(date_tournee=today)
    print(f"Aujourd'hui ({today}) : {tournees_aujourdhui.count()}")

    for tournee in tournees.order_by('-date_tournee')[:5]:
        print(f"\n  • ID: {tournee.id}")
        print(f"    Numéro: {tournee.numero_tournee}")
        print(f"    Date: {tournee.date_tournee}")
        print(f"    Livreur: {tournee.livreur.nom if tournee.livreur else 'N/A'}")
        print(f"    Statut: {tournee.statut}")
        print(f"    Arrêts: {tournee.arrets.count()}")
        print(f"    Argent départ: {tournee.argent_depart} DA")
else:
    print("  ❌ AUCUNE tournée trouvée !")
    print("\n  💡 Solution : Créer une tournée de test")

# 3. Vérifier les utilisateurs avec groupe livreurs
print("\n\n👤 UTILISATEURS DU GROUPE 'livreurs' :")
try:
    from django.contrib.auth.models import Group
    livreurs_group = Group.objects.get(name='livreurs')
    users = livreurs_group.user_set.all()
    print(f"Total : {users.count()}")

    for user in users:
        print(f"\n  • Username: {user.username}")
        print(f"    Email: {user.email}")
        print(f"    Active: {user.is_active}")

        # Vérifier si lié à un livreur
        try:
            livreur = LivreurDistribution.objects.get(user=user)
            print(f"    ✅ Lié au livreur: {livreur.nom} (ID: {livreur.id})")
        except LivreurDistribution.DoesNotExist:
            print(f"    ❌ PAS lié à un livreur !")
except Group.DoesNotExist:
    print("  ❌ Groupe 'livreurs' n'existe pas !")

# 4. Résumé et recommandations
print("\n\n" + "=" * 80)
print("RÉSUMÉ ET RECOMMANDATIONS")
print("=" * 80)

if livreurs.count() == 0:
    print("\n❌ PROBLÈME : Aucun livreur dans la base")
    print("   → Créer un livreur via : POST /API/distribution/livreurs/")
elif tournees.count() == 0:
    print("\n❌ PROBLÈME : Aucune tournée dans la base")
    print("   → Créer une tournée via : POST /API/distribution/tournees/")
else:
    # Vérifier les livreurs sans user
    livreurs_sans_user = livreurs.filter(user__isnull=True)
    if livreurs_sans_user.exists():
        print(f"\n⚠️  ATTENTION : {livreurs_sans_user.count()} livreur(s) sans compte utilisateur")
        print("   → Créer un compte via : POST /API/distribution/livreurs/{id}/creer_compte/")
    else:
        print("\n✅ Tous les livreurs ont un compte utilisateur")

    # Vérifier tournées d'aujourd'hui
    today = date.today()
    tournees_aujourdhui = tournees.filter(date_tournee=today)
    if tournees_aujourdhui.count() == 0:
        print(f"\n⚠️  ATTENTION : Aucune tournée pour aujourd'hui ({today})")
        print("   → L'app mobile ne trouvera pas de tournées")
    else:
        print(f"\n✅ {tournees_aujourdhui.count()} tournée(s) pour aujourd'hui")

print("\n")
