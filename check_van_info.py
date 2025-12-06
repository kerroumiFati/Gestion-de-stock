from API.distribution_models import LivreurDistribution
from API.models import Warehouse, ProductStock
from django.db.models import Sum

# Chercher le van VAN-LIVRAISON-A
van = Warehouse.objects.filter(code='VAN-LIVRAISON-A').first()

if van:
    print(f"Van trouvé: {van.name}")
    print(f"ID: {van.id}")
    print(f"Code: {van.code}")
    print("="*60)

    # Chercher le livreur assigné à ce van
    livreur = LivreurDistribution.objects.filter(entrepot=van).first()

    if livreur:
        print(f"\nLivreur assigné:")
        print(f"  Nom: {livreur.nom}")
        print(f"  ID: {livreur.id}")
        print(f"  Matricule: {livreur.matricule}")
    else:
        print("\nAucun livreur assigné à ce van")

    # Vérifier le stock
    stock_count = ProductStock.objects.filter(warehouse=van).count()
    total_qty = ProductStock.objects.filter(warehouse=van).aggregate(total=Sum('quantity'))['total'] or 0

    print(f"\nStock:")
    print(f"  Produits: {stock_count}")
    print(f"  Quantité totale: {total_qty}")
else:
    print("Van VAN-LIVRAISON-A non trouvé")

print("\n" + "="*60)
print("TOUS LES LIVREURS AVEC VANS:")
print("="*60)
livreurs = LivreurDistribution.objects.filter(entrepot__isnull=False).select_related('entrepot')
for l in livreurs:
    print(f"{l.nom} (ID: {l.id}) -> {l.entrepot.name} ({l.entrepot.code})")
