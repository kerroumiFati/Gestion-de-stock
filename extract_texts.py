#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract French texts from templates for translation
"""
import re
from pathlib import Path

def extract_texts_from_html(html_content):
    """Extract visible French texts from HTML"""
    texts = set()

    # Patterns to extract text
    patterns = [
        # Text between tags like <h1>Text</h1>, <p>Text</p>, <span>Text</span>
        r'<(?:h[1-6]|p|span|div|label|th|td|button|a|li)[^>]*>([^<{]+)</\1>',
        # Placeholder attributes
        r'placeholder=["\']([^"\']+)["\']',
        # Title attributes
        r'title=["\']([^"\']+)["\']',
        # Value in buttons
        r'<button[^>]*>([^<]+)</button>',
        # Simple text patterns
        r'>([A-ZÀ-ÿ][A-Za-zÀ-ÿ\s\-\']{2,50})<',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        for match in matches:
            text = match.strip()
            # Filter out: variables, single chars, pure numbers, HTML tags
            if (text and
                len(text) > 1 and
                not text.startswith('{') and
                not text.startswith('%') and
                not text.isdigit() and
                not text.startswith('<') and
                'var ' not in text and
                'function' not in text and
                'console.' not in text):
                texts.add(text)

    return texts

def main():
    base_dir = Path(__file__).parent
    templates_dir = base_dir / 'templates' / 'frontoffice' / 'page'

    priority_templates = [
        'caisse.html',
        'vente.html',
        'achat.html',
        'produit.html',
        'statistiques.html',
        'client.html',
        'fournisseur.html',
        'categorie.html',
        'parametres.html',
    ]

    all_texts = set()

    print("=" * 80)
    print("EXTRACTION DES TEXTES POUR TRADUCTION")
    print("=" * 80)

    for template_name in priority_templates:
        template_path = templates_dir / template_name

        if not template_path.exists():
            print(f"\n[X] {template_name} - NOT FOUND")
            continue

        print(f"\n[FILE] {template_name}")
        print("-" * 80)

        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        texts = extract_texts_from_html(content)
        all_texts.update(texts)

        print(f"   Found {len(texts)} unique texts in this file")

    # Sort and display all unique texts
    print("\n" + "=" * 80)
    print(f"TOTAL: {len(all_texts)} TEXTES UNIQUES À TRADUIRE")
    print("=" * 80)

    sorted_texts = sorted(all_texts)
    for i, text in enumerate(sorted_texts, 1):
        print(f"{i:3d}. {text}")

    # Save to file
    output_file = base_dir / 'texts_to_translate.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        for text in sorted_texts:
            f.write(f"{text}\n")

    print(f"\n[OK] Liste sauvegardee dans: {output_file}")
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
