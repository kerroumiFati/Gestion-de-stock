#!/usr/bin/env python
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Produit
from API.serializers import ProduitSerializer

print("=" * 80)
print("TEST API RESPONSE - Vérification du champ company")
print("=" * 80)

# Prendre un produit actif comme exemple
produit = Produit.objects.filter(is_active=True).first()

if produit:
    print(f"\n📦 Produit testé:")
    print(f"   ID: {produit.id}")
    print(f"   Référence: {produit.reference}")
    print(f"   Désignation: {produit.designation}")
    print(f"   Company (model): {produit.company.id if produit.company else 'NULL'}")
    print(f"   Company name: {produit.company.name if produit.company else 'NULL'}")

    # Sérialiser comme l'API le fait
    serializer = ProduitSerializer(produit)
    data = serializer.data

    print(f"\n📡 Données retournées par l'API (serializer):")
    print(json.dumps(dict(data), indent=2, default=str))

    print(f"\n🔍 Champ 'company' dans la réponse API:")
    if 'company' in data:
        print(f"   ✓ Présent: {data['company']}")
    else:
        print(f"   ✗ ABSENT! C'est le problème!")

else:
    print("Aucun produit actif trouvé!")
