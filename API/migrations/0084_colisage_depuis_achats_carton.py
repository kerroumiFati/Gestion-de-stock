"""Reprise des données : pour chaque produit sans Colisage actif, créer le Colisage
à partir de son dernier achat en carton (pieces_par_carton > 1).
Désormais Achat.save() le fait automatiquement à chaque achat en carton."""
from django.db import migrations


def colisage_depuis_achats(apps, schema_editor):
    Achat = apps.get_model('API', 'Achat')
    Conditionnement = apps.get_model('API', 'Conditionnement')

    deja = set(
        Conditionnement.objects.filter(is_active=True).values_list('produit_id', flat=True)
    )
    vus = set()
    achats = (
        Achat.objects.filter(unite_achat='carton', pieces_par_carton__gt=1)
        .order_by('produit_id', '-date_Achat', '-id')
        .values_list('produit_id', 'pieces_par_carton')
    )
    for produit_id, upc in achats:
        if produit_id in vus or produit_id in deja:
            continue
        vus.add(produit_id)
        Conditionnement.objects.create(produit_id=produit_id, unites_par_carton=upc, is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('API', '0083_depot_commandes_mobile'),
    ]

    operations = [
        migrations.RunPython(colisage_depuis_achats, migrations.RunPython.noop),
    ]
