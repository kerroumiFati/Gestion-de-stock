"""
Script pour initialiser les stocks dans ProductStock à partir de Produit.quantite
À exécuter avec: python manage.py shell < init_product_stocks.py
Ou copier/coller le contenu dans python manage.py shell
"""
import os
import django

# Configuration Django (si exécuté directement)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
try:
    django.setup()
except:
    pass

from API.models import Produit, ProductStock, Warehouse, Company

print("=" * 60)
print("INITIALISATION DES STOCKS DANS PRODUCTSTOCK")
print("=" * 60)

# Lister les entrepôts
print("\n=== ENTREPOTS DISPONIBLES ===")
warehouses = Warehouse.objects.all()
for w in warehouses:
    print(f"  {w.id}: {w.code} - {w.name} (company: {w.company}, active: {w.is_active})")

if not warehouses.exists():
    print("\n⚠️  AUCUN ENTREPOT TROUVE! Créez d'abord des entrepôts.")
    exit()

# Trouver l'entrepôt principal (non-van)
entrepot_principal = Warehouse.objects.exclude(code__icontains='van').filter(is_active=True).first()

if not entrepot_principal:
    print("\n⚠️  AUCUN ENTREPOT PRINCIPAL TROUVE (non-van)!")
    print("Création d'un entrepôt principal par défaut...")

    # Trouver une company
    company = Company.objects.first()
    if not company:
        print("⚠️  Aucune company trouvée. Impossible de créer un entrepôt.")
        exit()

    entrepot_principal = Warehouse.objects.create(
        code='WH-MAIN',
        name='Entrepôt Principal',
        address='Adresse principale',
        company=company,
        is_active=True
    )
    print(f"✅ Entrepôt principal créé: {entrepot_principal.code}")

print(f"\n📦 Entrepôt principal sélectionné: {entrepot_principal.code} - {entrepot_principal.name}")

# Lister les produits
print("\n=== PRODUITS À INITIALISER ===")
produits = Produit.objects.filter(is_active=True)
print(f"Nombre de produits actifs: {produits.count()}")

# Vérifier les stocks actuels dans ProductStock
print("\n=== STOCKS ACTUELS DANS PRODUCTSTOCK ===")
stocks_count = ProductStock.objects.count()
print(f"Nombre total de ProductStock: {stocks_count}")

if stocks_count > 0:
    print("\nTop 10 stocks existants:")
    for ps in ProductStock.objects.all()[:10]:
        print(f"  {ps.warehouse.code} - {ps.produit.reference}: {ps.quantity}")

# Initialiser les stocks
print("\n=== INITIALISATION DES STOCKS ===")
created = 0
updated = 0

for produit in produits:
    stock, is_new = ProductStock.objects.get_or_create(
        produit=produit,
        warehouse=entrepot_principal,
        defaults={'quantity': produit.quantite}
    )

    if is_new:
        created += 1
        print(f"  ✅ Créé: {produit.reference} -> {produit.quantite} unités dans {entrepot_principal.code}")
    elif stock.quantity == 0 and produit.quantite > 0:
        # Mettre à jour si le stock est à 0 mais le produit a une quantité
        stock.quantity = produit.quantite
        stock.save()
        updated += 1
        print(f"  🔄 Mis à jour: {produit.reference} -> {produit.quantite} unités")

print(f"\n=== RÉSUMÉ ===")
print(f"Stocks créés: {created}")
print(f"Stocks mis à jour: {updated}")
print(f"Total ProductStock maintenant: {ProductStock.objects.count()}")

# Afficher le stock total par entrepôt
print("\n=== STOCK TOTAL PAR ENTREPOT ===")
from django.db.models import Sum
for w in Warehouse.objects.filter(is_active=True):
    total = ProductStock.objects.filter(warehouse=w).aggregate(Sum('quantity'))['quantity__sum'] or 0
    count = ProductStock.objects.filter(warehouse=w, quantity__gt=0).count()
    print(f"  {w.code}: {count} produits, {total} unités totales")

print("\n✅ Initialisation terminée!")
