"""
Script pour affecter tous les produits sans entrepôt à l'entrepôt DEPOT-MAIN
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from API.models import Produit, Warehouse, ProductStock

def main():
    # Trouver l'entrepôt DEPOT-MAIN
    try:
        depot_main = Warehouse.objects.get(code='DEPOT-MAIN')
        print(f"Entrepôt trouvé: {depot_main.name} (code: {depot_main.code})")
    except Warehouse.DoesNotExist:
        print("ERREUR: L'entrepôt avec le code 'DEPOT-MAIN' n'existe pas!")
        print("\nEntrepôts disponibles:")
        for w in Warehouse.objects.all():
            print(f"  - {w.code}: {w.name}")
        return

    # Trouver tous les produits
    tous_produits = Produit.objects.all()
    print(f"\nNombre total de produits: {tous_produits.count()}")

    # Trouver les produits qui ont déjà un stock dans un entrepôt
    produits_avec_stock = ProductStock.objects.values_list('produit_id', flat=True).distinct()
    print(f"Produits avec au moins un entrepôt: {len(set(produits_avec_stock))}")

    # Trouver les produits sans aucun entrepôt
    produits_sans_entrepot = tous_produits.exclude(id__in=produits_avec_stock)
    print(f"Produits sans entrepôt: {produits_sans_entrepot.count()}")

    if produits_sans_entrepot.count() == 0:
        print("\nTous les produits ont déjà un entrepôt assigné!")
        return

    # Créer les entrées ProductStock pour chaque produit sans entrepôt
    created_count = 0
    for produit in produits_sans_entrepot:
        ProductStock.objects.create(
            produit=produit,
            warehouse=depot_main,
            quantity=0  # Stock initial à 0
        )
        created_count += 1
        print(f"  Assigne: {produit.reference} - {produit.designation}")

    print(f"\n{created_count} produit(s) affecté(s) à l'entrepôt {depot_main.code}")

if __name__ == '__main__':
    main()
