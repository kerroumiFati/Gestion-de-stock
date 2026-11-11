"""Retire les mots « undefined » / « null » ajoutés par erreur au nom des livreurs.

L'ancien formulaire de modification (page Livreurs) remplissait la case Prénom avec
« undefined » puis recollait Nom + Prénom à chaque enregistrement.
"""
from django.db import migrations

PARASITES = {'undefined', 'null'}


def nettoyer(apps, schema_editor):
    LivreurDistribution = apps.get_model('API', 'LivreurDistribution')
    for livreur in LivreurDistribution.objects.all():
        mots = [m for m in (livreur.nom or '').split() if m not in PARASITES]
        propre = ' '.join(mots) or livreur.matricule
        if propre != livreur.nom:
            livreur.nom = propre
            livreur.save(update_fields=['nom'])


class Migration(migrations.Migration):

    dependencies = [
        ('API', '0078_libelle_colisage'),
    ]

    operations = [
        migrations.RunPython(nettoyer, migrations.RunPython.noop),
    ]
