"""Lignes des ventes faites sur le téléphone : le prix envoyé est le prix payé (TTC), mais le
modèle ajoutait 20 % de TVA par défaut (taux_tva=20), d'où des lignes à 120 % du total de la
vente. On remet ces lignes à taux 0 : montant TTC = quantité x prix."""
from decimal import Decimal
from django.db import migrations


def lignes_sans_tva(apps, schema_editor):
    Ligne = apps.get_model('API', 'LigneVenteTourneeMobile')
    for l in Ligne.objects.exclude(taux_tva=0):
        ht = Decimal(l.quantite) * (l.prix_unitaire or Decimal('0'))
        Ligne.objects.filter(pk=l.pk).update(taux_tva=Decimal('0'), montant_ht=ht,
                                             montant_tva=Decimal('0'), montant_ttc=ht)


class Migration(migrations.Migration):
    dependencies = [('API', '0087_commande_passee_par')]
    operations = [migrations.RunPython(lignes_sans_tva, migrations.RunPython.noop)]
