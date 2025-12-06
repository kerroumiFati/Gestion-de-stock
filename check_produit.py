import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Produit, Promotion

# Vérifier le produit fanta
produit = Produit.objects.get(reference='02')
print(f"Produit: {produit.designation}")
print(f"Reference: {produit.reference}")
print(f"Prix unitaire (prixU): {produit.prixU}")
print(f"Prix achat: {produit.prixAchat}")

# Vérifier la promotion
promo = Promotion.objects.get(code='PROMO01')
print(f"\nPromotion: {promo.code}")
print(f"Type: {promo.type_promotion}")
print(f"Quantite achat: {promo.quantite_achat}")
print(f"Quantite offerte (a payer): {promo.quantite_offerte}")

# Calculer pour 3 unités
prix_original = produit.prixU
quantite = 3
offre = promo.calculer_offre_speciale(quantite)
print(f"\nCalcul pour {quantite} unites:")
print(f"  Prix unitaire: {prix_original}")
print(f"  Offre: {offre}")
print(f"  Prix total sans promo: {prix_original * quantite}")
print(f"  Prix total avec promo: {prix_original * offre['quantite_a_payer']}")
print(f"  Economie: {prix_original * quantite - prix_original * offre['quantite_a_payer']}")
