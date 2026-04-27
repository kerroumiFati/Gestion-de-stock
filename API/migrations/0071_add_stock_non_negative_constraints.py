from django.db import migrations, models


def clamp_negative_stock(apps, schema_editor):
    """Ramène à 0 tout stock négatif existant avant d'appliquer la contrainte CHECK."""
    Produit = apps.get_model('API', 'Produit')
    ProductStock = apps.get_model('API', 'ProductStock')
    Produit.objects.filter(quantite__lt=0).update(quantite=0)
    ProductStock.objects.filter(quantity__lt=0).update(quantity=0)


class Migration(migrations.Migration):

    dependencies = [
        ('API', '0070_add_paiement_solde'),
    ]

    operations = [
        migrations.RunPython(clamp_negative_stock, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='produit',
            constraint=models.CheckConstraint(
                check=models.Q(quantite__gte=0),
                name='produit_quantite_non_negative',
            ),
        ),
        migrations.AddConstraint(
            model_name='productstock',
            constraint=models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name='productstock_quantity_non_negative',
            ),
        ),
    ]
