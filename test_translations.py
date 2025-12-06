#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify translations are working
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.utils.translation import gettext, activate, get_language

print("=" * 60)
print("TEST DES TRADUCTIONS DJANGO")
print("=" * 60)

# Test words
test_words = [
    'Commercial',
    'Produits',
    'Clients',
    'Ventes',
    'Achats',
    'Déconnexion',
    'Paramètres',
]

# Test each language
for lang_code, lang_name in [('fr', 'Français'), ('en', 'English'), ('ar', 'العربية')]:
    print(f"\n{'=' * 60}")
    print(f"Langue: {lang_name} ({lang_code})")
    print('=' * 60)

    activate(lang_code)
    current = get_language()
    print(f"Langue activée: {current}")

    for word in test_words:
        translated = gettext(word)
        status = "✓" if translated != word or lang_code == 'fr' else "✗"
        print(f"{status} {word:20s} -> {translated}")

print("\n" + "=" * 60)
print("Vérification des fichiers .mo")
print("=" * 60)

base_dir = os.path.dirname(os.path.abspath(__file__))
for lang in ['ar', 'en']:
    mo_file = os.path.join(base_dir, 'locale', lang, 'LC_MESSAGES', 'django.mo')
    exists = os.path.exists(mo_file)
    if exists:
        size = os.path.getsize(mo_file)
        print(f"✓ {lang}/django.mo exists ({size} bytes)")
    else:
        print(f"✗ {lang}/django.mo MISSING")

print("\n" + "=" * 60)
print("Vérification de SystemConfig")
print("=" * 60)

try:
    from API.models import SystemConfig
    config = SystemConfig.get_solo()
    print(f"✓ SystemConfig existe")
    print(f"  Langue configurée: {config.language if config.language else 'None'}")
except Exception as e:
    print(f"✗ Erreur: {e}")

print("\n" + "=" * 60)
print("FIN DU TEST")
print("=" * 60)
