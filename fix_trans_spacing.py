#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix spacing in {% trans %} tags
"""
import re
from pathlib import Path


def fix_trans_tags(content):
    """Fix malformed {% trans %} tags"""

    # Fix {%trans" -> {% trans "
    content = re.sub(r'{%trans"', r'{% trans "', content)
    content = re.sub(r"{%trans'", r"{% trans '", content)

    # Fix "% } -> " %}
    content = re.sub(r'"% }', r'" %}', content)
    content = re.sub(r"'% }", r"' %}", content)

    # Fix "%} -> " %}
    content = re.sub(r'"%}', r'" %}', content)
    content = re.sub(r"'%}", r"' %}", content)

    return content


def fix_file(file_path):
    """Fix a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        content = fix_trans_tags(content)

        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    base_dir = Path(__file__).parent

    # Fix all HTML templates in frontoffice
    templates_dir = base_dir / 'templates' / 'frontoffice'

    html_files = list(templates_dir.rglob('*.html'))

    print("Fixing {% trans %} tag spacing...")
    fixed = 0

    for file_path in html_files:
        if fix_file(file_path):
            print(f"  [FIXED] {file_path.relative_to(templates_dir)}")
            fixed += 1

    print(f"\nFixed {fixed} files")


if __name__ == '__main__':
    main()
