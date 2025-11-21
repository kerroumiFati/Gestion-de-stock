#!/usr/bin/env python
"""
Compile .po files to .mo files without needing gettext installed
Uses Python's built-in msgfmt functionality
"""
import os
import sys
from pathlib import Path


def compile_po_file(po_file):
    """Compile a .po file to .mo using Python"""
    import struct
    import sys

    # Force UTF-8 encoding for stdout on Windows
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    mo_file = po_file.replace('.po', '.mo')

    print(f"Compiling {po_file} -> {mo_file}")

    # Read the .po file with explicit UTF-8 encoding
    with open(po_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Parse the .po file (simple parser)
    messages = {}
    msgid = None
    msgstr = None
    in_msgid = False
    in_msgstr = False

    for line in lines:
        line = line.strip()

        if line.startswith('msgid "'):
            msgid = line[7:-1]  # Remove msgid " and trailing "
            in_msgid = True
            in_msgstr = False
        elif line.startswith('msgstr "'):
            msgstr = line[8:-1]  # Remove msgstr " and trailing "
            in_msgstr = True
            in_msgid = False
        elif line.startswith('"') and in_msgid:
            msgid += line[1:-1]
        elif line.startswith('"') and in_msgstr:
            msgstr += line[1:-1]
        elif line == '':
            if msgid is not None and msgstr is not None:
                if msgid and msgstr:  # Don't include header or empty translations
                    messages[msgid] = msgstr
                msgid = None
                msgstr = None
                in_msgid = False
                in_msgstr = False

    # Add last message if exists
    if msgid is not None and msgstr is not None and msgid and msgstr:
        messages[msgid] = msgstr

    print(f"Found {len(messages)} translations")

    # Generate .mo file (GNU gettext format)
    keys = sorted(messages.keys())
    offsets = []
    ids = b''
    strs = b''

    for key in keys:
        ids += key.encode('utf-8') + b'\x00'
        strs += messages[key].encode('utf-8') + b'\x00'

    # Build the hash table
    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids)

    koffsets = []
    voffsets = []

    offset = 0
    for key in keys:
        msg_bytes = key.encode('utf-8')
        koffsets.append((len(msg_bytes), keystart + offset))
        offset += len(msg_bytes) + 1

    offset = 0
    for key in keys:
        msg_bytes = messages[key].encode('utf-8')
        voffsets.append((len(msg_bytes), valuestart + offset))
        offset += len(msg_bytes) + 1

    # Write the .mo file
    with open(mo_file, 'wb') as f:
        # Magic number
        f.write(struct.pack('I', 0x950412de))
        # Version
        f.write(struct.pack('I', 0))
        # Number of entries
        f.write(struct.pack('I', len(keys)))
        # Offset of table with original strings
        f.write(struct.pack('I', 7 * 4))
        # Offset of table with translation strings
        f.write(struct.pack('I', 7 * 4 + len(keys) * 8))
        # Size of hashing table (0 = no hashing)
        f.write(struct.pack('I', 0))
        # Offset of hashing table
        f.write(struct.pack('I', 0))

        # Write original strings offset table
        for length, offset in koffsets:
            f.write(struct.pack('I', length))
            f.write(struct.pack('I', offset))

        # Write translation strings offset table
        for length, offset in voffsets:
            f.write(struct.pack('I', length))
            f.write(struct.pack('I', offset))

        # Write original strings
        f.write(ids)
        # Write translation strings
        f.write(strs)

    print(f"[OK] Created {mo_file}")
    return True


def main():
    base_dir = Path(__file__).parent
    locale_dir = base_dir / 'locale'

    if not locale_dir.exists():
        print(f"Error: {locale_dir} does not exist")
        return 1

    # Find all .po files
    po_files = list(locale_dir.glob('*/LC_MESSAGES/*.po'))

    if not po_files:
        print("No .po files found!")
        return 1

    print(f"Found {len(po_files)} .po file(s)")

    for po_file in po_files:
        try:
            compile_po_file(str(po_file))
        except Exception as e:
            print(f"Error compiling {po_file}: {e}")
            return 1

    print("\n[OK] All translations compiled successfully!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
