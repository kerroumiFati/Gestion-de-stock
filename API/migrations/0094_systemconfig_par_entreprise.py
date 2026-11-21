# Paramètres généraux : une configuration par entreprise au lieu d'une seule partagée.

from django.db import migrations, models
import django.db.models.deletion


def creer_parametres_par_entreprise(apps, schema_editor):
    """Crée les paramètres de chaque entreprise à partir de l'ancienne configuration partagée (pk=1).

    - Langue, devise, impression automatique : recopiées pour tout le monde (rien ne change à l'usage).
    - Entrepôt par défaut / dépôt des commandes mobiles : gardés seulement pour l'entreprise
      à qui l'entrepôt appartient (une entreprise ne garde jamais l'entrepôt d'une autre).
    - En-tête et pied du ticket (nom, adresse, téléphone, message) : gardés seulement pour
      l'entreprise qui les a vraisemblablement saisis (propriétaire de l'entrepôt / du dépôt configuré,
      ou la seule entreprise). Les autres retombent sur la fiche de leur propre entreprise.
    - La configuration partagée reste, sans entreprise, pour les comptes qui n'ont pas d'entreprise.
    """
    SystemConfig = apps.get_model('API', 'SystemConfig')
    Company = apps.get_model('API', 'Company')

    ancienne = SystemConfig.objects.filter(company__isnull=True).order_by('pk').first()
    if ancienne is None:
        return

    # PostgreSQL : la ligne d'origine a pu être insérée avec un id explicite (id=1) sans faire avancer
    # la séquence ; le premier INSERT reprendrait alors l'id 1 (IntegrityError vue en production).
    from django.core.management.color import no_style
    for sql in schema_editor.connection.ops.sequence_reset_sql(no_style(), [SystemConfig]):
        schema_editor.execute(sql)

    entreprises = list(Company.objects.all())
    proprietaire_id = None
    for w in (ancienne.default_warehouse, ancienne.depot_commandes_mobile):
        if w is not None and w.company_id:
            proprietaire_id = w.company_id
            break
    if proprietaire_id is None and len(entreprises) == 1:
        proprietaire_id = entreprises[0].pk

    for company in entreprises:
        if SystemConfig.objects.filter(company=company).exists():
            continue
        est_proprietaire = company.pk == proprietaire_id

        def entrepot_si_a_elle(w):
            return w if (w is not None and w.company_id in (company.pk, None)) else None

        SystemConfig.objects.create(
            company=company,
            language=ancienne.language or 'fr',
            default_currency=ancienne.default_currency,
            auto_print_ticket=ancienne.auto_print_ticket,
            default_warehouse=entrepot_si_a_elle(ancienne.default_warehouse),
            depot_commandes_mobile=entrepot_si_a_elle(ancienne.depot_commandes_mobile),
            ticket_footer_message=ancienne.ticket_footer_message if est_proprietaire else '',
            ticket_company_name=ancienne.ticket_company_name if est_proprietaire else '',
            ticket_company_address=ancienne.ticket_company_address if est_proprietaire else '',
            ticket_company_phone=ancienne.ticket_company_phone if est_proprietaire else '',
        )


def supprimer_parametres_par_entreprise(apps, schema_editor):
    SystemConfig = apps.get_model('API', 'SystemConfig')
    SystemConfig.objects.filter(company__isnull=False).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('API', '0093_paiement_ventes_pc_validees'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemconfig',
            name='company',
            field=models.OneToOneField(blank=True, help_text='Entreprise à laquelle appartiennent ces paramètres', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='system_config', to='API.company'),
        ),
        migrations.RunPython(creer_parametres_par_entreprise, supprimer_parametres_par_entreprise),
    ]
