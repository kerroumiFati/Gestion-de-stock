from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType

# Define the role names
ADMIN = "Administrateur"
MAGASINIER = "Magasinier"
COMPTABLE = "Comptable"

# Models we expect in the API app and typical permissions we want to map
API_MODELS = {
    # core catalogue / stock
    "Produit": {"magasinier": ["add", "change", "view"], "comptable": ["view"], "admin": "all"},
    "Warehouse": {"magasinier": ["add", "change", "view"], "comptable": ["view"], "admin": "all"},
    "ProductStock": {"magasinier": ["add", "change", "view"], "comptable": ["view"], "admin": "all"},
    "StockMove": {"magasinier": ["add", "change", "view"], "comptable": ["view"], "admin": "all"},
    "InventorySession": {"magasinier": ["add", "change", "view"], "comptable": ["view"], "admin": "all"},
    "InventoryLine": {"magasinier": ["add", "change", "view"], "comptable": ["view"], "admin": "all"},

    # achats / ventes / facturation
    "Achat": {"magasinier": ["add", "change", "view"], "comptable": ["view", "change"], "admin": "all"},
    "BonLivraison": {"magasinier": ["add", "change", "view"], "comptable": ["view"], "admin": "all"},
    "Vente": {"magasinier": ["view"], "comptable": ["add", "change", "view"], "admin": "all"},
    "LigneVente": {"magasinier": ["view"], "comptable": ["add", "change", "view"], "admin": "all"},
    "Facture": {"magasinier": ["view"], "comptable": ["add", "change", "view"], "admin": "all"},
    "LigneFacture": {"magasinier": ["view"], "comptable": ["add", "change", "view"], "admin": "all"},

    # référentiels
    "Categorie": {"magasinier": ["view"], "comptable": ["view"], "admin": "all"},
    "Client": {"magasinier": ["view"], "comptable": ["view", "change"], "admin": "all"},
    "Fournisseur": {"magasinier": ["view", "change"], "comptable": ["view"], "admin": "all"},

    # currency
    "Currency": {"magasinier": ["view"], "comptable": ["view", "change"], "admin": "all"},
    "ExchangeRate": {"magasinier": ["view"], "comptable": ["view", "change"], "admin": "all"},
}

SUPPORTED_ACTIONS = {"add", "change", "delete", "view"}

class Command(BaseCommand):
    help = "Create or update default user roles (Groups) and assign permissions: Administrateur, Magasinier, Comptable"

    def handle(self, *args, **options):
        # Ensure groups exist
        admin_group, _ = Group.objects.get_or_create(name=ADMIN)
        magasinier_group, _ = Group.objects.get_or_create(name=MAGASINIER)
        comptable_group, _ = Group.objects.get_or_create(name=COMPTABLE)

        # Collect all permissions we want to grant per group
        admin_perms = set()
        magasinier_perms = set()
        comptable_perms = set()

        # Iterate through expected models in API app
        for model_name, rules in API_MODELS.items():
            try:
                ct = ContentType.objects.get(app_label="API", model=model_name.lower())
            except ContentType.DoesNotExist:
                # Skip silently if model not present; keeps command idempotent across schemas
                self.stdout.write(self.style.WARNING(f"Model not found (skipped): API.{model_name}"))
                continue

            # Admin gets all perms on this model
            for codename in Permission.objects.filter(content_type=ct).values_list("codename", flat=True):
                admin_perms.add(codename)

            # Magasinier
            acts = rules.get("magasinier", [])
            for act in acts:
                if act in SUPPORTED_ACTIONS:
                    codename = f"{act}_{ct.model}"
                    magasinier_perms.add(codename)

            # Comptable
            acts = rules.get("comptable", [])
            for act in acts:
                if act in SUPPORTED_ACTIONS:
                    codename = f"{act}_{ct.model}"
                    comptable_perms.add(codename)

        def set_group_perms(group: Group, codenames: set):
            perms = Permission.objects.filter(codename__in=list(codenames))
            group.permissions.set(perms)
            group.save()

        # Apply permissions to groups
        set_group_perms(admin_group, admin_perms)
        set_group_perms(magasinier_group, magasinier_perms)
        set_group_perms(comptable_group, comptable_perms)

        self.stdout.write(self.style.SUCCESS("Roles and permissions have been configured."))

        # Helpful hint
        self.stdout.write("Assign users to groups via Django admin or programmatically:")
        self.stdout.write("  user.groups.add(Group.objects.get(name='Magasinier'))")
