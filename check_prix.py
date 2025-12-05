import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Produit, PrixProduit

# Vérifier le produit fanta
produit = Produit.objects.get(reference='02')
print(f"Produit: {produit.designation} (ID: {produit.id})")
print(f"Prix unitaire (prixU): {produit.prixU}")

# Vérifier tous les prix associés
print(f"\nPrix par type:")
try:
    prix_list = PrixProduit.objects.filter(produit=produit)
    for p in prix_list:
        print(f"  - {p.type_prix.libelle if p.type_prix else 'N/A'}: {p.prix} DA")
except Exception as e:
    print(f"Erreur: {e}")

# Mettre à jour le prix à 120
print(f"\nMise à jour du prix à 120.00 DA...")
produit.prixU = 120
produit.save()
print(f"Nouveau prixU: {produit.prixU}")
