from django.db import migrations, models
import django.db.models.deletion


def reprendre_entrepot_livreur(apps, schema_editor):
    """Tournées existantes : reprendre l'entrepôt actuel de la fiche du livreur."""
    TourneeMobile = apps.get_model('API', 'TourneeMobile')
    tournees = TourneeMobile.objects.filter(
        entrepot_depart__isnull=True, livreur__entrepot__isnull=False
    ).select_related('livreur')
    for tournee in tournees:
        tournee.entrepot_depart_id = tournee.livreur.entrepot_id
        tournee.save(update_fields=['entrepot_depart'])


class Migration(migrations.Migration):

    dependencies = [
        ('API', '0074_objectifs_vendeurs_entrepot_rattachement'),
    ]

    operations = [
        migrations.AddField(
            model_name='tourneemobile',
            name='entrepot_depart',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tournees_depart', to='API.warehouse',
                verbose_name='Entrepôt de départ',
                help_text="Entrepôt / van de départ de la tournée (reporté sur la fiche du livreur)",
            ),
        ),
        migrations.RunPython(reprendre_entrepot_livreur, migrations.RunPython.noop),
    ]
