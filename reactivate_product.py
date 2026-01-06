#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Produit

# Reactivate product ID 16
p = Produit.objects.get(id=16)
print(f"Product: [{p.id}] {p.reference} - {p.designation}")
print(f"Current status: {'Active' if p.is_active else 'Inactive'}")

p.is_active = True
p.save()

print(f"New status: {'Active' if p.is_active else 'Inactive'}")
print("\nProduct reactivated successfully!")
