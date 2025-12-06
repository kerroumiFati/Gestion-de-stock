"""
Script de diagnostic pour vérifier les stocks par van
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution
from API.models import Warehouse, ProductStock, Produit

print("=" * 80)
print("DIAGNOSTIC DES STOCKS PAR VAN")
print("=" * 80)

# 1. Vérifier les livreurs et leurs vans
print("\n📦 LIVREURS ET LEURS VANS :")
livreurs = LivreurDistribution.objects.all()

for livreur in livreurs:
    print(f"\n  • {livreur.nom} (ID: {livreur.id})")
    print(f"    Matricule: {livreur.matricule}")
    print(f"    Statut: {livreur.statut}")

    if livreur.entrepot:
        warehouse = livreur.entrepot
        print(f"    ✅ Van assigné: {warehouse.name} (Code: {warehouse.code})")

        # Compter les stocks
        stocks = ProductStock.objects.filter(warehouse=warehouse)
        total_products = stocks.count()
        total_quantity = sum(s.quantity for s in stocks)
        stocks_non_vides = stocks.filter(quantity__gt=0)

        print(f"       - Total références: {total_products}")
        print(f"       - Références en stock: {stocks_non_vides.count()}")
        print(f"       - Quantité totale: {total_quantity}")

        if stocks_non_vides.exists():
            print(f"\n       Détail des 5 premiers produits :")
            for stock in stocks_non_vides[:5]:
                print(f"         - {stock.produit.designation}: {stock.quantity} {stock.produit.get_unite_mesure_display()}")
    else:
        print(f"    ❌ PAS de van assigné !")

# 2. Vérifier tous les entrepôts de type "van"
print("\n\n🚐 ENTREPÔTS (VANS) :")
warehouses = Warehouse.objects.all()
print(f"Total : {warehouses.count()}")

for warehouse in warehouses:
    print(f"\n  • {warehouse.name} (ID: {warehouse.id})")
    print(f"    Code: {warehouse.code}")
    print(f"    Actif: {warehouse.is_active}")

    # Trouver le livreur assigné
    livreur_assigne = LivreurDistribution.objects.filter(entrepot=warehouse).first()
    if livreur_assigne:
        print(f"    ✅ Assigné à: {livreur_assigne.nom}")
    else:
        print(f"    ⚠️  Non assigné à un livreur")

    # Stock
    stocks = ProductStock.objects.filter(warehouse=warehouse)
    stocks_non_vides = stocks.filter(quantity__gt=0)
    print(f"    Stock: {stocks_non_vides.count()} produits ({stocks.count()} références)")

# 3. Vérifier les produits disponibles
print("\n\n📦 PRODUITS DISPONIBLES :")
produits = Produit.objects.all()
print(f"Total : {produits.count()}")

if produits.count() == 0:
    print("  ❌ AUCUN produit dans la base !")
    print("  💡 Créez des produits via Django Admin ou l'API")
else:
    print(f"\n  Exemples de produits :")
    for produit in produits[:5]:
        print(f"    - {produit.reference}: {produit.designation}")
        print(f"      Prix: {produit.prixU} (Unité: {produit.get_unite_mesure_display()})")

# 4. Résumé et recommandations
print("\n\n" + "=" * 80)
print("RÉSUMÉ ET RECOMMANDATIONS")
print("=" * 80)

livreurs_sans_van = livreurs.filter(entrepot__isnull=True)
if livreurs_sans_van.exists():
    print(f"\n⚠️  {livreurs_sans_van.count()} livreur(s) sans van assigné :")
    for liv in livreurs_sans_van:
        print(f"   - {liv.nom} ({liv.matricule})")
    print("\n   💡 Solution : Assigner un entrepôt (van) via Django Admin")

vans_sans_stock = []
for warehouse in warehouses:
    stocks = ProductStock.objects.filter(warehouse=warehouse, quantity__gt=0)
    if stocks.count() == 0:
        vans_sans_stock.append(warehouse)

if vans_sans_stock:
    print(f"\n⚠️  {len(vans_sans_stock)} van(s) sans stock :")
    for van in vans_sans_stock:
        print(f"   - {van.name} ({van.code})")
    print("\n   💡 Solution : Ajouter du stock via Django Admin ou transférer depuis entrepôt principal")

# Vérifier l'endpoint API
print("\n\n📡 TEST DE L'ENDPOINT API :")
for livreur in livreurs.filter(entrepot__isnull=False)[:1]:
    print(f"\n  URL à tester : GET /API/distribution/livreurs/{livreur.id}/stock_van/")
    print(f"  Livreur : {livreur.nom}")
    print(f"  Van : {livreur.entrepot.name}")

print("\n")
