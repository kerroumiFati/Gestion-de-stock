import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Promotion

promo = Promotion.objects.get(code='PROMO01')
promo.type_promotion = 'achetez_x_payez_y'
promo.quantite_achat = 3
promo.quantite_offerte = 2
promo.save()

print(f"Promo mise a jour:")
print(f"  Type: {promo.type_promotion}")
print(f"  Quantite achat: {promo.quantite_achat}")
print(f"  Quantite offerte: {promo.quantite_offerte}")
print(f"  Offre pour 3 unites: {promo.calculer_offre_speciale(3)}")
