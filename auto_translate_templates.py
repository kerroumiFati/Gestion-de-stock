#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Automatically add {% trans %} tags to all templates
"""
import re
from pathlib import Path

# Common texts that should be translated
TEXTS_TO_TRANSLATE = [
    # From extraction
    "Point de Vente", "Scanner Code-Barres", "Scanner code-barres ou référence...",
    "Sélection manuelle", "Panier", "Panier vide", "article(s)",
    "Informations de Vente", "Sous-total HT", "Remise (%)", "Total TTC",
    "Produit", "Prix U", "Qté", "Total", "Actions",
    "Client", "Entrepôt", "Paiement", "Espèces", "Carte", "Chèque", "Virement", "Crédit",
    "Ajouter", "Modifier", "Supprimer", "Fermer", "Confirmer",
    "Nom", "Prénom", "Email", "Téléphone", "Adresse", "Référence", "Désignation",
    "Description", "Prix", "Prix unitaire", "Quantité", "Date", "Catégorie",
    "Fournisseur", "Code", "Code-barres", "Numéro", "Statut",
    "Gestion des Achats", "Gestion des Ventes", "Gestion des Produits",
    "Filtrer par produit", "Filtrer par statut", "Tous les produits",
    "Brouillons", "Finalisées", "Toutes",
    "Sélectionner un produit", "Sélectionner un entrepôt", "Sélectionner un fournisseur",
    "Observations", "Commentaires", "Type de paiement",
    # Additional common terms
    "Enregistrer", "Annuler", "Rechercher", "Filtrer", "Rafraîchir",
    "Imprimer", "Exporter", "Valider", "Vider",  "Choisir",
    "Liste", "Nouveau", "Edition", "Détails", "Retour",
]

def add_i18n_to_template(file_path):
    """Add {% load i18n %} and {% trans %} tags to a template"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already has {% load i18n %}
    if '{% load i18n %}' in content:
        print(f"  [SKIP] Already has i18n")
        return False

    # Add {% load i18n %} after {% load static %} if exists
    if '{% load static %}' in content:
        content = content.replace('{% load static %}', '{% load static %}\n{% load i18n %}')
    else:
        # Add at the beginning
        content = '{% load i18n %}\n' + content

    # Replace common text patterns with {% trans %}
    for text in TEXTS_TO_TRANSLATE:
        # Escape special regex characters
        escaped_text = re.escape(text)

        # Replace in different contexts
        # 1. Between > and < (tag content)
        content = re.sub(
            f'>({escaped_text})<',
            r'>{{% trans "\1" %}}<',
            content
        )

        # 2. In placeholder attributes
        content = re.sub(
            f'placeholder="({escaped_text})"',
            r'placeholder="{% trans "\1" %}"',
            content
        )

        # 3. In labels
        content = re.sub(
            f'<label([^>]*)>({escaped_text})',
            r'<label\1>{% trans "\2" %}',
            content
        )

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  [OK] Template updated")
    return True


def main():
    base_dir = Path(__file__).parent
    templates_dir = base_dir / 'templates' / 'frontoffice' / 'page'

    templates = list(templates_dir.glob('*.html'))

    print("=" * 80)
    print("AUTO-TRADUCTION DES TEMPLATES")
    print("=" * 80)

    updated_count = 0
    for template_path in templates:
        print(f"\n{template_path.name}")
        if add_i18n_to_template(template_path):
            updated_count += 1

    print(f"\n" + "=" * 80)
    print(f"TERMINE: {updated_count} templates mis à jour")
    print("=" * 80)


if __name__ == '__main__':
    main()
