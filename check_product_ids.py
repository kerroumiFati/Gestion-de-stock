#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Produit

print("Active products with their IDs:")
print("=" * 60)
for p in Produit.objects.filter(is_active=True).order_by('id'):
    company_str = f"{p.company.name}" if p.company else "NO COMPANY"
    print(f"ID: {p.id:3d} | Ref: {p.reference:15s} | {p.designation:30s} | {company_str}")

print("\nInactive products:")
print("=" * 60)
for p in Produit.objects.filter(is_active=False).order_by('id'):
    company_str = f"{p.company.name}" if p.company else "NO COMPANY"
    print(f"ID: {p.id:3d} | Ref: {p.reference:15s} | {p.designation:30s} | {company_str}")
