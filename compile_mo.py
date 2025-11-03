#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compile .po files to .mo files using polib
"""
import os
import sys
from pathlib import Path

# Force UTF-8 encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

try:
    import polib
except ImportError:
    print("Error: polib is not installed. Run: pip install polib")
    sys.exit(1)


def compile_po_files():
    """Compile all .po files in locale directory"""
    base_dir = Path(__file__).parent
    locale_dir = base_dir / 'locale'

    if not locale_dir.exists():
        print(f"Error: {locale_dir} does not exist")
        return False

    # Find all .po files
    po_files = list(locale_dir.glob('*/LC_MESSAGES/*.po'))

    if not po_files:
        print("No .po files found!")
        return False

    print(f"Found {len(po_files)} .po file(s)\n")

    success_count = 0
    for po_file in po_files:
        try:
            print(f"Compiling: {po_file.relative_to(base_dir)}")

            # Load the .po file
            po = polib.pofile(str(po_file), encoding='utf-8')

            # Get the .mo file path
            mo_file = po_file.with_suffix('.mo')

            # Save as .mo
            po.save_as_mofile(str(mo_file))

            print(f"  -> Created: {mo_file.relative_to(base_dir)}")
            print(f"  -> Entries: {len(po)} translations\n")

            success_count += 1

        except Exception as e:
            print(f"  -> ERROR: {e}\n")
            return False

    print(f"[SUCCESS] Compiled {success_count} file(s)")
    return True


if __name__ == '__main__':
    if compile_po_files():
        sys.exit(0)
    else:
        sys.exit(1)
