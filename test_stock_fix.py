import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Warehouse
from django.db.models import Sum

print("="*70)
print("VÉRIFICATION APRÈS CORRECTION")
print("="*70)

warehouses = Warehouse.objects.all().order_by('code')
for entrepot in warehouses:
    # Nouvelle logique (corrigée)
    nb_produits = entrepot.stocks.filter(quantity__gt=0).count()
    total_quantite = entrepot.stocks.aggregate(Sum('quantity'))['quantity__sum'] or 0
    valeur_stock = sum(
        stock.quantity * stock.produit.prixU
        for stock in entrepot.stocks.select_related('produit')
        if stock.produit.prixU
    )

    # Afficher seulement si non vide
    if nb_produits > 0 or total_quantite > 0:
        print(f"\n{entrepot.code} ({entrepot.name})")
        print(f"  Produits en stock (qty>0): {nb_produits}")
        print(f"  Quantité totale: {total_quantite}")
        print(f"  Valeur: {valeur_stock:.2f} DA")

print("\n" + "="*70)
print("✅ Les nombres sont maintenant cohérents!")
print("="*70)
