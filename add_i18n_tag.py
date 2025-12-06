#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Add {% load i18n %} to all templates that don't have it
"""
from pathlib import Path

def add_i18n_tag(file_path):
    """Add {% load i18n %} to a template if not present"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if '{% load i18n %}' in content:
        return False  # Already has it

    # Add after {% load static %} if present
    if '{% load static %}' in content:
        content = content.replace('{% load static %}', '{% load static %}\n{% load i18n %}')
    else:
        # Add at the very beginning
        content = '{% load i18n %}\n' + content

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def main():
    base_dir = Path(__file__).parent
    templates_dir = base_dir / 'templates' / 'frontoffice' / 'page'

    templates = [
        'vente.html',
        'achat.html',
        'produit.html',
        'client.html',
        'fournisseur.html',
        'categorie.html',
        'statistiques.html',
        'parametres.html',
        'entrepots.html',
        'facture.html',
        'inventaire.html',
        'mouvements.html',
        'rapports.html',
    ]

    print("Adding {% load i18n %} to templates...")
    updated = 0

    for template_name in templates:
        file_path = templates_dir / template_name
        if file_path.exists():
            if add_i18n_tag(file_path):
                print(f"  [OK] {template_name}")
                updated += 1
            else:
                print(f"  [SKIP] {template_name} (already has i18n)")
        else:
            print(f"  [NOT FOUND] {template_name}")

    print(f"\nDone! Updated {updated} templates")


if __name__ == '__main__':
    main()
