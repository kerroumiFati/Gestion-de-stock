"""Liste les clients visités par PLUSIEURS prévendeurs le même jour de la semaine (lecture seule).

    python manage.py verifier_doublons_planning

Causes connues : anciennes affectations sans entreprise à côté d'une affectation avec entreprise
(la règle d'unicité de la base inclut l'entreprise), ou secteur donné à deux prévendeurs avant la
vérification. À corriger dans Distribution → Configuration clients-chauffeurs (avertissement rouge
dans la colonne du jour : cliquer sur le client pour le retirer ou le donner)."""
from collections import defaultdict

from django.core.management.base import BaseCommand

JOURS = {1: 'Lundi', 2: 'Mardi', 3: 'Mercredi', 4: 'Jeudi', 5: 'Vendredi', 6: 'Samedi', 7: 'Dimanche'}


class Command(BaseCommand):
    help = "Liste les clients visités par plusieurs prévendeurs le même jour (aucune modification)."

    def handle(self, *args, **options):
        from API.distribution_models import LivreurDistribution
        from API.distribution_prix_stock import clients_planifies

        chez = defaultdict(list)   # (jour, client) -> [prévendeurs]
        noms = {}
        for livreur in LivreurDistribution.objects.order_by('nom'):
            for jour in range(1, 8):
                for item in clients_planifies(livreur.id, jour):
                    client = item['client']
                    chez[(jour, client.id)].append(f"{livreur.nom} ({item['source']})")
                    noms[client.id] = (f"{client.nom or ''} {client.prenom or ''}".strip(),
                                       getattr(client.company, 'name', '—') if client.company_id else '—')
        doublons = {k: v for k, v in chez.items() if len(v) > 1}
        if not doublons:
            self.stdout.write(self.style.SUCCESS('Aucun doublon : chaque client a au plus un prévendeur par jour.'))
            return
        self.stdout.write(self.style.WARNING(f'{len(doublons)} doublon(s) client/jour :'))
        for (jour, cid), prevendeurs in sorted(doublons.items(), key=lambda x: (noms[x[0][1]][1], x[0][0], noms[x[0][1]][0])):
            nom, entreprise = noms[cid]
            self.stdout.write(f'  [{entreprise}] {JOURS[jour]:9s} {nom} (id {cid}) : ' + ', '.join(prevendeurs))
