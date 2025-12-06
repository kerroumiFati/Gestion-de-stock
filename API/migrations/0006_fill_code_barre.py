from django.db import migrations

def fill_code_barre(apps, schema_editor):
    Produit = apps.get_model('API', 'Produit')
    for p in Produit.objects.all():
        if not getattr(p, 'code_barre', None):
            p.code_barre = f"AUTO-{p.id:06d}"
            p.save(update_fields=['code_barre'])

def reverse_code_barre(apps, schema_editor):
    # No-op reverse
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('API', '0005_produit_code_barre'),
    ]

    operations = [
        migrations.RunPython(fill_code_barre, reverse_code_barre),
    ]
