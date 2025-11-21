"""
Script pour patcher automatiquement les modeles de distribution avec le champ company
"""
import re

file_path = r"C:\Users\KB\Documents\autre\GestionStock-django-master\GestionStock-django-master\API\distribution_models.py"

# Lire le fichier
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Modeles a patcher (ceux qui n'ont pas encore company)
models_to_patch = [
    ('ArretTourneeMobile', 'arrets_tournees_mobiles'),
    ('VenteTourneeMobile', 'ventes_tournees_mobiles'),
    ('LigneVenteTourneeMobile', 'lignes_ventes_tournees_mobiles'),
    ('RapportCaisseMobile', 'rapports_caisses_mobiles'),
    ('BonLivraisonVan', 'bons_livraison_vans'),
    ('LigneBonLivraisonVan', 'lignes_bons_livraison_vans'),
    ('LigneCommandeClient', 'lignes_commandes_clients'),
]

company_field_template = """
    # Multi-tenancy
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='{related_name}',
                               help_text='Entreprise à laquelle appartient cet enregistrement')
"""

def add_company_field(content, model_name, related_name):
    """Ajoute le champ company avant # Metadonnees ou created_at"""
    # Pattern pour trouver la section metadata ou created_at du modele
    # On cherche le modele specifique
    pattern = rf"(class {model_name}\(models\.Model\):.*?)(    # Métadonnées\s+created_at|    created_at)"

    def replacer(match):
        before = match.group(1)
        metadata_or_created = match.group(2)

        # Verifier si company existe deja
        if 'company = models.ForeignKey' in before:
            return match.group(0)  # Ne rien changer

        # Ajouter le champ company
        company_code = company_field_template.format(related_name=related_name)
        return before + company_code + "\n" + metadata_or_created

    new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
    return new_content

print("=" * 80)
print("PATCH DES MODELES DE DISTRIBUTION")
print("=" * 80)

modified = False
for model_name, related_name in models_to_patch:
    print(f"\nTraitement de {model_name}...")

    new_content = add_company_field(content, model_name, related_name)

    if new_content != content:
        print(f"  [OK] Champ company ajoute")
        content = new_content
        modified = True
    else:
        print(f"  [-] Deja present ou modele non trouve")

if modified:
    # Sauvegarder le fichier modifie
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\n" + "=" * 80)
    print("FICHIER MODIFIE AVEC SUCCES!")
    print("=" * 80)
    print("\nProchaines etapes:")
    print("  1. python manage.py makemigrations API")
    print("  2. python manage.py migrate")
else:
    print("\n" + "=" * 80)
    print("AUCUNE MODIFICATION NECESSAIRE")
    print("=" * 80)
