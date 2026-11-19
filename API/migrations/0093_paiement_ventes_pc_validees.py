"""Ventes du PC validées hors crédit et SANS aucun paiement : elles ont été payées au comptoir
(la Caisse n'a pas de champ « montant reçu »), mais aucun paiement n'avait été enregistré, si
bien qu'elles apparaissaient « à payer » (et comme dettes dans le compte client).
On enregistre le paiement du total. Ventes à crédit et ventes déjà (partiellement) payées : intactes."""
from django.db import migrations


def reprendre(apps, schema_editor):
    Vente = apps.get_model('API', 'Vente')
    PaiementVente = apps.get_model('API', 'PaiementVente')
    for v in Vente.objects.filter(statut='completed').exclude(type_paiement='credit'):
        if v.total_ttc and v.total_ttc > 0 and not PaiementVente.objects.filter(vente=v).exists():
            PaiementVente.objects.create(
                vente=v, montant=v.total_ttc, date_paiement=v.date_vente,
                moyen_paiement=v.type_paiement if v.type_paiement in ('cash', 'card', 'check', 'transfer') else 'other',
                notes='Reprise : payé à la validation de la vente')


class Migration(migrations.Migration):
    dependencies = [('API', '0092_paiement_client')]
    operations = [migrations.RunPython(reprendre, migrations.RunPython.noop)]
