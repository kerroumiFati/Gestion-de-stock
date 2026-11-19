from django.db import migrations, models
import django.db.models.deletion


def reprendre_passee_par(apps, schema_editor):
    """Anciennes commandes passées depuis le téléphone (app_id) et jamais affectées à un
    autre livreur : le livreur actuel est celui qui les a passées. Les commandes déjà
    affectées (transfert « Transfert automatique pour commande <ref> ») restent vides,
    car le vendeur d'origine n'a pas été conservé."""
    CommandeClient = apps.get_model('API', 'CommandeClient')
    TransfertStock = apps.get_model('API', 'TransfertStock')
    affectees = set()
    for notes in TransfertStock.objects.filter(notes__startswith='Transfert automatique pour commande ').values_list('notes', flat=True):
        affectees.add(notes[len('Transfert automatique pour commande '):].strip())
    for cmd in CommandeClient.objects.filter(passee_par__isnull=True, livreur__isnull=False).exclude(app_id__isnull=True).exclude(app_id=''):
        if cmd.reference not in affectees:
            CommandeClient.objects.filter(pk=cmd.pk).update(passee_par_id=cmd.livreur_id)


class Migration(migrations.Migration):

    dependencies = [
        ('API', '0086_commande_tournee_livraison'),
    ]

    operations = [
        migrations.AddField(
            model_name='commandeclient',
            name='passee_par',
            field=models.ForeignKey(blank=True, help_text="Vendeur qui a passé la commande (ne change pas à l'affectation)", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='commandes_passees', to='API.livreurdistribution'),
        ),
        migrations.RunPython(reprendre_passee_par, migrations.RunPython.noop),
    ]
