"""
Script pour ajouter default=1 aux champs company seulement
"""
import re

file_path = r"C:\Users\KB\Documents\autre\GestionStock-django-master\GestionStock-django-master\API\distribution_models.py"

# Lire le fichier
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern pour trouver les champs company SANS default
# Format: company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='...'
pattern = r"(company = models\.ForeignKey\('Company', on_delete=models\.CASCADE), (related_name='[^']+',)"

# Remplacer par: company = models.ForeignKey('Company', on_delete=models.CASCADE, default=1, related_name='...'
replacement = r"\1, default=1, \2"

new_content = re.sub(pattern, replacement, content)

# Compter les modifications
count = len(re.findall(pattern, content))

print("=" * 80)
print("AJOUT DE default=1 AUX CHAMPS company")
print("=" * 80)
print(f"\nNombre de champs company modifies: {count}")

if count > 0:
    # Sauvegarder
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("\n[OK] Fichier modifie avec succes!")
else:
    print("\n[INFO] Aucune modification necessaire")

print("=" * 80)
