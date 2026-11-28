"""Vérification (LECTURE SEULE) de l'affectation des vans aux livreurs.

    python manage.py verifier_vans_livreurs

Contexte (journaux du 28/11/2026) : tous les livreurs étaient rattachés au même entrepôt
« CENTRAL », sans entreprise. Les livraisons étaient refusées en 409 « Stock insuffisant dans le
van CENTRAL » : un stock unique partagé par tous, et l'affectation d'une commande transférait le
stock de CENTRAL vers… CENTRAL (aucune réservation pour le livreur).

Aucune donnée n'est modifiée : le script liste seulement ce qu'il faut corriger dans
Livreurs → Van/Entrepôt assigné (un van par livreur) et dans les paramètres (dépôt des commandes).
"""
from collections import defaultdict

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Vérifie l'affectation des vans aux livreurs (lecture seule, ne modifie rien)."

    def handle(self, *args, **options):
        from API.models import SystemConfig, Warehouse
        from API.distribution_models import LivreurDistribution
        from API.securite_encaissements import company_id_du_livreur

        livreurs = list(LivreurDistribution.objects.select_related('entrepot', 'user__profile').order_by('id'))
        actifs = [l for l in livreurs if l.statut == 'actif']
        problemes = 0

        def titre(t):
            self.stdout.write('\n' + self.style.MIGRATE_HEADING(t))

        titre(f'Livreurs : {len(livreurs)} (dont {len(actifs)} actifs)')

        # 1. Livreurs actifs sans van
        sans_van = [l for l in actifs if not l.entrepot_id]
        titre(f'1. Livreurs actifs sans van : {len(sans_van)}')
        for l in sans_van:
            self.stdout.write(f'   - #{l.id} {l.matricule} {l.nom}')
        problemes += len(sans_van)

        # 2. Un même entrepôt partagé par plusieurs livreurs
        par_entrepot = defaultdict(list)
        for l in actifs:
            if l.entrepot_id:
                par_entrepot[l.entrepot_id].append(l)
        partages = {e: ls for e, ls in par_entrepot.items() if len(ls) > 1}
        titre(f'2. Entrepôts partagés par plusieurs livreurs : {len(partages)}')
        for e_id, ls in partages.items():
            e = ls[0].entrepot
            self.stdout.write(self.style.WARNING(
                f'   - {e.name} ({e.code}, id {e.id}) : {len(ls)} livreurs → '
                + ', '.join(f'#{l.id} {l.nom}' for l in ls)))
        problemes += len(partages)

        # 3. « Van » qui n'est pas un van (code sans « van ») : c'est alors aussi un dépôt possible
        #    pour l'affectation des commandes (transfert du dépôt vers lui-même)
        non_vans = {l.entrepot_id: l.entrepot for l in actifs
                    if l.entrepot_id and 'van' not in (l.entrepot.code or '').lower()}
        titre(f'3. Entrepôts assignés comme van mais dont le code ne contient pas « van » : {len(non_vans)}')
        for e in non_vans.values():
            self.stdout.write(f'   - {e.name} ({e.code}, id {e.id}) — la liste des vans du formulaire Livreurs ne le propose pas')
        problemes += len(non_vans)

        # 4. Van sans entreprise
        vans_sans_co = {l.entrepot_id: l.entrepot for l in actifs if l.entrepot_id and l.entrepot.company_id is None}
        titre(f'4. Vans sans entreprise : {len(vans_sans_co)}')
        for e in vans_sans_co.values():
            self.stdout.write(f'   - {e.name} ({e.code}, id {e.id})')
        problemes += len(vans_sans_co)

        # 5. Livreurs rattachés à aucune entreprise (ni van, ni compte) : visibles par toutes
        sans_co = [l for l in actifs if company_id_du_livreur(l) is None]
        titre(f'5. Livreurs actifs sans entreprise (ni par le van, ni par le compte) : {len(sans_co)}')
        for l in sans_co:
            self.stdout.write(f'   - #{l.id} {l.matricule} {l.nom}')
        problemes += len(sans_co)

        # 6. Dépôt des commandes (paramètres) utilisé aussi comme van d'un livreur
        titre('6. Dépôt des commandes mobiles (Paramètres) utilisé comme van')
        vans_ids = {l.entrepot_id for l in actifs if l.entrepot_id}
        for cfg in SystemConfig.objects.select_related('depot_commandes_mobile'):
            depot = cfg.depot_commandes_mobile
            if depot and depot.id in vans_ids:
                self.stdout.write(self.style.WARNING(
                    f'   - {depot.name} (id {depot.id}) est à la fois le dépôt des commandes et un van'))
                problemes += 1

        # 7. Vans disponibles non assignés (pour la correction)
        libres = Warehouse.objects.filter(is_active=True, code__icontains='van').exclude(id__in=vans_ids)
        titre(f'7. Vans actifs non assignés (disponibles) : {libres.count()}')
        for e in libres:
            self.stdout.write(f'   - {e.name} ({e.code}, id {e.id}, entreprise {e.company_id or "aucune"})')

        self.stdout.write('')
        if problemes:
            self.stdout.write(self.style.WARNING(
                f'{problemes} point(s) à corriger. Rien n\'a été modifié : assignez un van par livreur '
                '(Livreurs → Van/Entrepôt assigné) et rattachez les vans à l\'entreprise.'))
        else:
            self.stdout.write(self.style.SUCCESS('Aucun problème détecté.'))
