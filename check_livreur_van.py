import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GestionStock.settings')
django.setup()

from API.distribution_models import LivreurDistribution
from API.models import Warehouse, ProductStock

# Chercher le van VAN-LIVRAISON-A
van = Warehouse.objects.filter(code='VAN-LIVRAISON-A').first()

if van:
    print(f"Van trouvé: {van.name} (ID: {van.id}, Code: {van.code})")
    print("="*60)

    # Chercher le livreur assigné à ce van
    livreur = LivreurDistribution.objects.filter(entrepot=van).first()

    if livreur:
        print(f"\nLivreur assigné:")
        print(f"  - Nom: {livreur.nom}")
        print(f"  - ID: {livreur.id}")
        print(f"  - Matricule: {livreur.matricule}")
        print(f"  - Téléphone: {livreur.telephone}")
        print(f"  - Email: {livreur.email}")
    else:
        print("\nAucun livreur assigné à ce van")

    # Vérifier le stock dans ce van
    stock_count = ProductStock.objects.filter(warehouse=van).count()
    total_quantity = ProductStock.objects.filter(warehouse=van).aggregate(
        total=django.db.models.Sum('quantity')
    )['total'] or 0

    print(f"\nStock dans ce van:")
    print(f"  - Nombre de produits: {stock_count}")
    print(f"  - Quantité totale: {total_quantity}")

    # Afficher le détail des produits
    stocks = ProductStock.objects.filter(warehouse=van).select_related('produit')
    if stocks:
        print(f"\nDétail des produits:")
        print("-"*60)
        for s in stocks:
            print(f"  - {s.produit.designation}: {s.quantity} {s.produit.get_unite_mesure_display()}")
else:
    print("Van VAN-LIVRAISON-A non trouvé")

# Afficher tous les livreurs avec leurs vans
print("\n" + "="*60)
print("TOUS LES LIVREURS AVEC VANS ASSIGNÉS:")
print("="*60)
livreurs = LivreurDistribution.objects.filter(entrepot__isnull=False).select_related('entrepot')
for l in livreurs:
    print(f"\nLivreur: {l.nom} (ID: {l.id})")
    print(f"  Van: {l.entrepot.name} ({l.entrepot.code})")
