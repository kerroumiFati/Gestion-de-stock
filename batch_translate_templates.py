#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch add {% trans %} tags to templates
This is a SMART script that will:
1. Add {% load i18n %} if not present
2. Wrap common French texts in {% trans %} tags
3. Handle placeholders, labels, headings, buttons, etc.
"""
import re
from pathlib import Path


# Common patterns that need translation
TRANSLATION_PATTERNS = [
    # Headers and titles
    (r'<h[1-6][^>]*>([^<{%]+)</h', r'<h\1>{%% trans "\2" %%}</h'),
    # Labels
    (r'<label[^>]*>([^<{%]+?)(<span|</label)', r'<label>{%% trans "\1" %%}\2'),
    # Buttons with icon + text
    (r'(<button[^>]*><i[^>]*></i>)\s*([^<{%]+)(</button>)', r'\1 {% trans "\2" %}\3'),
    # Option values
    (r'(<option[^>]*>)([^<{%]+)(</option>)', r'\1{% trans "\2" %}\3'),
    # Simple text in table headers
    (r'<th>([^<{%]+)</th>', r'<th>{% trans "\1" %}</th>'),
]


def add_trans_tags(content):
    """Add {% trans %} tags to common patterns"""

    # Replace each pattern
    for pattern, replacement in TRANSLATION_PATTERNS:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    return content


def process_template(file_path):
    """Process a single template file"""
    print(f"\nProcessing: {file_path.name}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Add {% load i18n %} if not present
    if '{% load i18n %}' not in content:
        if '{% load static %}' in content:
            content = content.replace('{% load static %}', '{% load static %}\n{% load i18n %}')
            print("  + Added {% load i18n %}")
        else:
            content = '{% load i18n %}\n' + content
            print("  + Added {% load i18n %} at start")

    # Add trans tags
    content = add_trans_tags(content)

    # Check if anything changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✓ Template updated")
        return True
    else:
        print("  - No changes needed")
        return False


def main():
    base_dir = Path(__file__).parent
    templates_dir = base_dir / 'templates' / 'frontoffice' / 'page'

    priority_files = [
        'vente.html',
        'achat.html',
        'produit.html',
        'client.html',
        'fournisseur.html',
        'categorie.html',
        'statistiques.html',
        'parametres.html',
        'entrepots.html',
    ]

    print("=" * 80)
    print("BATCH TRANSLATION OF TEMPLATES")
    print("=" * 80)

    updated = 0
    for filename in priority_files:
        file_path = templates_dir / filename
        if file_path.exists():
            if process_template(file_path):
                updated += 1
        else:
            print(f"\n✗ {filename} - NOT FOUND")

    print(f"\n" + "=" * 80)
    print(f"DONE: {updated} templates updated")
    print("=" * 80)


if __name__ == '__main__':
    main()
