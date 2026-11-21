"""Recalcule Produit.quantite = somme des stocks par dépôt (ProductStock, TOUS les dépôts).

    python manage.py resync_stock --dry-run   # affiche les écarts sans rien modifier
    python manage.py resync_stock             # corrige les totaux
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from API.models import Produit, ProductStock


class Command(BaseCommand):
    help = "Recalcule le stock total de chaque produit à partir du stock de ses dépôts."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Affiche seulement les écarts, sans rien modifier")

    def handle(self, *args, **options):
        dry = options['dry_run']
        totaux = dict(ProductStock.objects.values('produit_id').annotate(t=Sum('quantity')).values_list('produit_id', 't'))
        ecarts = []
        for p in Produit.objects.all().order_by('reference').only('id', 'reference', 'designation', 'quantite'):
            total = totaux.get(p.id) or 0
            if (p.quantite or 0) != total:
                ecarts.append((p, p.quantite or 0, total))

        nb = Produit.objects.count()
        if not ecarts:
            self.stdout.write(self.style.SUCCESS(f"{nb} produit(s) vérifié(s) : aucun écart."))
            return
        self.stdout.write(f"{'Référence':<20} {'Désignation':<35} {'Total actuel':>12} {'Somme dépôts':>12} {'Écart':>8}")
        for p, actuel, total in ecarts:
            self.stdout.write(f"{(p.reference or '')[:20]:<20} {(p.designation or '')[:35]:<35} "
                              f"{actuel:>12} {total:>12} {total - actuel:>+8}")
        if dry:
            self.stdout.write(self.style.WARNING(
                f"{len(ecarts)} produit(s) sur {nb} en écart (simulation : rien n'a été modifié)."))
            return
        with transaction.atomic():
            for p, _actuel, total in ecarts:
                Produit.objects.filter(pk=p.pk).update(quantite=total)
        self.stdout.write(self.style.SUCCESS(f"{len(ecarts)} produit(s) corrigé(s) sur {nb}."))
