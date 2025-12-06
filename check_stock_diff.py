import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import ProductStock, Warehouse, Produit
from django.db.models import Sum, Count

print("="*70)
print("ANALYSE DES STOCKS - Comparaison entre les deux vues")
print("="*70)

# Vue 1: Stocks par entrepôt (entrepots_list)
print("\n📊 VUE 1: STOCKS PAR ENTREPÔT (entrepots_list)")
print("-"*70)
warehouses = Warehouse.objects.all().order_by('code')
for entrepot in warehouses:
    nb_produits = entrepot.stocks.count()
    total_quantite = entrepot.stocks.aggregate(Sum('quantity'))['quantity__sum'] or 0
    valeur_stock = sum(
        stock.quantity * stock.produit.prixU
        for stock in entrepot.stocks.select_related('produit')
        if stock.produit.prixU
    )
    print(f"\n{entrepot.code} ({entrepot.name})")
    print(f"  Nombre de produits: {nb_produits}")
    print(f"  Quantité totale: {total_quantite}")
    print(f"  Valeur stock: {valeur_stock:.2f} DA")

# Vue 2: Liste des stocks (stocks_list)
print("\n\n📊 VUE 2: LISTE DES STOCKS (stocks_list)")
print("-"*70)
print("Total des lignes de stock dans la base:")
total_stocks = ProductStock.objects.count()
stocks_non_vides = ProductStock.objects.filter(quantity__gt=0).count()
stocks_vides = ProductStock.objects.filter(quantity=0).count()
print(f"  Total lignes: {total_stocks}")
print(f"  Lignes avec stock > 0: {stocks_non_vides}")
print(f"  Lignes vides (0): {stocks_vides}")

# Par entrepôt détaillé
print("\nDétail par entrepôt:")
for entrepot in warehouses:
    stocks = ProductStock.objects.filter(warehouse=entrepot)
    stocks_non_vides = stocks.filter(quantity__gt=0)
    print(f"\n{entrepot.code}:")
    print(f"  Total lignes: {stocks.count()}")
    print(f"  Lignes non vides: {stocks_non_vides.count()}")
    print(f"  Lignes vides: {stocks.filter(quantity=0).count()}")

# Vérifier les incohérences potentielles
print("\n\n🔍 VÉRIFICATION DES INCOHÉRENCES")
print("-"*70)

# Produits sans stock
produits_total = Produit.objects.count()
produits_avec_stock = ProductStock.objects.values('produit').distinct().count()
produits_sans_stock = produits_total - produits_avec_stock
print(f"Produits total: {produits_total}")
print(f"Produits avec au moins une ligne de stock: {produits_avec_stock}")
print(f"Produits SANS ligne de stock: {produits_sans_stock}")

# Stocks dupliqués (même produit plusieurs fois dans même entrepôt)
duplicates = ProductStock.objects.values('warehouse', 'produit')\
    .annotate(count=Count('id'))\
    .filter(count__gt=1)
if duplicates:
    print(f"\n⚠️  ATTENTION: {len(duplicates)} doublons détectés!")
    for dup in duplicates[:5]:
        w = Warehouse.objects.get(id=dup['warehouse'])
        p = Produit.objects.get(id=dup['produit'])
        print(f"  - {w.code} / {p.designation}: {dup['count']} lignes")
else:
    print("\n✅ Aucun doublon détecté")

print("\n" + "="*70)
