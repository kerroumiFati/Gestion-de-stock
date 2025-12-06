#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick and dirty translation - replace common French texts with {% trans %}
"""
import re
from pathlib import Path

# List of exact texts to replace (most common ones)
EXACT_REPLACEMENTS = {
    # Buttons
    '>Ajouter<': '>{%trans"Ajouter"%}<',
    '>Modifier<': '>{%trans"Modifier"%}<',
    '>Supprimer<': '>{%trans"Supprimer"%}<',
    '>Fermer<': '>{%trans"Fermer"%}<',
    '>Enregistrer<': '>{%trans"Enregistrer"%}<',
    '>Rechercher<': '>{%trans"Rechercher"%}<',
    '>Filtrer<': '>{%trans"Filtrer"%}<',
    '>Rafraîchir<': '>{%trans"Rafraîchir"%}<',
    '>Imprimer<': '>{%trans"Imprimer"%}<',
    '>Exporter<': '>{%trans"Exporter"%}<',
    '>Annuler<': '>{%trans"Annuler"%}<',
    '>Confirmer<': '>{%trans"Confirmer"%}<',

    # Table headers
    '>Produit<': '>{%trans"Produit"%}<',
    '>Produits<': '>{%trans"Produits"%}<',
    '>Référence<': '>{%trans"Référence"%}<',
    '>Désignation<': '>{%trans"Désignation"%}<',
    '>Description<': '>{%trans"Description"%}<',
    '>Prix<': '>{%trans"Prix"%}<',
    '>Quantité<': '>{%trans"Quantité"%}<',
    '>Date<': '>{%trans"Date"%}<',
    '>Actions<': '>{%trans"Actions"%}<',
    '>Statut<': '>{%trans"Statut"%}<',
    '>Total<': '>{%trans"Total"%}<',
    '>Client<': '>{%trans"Client"%}<',
    '>Clients<': '>{%trans"Clients"%}<',
    '>Fournisseur<': '>{%trans"Fournisseur"%}<',
    '>Nom<': '>{%trans"Nom"%}<',
    '>Email<': '>{%trans"Email"%}<',
    '>Téléphone<': '>{%trans"Téléphone"%}<',
    '>Adresse<': '>{%trans"Adresse"%}<',
    '>Code<': '>{%trans"Code"%}<',
    '>Catégorie<': '>{%trans"Catégorie"%}<',
    '>Paiement<': '>{%trans"Paiement"%}<',
    '>Entrepôt<': '>{%trans"Entrepôt"%}<',

    # Placeholders (need to be more careful)
    'placeholder="Référence"': 'placeholder="{%trans\'Référence\'%}"',
    'placeholder="Nom"': 'placeholder="{%trans\'Nom\'%}"',
    'placeholder="Email"': 'placeholder="{%trans\'Email\'%}"',
    'placeholder="Téléphone"': 'placeholder="{%trans\'Téléphone\'%}"',
    'placeholder="Adresse"': 'placeholder="{%trans\'Adresse\'%}"',
    'placeholder="Description"': 'placeholder="{%trans\'Description\'%}"',
    'placeholder="Quantité"': 'placeholder="{%trans\'Quantité\'%}"',
}


def quick_translate(content):
    """Replace common texts with {% trans %} tags"""
    for old, new in EXACT_REPLACEMENTS.items():
        content = content.replace(old, new)
    return content


def process_file(file_path):
    """Process a single file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    content = quick_translate(content)

    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    base_dir = Path(__file__).parent
    templates_dir = base_dir / 'templates' / 'frontoffice' / 'page'

    templates = list(templates_dir.glob('*.html'))

    print("Quick Translation of Templates...")
    updated = 0

    for template_path in templates:
        if process_file(template_path):
            print(f"  [OK] {template_path.name}")
            updated += 1
        else:
            print(f"  [SKIP] {template_path.name}")

    print(f"\nUpdated {updated} templates")


if __name__ == '__main__':
    main()
