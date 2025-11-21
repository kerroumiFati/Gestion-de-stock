"""
Script pour vérifier tous les entrepôts et vans dans le système
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Warehouse
from API.distribution_models import LivreurDistribution

print("=" * 70)
print("VÉRIFICATION DES ENTREPÔTS ET VANS")
print("=" * 70)

# Récupérer tous les entrepôts
entrepots = Warehouse.objects.all().order_by('code')
print(f"\n📦 Total d'entrepôts dans le système: {entrepots.count()}")

if entrepots.count() == 0:
    print("⚠️  Aucun entrepôt trouvé!")
else:
    print("\nListe des entrepôts:")
    for e in entrepots:
        van_info = ""
        # Vérifier si cet entrepôt est assigné à un livreur (c'est un van)
        livreur = LivreurDistribution.objects.filter(entrepot=e).first()
        if livreur:
            van_info = f" 🚐 [VAN de {livreur.nom}]"

        print(f"  {e.id}. {e.code} - {e.name}{van_info}")

# Vérifier les livreurs et leurs vans
print("\n" + "=" * 70)
print("LIVREURS ET LEURS VANS ASSIGNÉS")
print("=" * 70)

livreurs = LivreurDistribution.objects.all().order_by('nom')
print(f"\n👤 Total de livreurs: {livreurs.count()}")

if livreurs.count() == 0:
    print("⚠️  Aucun livreur trouvé!")
else:
    print("\nListe des livreurs:")
    for l in livreurs:
        if l.entrepot:
            print(f"  ✅ {l.nom} (Matricule: {l.matricule})")
            print(f"     Van assigné: {l.entrepot.code} - {l.entrepot.name}")
        else:
            print(f"  ❌ {l.nom} (Matricule: {l.matricule})")
            print(f"     Aucun van assigné")

# Statistiques
print("\n" + "=" * 70)
print("STATISTIQUES")
print("=" * 70)

vans = LivreurDistribution.objects.exclude(entrepot__isnull=True).count()
livreurs_sans_van = LivreurDistribution.objects.filter(entrepot__isnull=True).count()
entrepots_non_van = entrepots.exclude(livreur_associe__isnull=False).count()

print(f"\n📊 Résumé:")
print(f"  - Total entrepôts: {entrepots.count()}")
print(f"  - Entrepôts classiques (non-vans): {entrepots_non_van}")
print(f"  - Vans (entrepôts mobiles): {vans}")
print(f"  - Livreurs avec van: {vans}")
print(f"  - Livreurs sans van: {livreurs_sans_van}")

print("\n" + "=" * 70)
