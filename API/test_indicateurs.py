"""Tests des indicateurs de performance des vendeurs (API/indicateurs.py).

Periode de reference : du lundi 7 au dimanche 13 septembre 2026, "aujourd'hui" fixe
au 13 pour que tous les jours planifies soient comptes.
"""
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .indicateurs import calculer_indicateurs, calculer_indicateurs_vendeur
from .models import Categorie, Client, Produit, Warehouse
from .distribution_models import (
    ArretTourneeMobile, ClientLivreurHebdo, CommandeClient, LigneCommandeClient,
    LigneVenteTourneeMobile, LivreurDistribution, ObjectifVendeur, TourneeMobile,
    VenteTourneeMobile, VisiteClient,
)

DEBUT, FIN = date(2026, 9, 7), date(2026, 9, 13)
LUNDI, MARDI, MERCREDI = date(2026, 9, 7), date(2026, 9, 8), date(2026, 9, 9)


def _dt(d, h=10):
    return timezone.make_aware(datetime(d.year, d.month, d.day, h, 0))


class IndicateursTests(TestCase):
    def setUp(self):
        self.ent = Warehouse.objects.create(code='ENT1', name='Frais')
        self.cat = Categorie.objects.create(nom='Boissons')
        self.produit = Produit.objects.create(reference='EAU', code_barre='1', designation='Eau', prixU=Decimal('10'),
                                              categorie=self.cat, entrepot_rattachement=self.ent)
        self.vendeur = LivreurDistribution.objects.create(matricule='V1', nom='Ahmed', telephone='0')
        self.clients = [Client.objects.create(nom=f'C{i}', prenom='x', telephone=str(i)) for i in range(5)]
        self._n = 0

    # ---- fabriques ----
    def _planning(self, client, jour_semaine, **kw):
        return ClientLivreurHebdo.objects.create(livreur=self.vendeur, client=client, jour_semaine=jour_semaine, **kw)

    def _tournee(self, jour):
        t, _ = TourneeMobile.objects.get_or_create(livreur=self.vendeur, date_tournee=jour,
                                                   defaults={'numero_tournee': f'T-{jour.isoformat()}'})
        return t

    def _vente(self, client, jour, montant):
        self._n += 1
        v = VenteTourneeMobile.objects.create(tournee=self._tournee(jour), client=client, numero_vente=f'V-{self._n}',
                                              date_vente=_dt(jour), type_paiement='especes', montant_total=montant)
        LigneVenteTourneeMobile.objects.create(vente=v, produit=self.produit, quantite=1, prix_unitaire=montant,
                                               taux_tva=0, montant_ht=montant, montant_tva=0, montant_ttc=montant)
        return v

    def _commande(self, client, jour, montant, statut='pending'):
        self._n += 1
        c = CommandeClient.objects.create(client=client, livreur=self.vendeur, statut=statut,
                                          reference=f'CMD-{self._n}', montant_total_ttc=montant, montant_total_ht=montant)
        CommandeClient.objects.filter(pk=c.pk).update(date_commande=_dt(jour), montant_total_ttc=montant, statut=statut)
        l = LigneCommandeClient.objects.create(commande=c, produit=self.produit, quantite=1, prix_unitaire_ht=montant,
                                               taux_tva=0, montant_ht=montant, montant_tva=0, montant_ttc=montant)
        LigneCommandeClient.objects.filter(pk=l.pk).update(montant_ttc=montant)
        CommandeClient.objects.filter(pk=c.pk).update(montant_total_ttc=montant, statut=statut)
        return c

    def _calc(self, debut=DEBUT, fin=FIN, aujourd_hui=FIN):
        return calculer_indicateurs_vendeur(self.vendeur, debut, fin, aujourd_hui=aujourd_hui)

    # ---- taux de visite ----
    def test_taux_de_visite_sur_planning_hebdo(self):
        # Lundi : C0, C1 planifies ; mardi : C2, C3 planifies -> 4 planifies
        self._planning(self.clients[0], 1); self._planning(self.clients[1], 1)
        self._planning(self.clients[2], 2); self._planning(self.clients[3], 2)
        # Visites : C0 lundi (vente), C2 mardi (absent), C4 mardi hors planning
        VisiteClient.objects.create(livreur=self.vendeur, client=self.clients[0], date_visite=LUNDI, resultat='vente')
        VisiteClient.objects.create(livreur=self.vendeur, client=self.clients[2], date_visite=MARDI, resultat='absent')
        VisiteClient.objects.create(livreur=self.vendeur, client=self.clients[4], date_visite=MARDI, resultat='commande')
        ind = self._calc()
        self.assertEqual(ind['clients_planifies'], 4)
        self.assertEqual(ind['clients_planifies_visites'], 2)
        self.assertEqual(ind['visites_hors_planning'], 1)
        self.assertEqual(ind['taux_visite'], 50.0)
        # Reussite : 2 fructueuses (C0 vente, C4 commande) sur 3 visites
        self.assertEqual(ind['visites'], 3)
        self.assertEqual(ind['visites_fructueuses'], 2)
        self.assertEqual(ind['taux_reussite'], 66.7)

    def test_jours_futurs_et_validite_du_planning(self):
        self._planning(self.clients[0], 1)                                   # lundi
        self._planning(self.clients[1], 3)                                   # mercredi (futur)
        self._planning(self.clients[2], 1, date_fin=date(2026, 8, 31))       # expire
        self._planning(self.clients[3], 1, is_active=False)                  # inactif
        ind = self._calc(aujourd_hui=MARDI)   # on est mardi : mercredi pas encore compte
        self.assertEqual(ind['clients_planifies'], 1)

    def test_arrets_de_tournee(self):
        t = self._tournee(LUNDI)
        ArretTourneeMobile.objects.create(tournee=t, client=self.clients[0], statut='livre')
        ArretTourneeMobile.objects.create(tournee=t, client=self.clients[1], statut='echec', ordre_passage=2)
        ArretTourneeMobile.objects.create(tournee=t, client=self.clients[2], statut='en_attente', ordre_passage=3)
        ind = self._calc()
        self.assertEqual(ind['clients_planifies'], 3)
        self.assertEqual(ind['clients_planifies_visites'], 2)   # livre + echec
        self.assertEqual(ind['taux_visite'], 66.7)
        self.assertEqual(ind['visites_fructueuses'], 1)          # livre seulement
        self.assertEqual(ind['taux_reussite'], 50.0)

    def test_meme_client_meme_jour_compte_une_fois(self):
        self._planning(self.clients[0], 1)
        VisiteClient.objects.create(livreur=self.vendeur, client=self.clients[0], date_visite=LUNDI, resultat='vente')
        self._vente(self.clients[0], LUNDI, 100)
        self._commande(self.clients[0], LUNDI, 50)
        ind = self._calc()
        self.assertEqual(ind['visites'], 1)
        self.assertEqual(ind['taux_visite'], 100.0)
        self.assertEqual(ind['taux_reussite'], 100.0)

    # ---- realisation et livraison ----
    def test_taux_de_realisation_ventes_et_commandes(self):
        ObjectifVendeur.objects.create(livreur=self.vendeur, annee=2026, mois=9, type_perimetre='entrepot',
                                       entrepot=self.ent, montant_objectif=Decimal('1000'))
        self._vente(self.clients[0], LUNDI, 300)
        self._commande(self.clients[1], MARDI, 200)
        self._commande(self.clients[2], MARDI, 999, statut='cancelled')   # annulee : ignoree
        ind = self._calc()
        self.assertEqual(ind['nb_objectifs'], 1)
        self.assertEqual(ind['objectif_ca'], 1000.0)
        self.assertEqual(ind['ca_realise_objectifs'], 500.0)
        self.assertEqual(ind['taux_realisation'], 50.0)

    def test_taux_de_livraison_des_commandes(self):
        self._commande(self.clients[0], LUNDI, 300, statut='delivered')
        self._commande(self.clients[1], LUNDI, 100, statut='pending')
        self._commande(self.clients[2], MARDI, 500, statut='cancelled')
        ind = self._calc()
        self.assertEqual(ind['commandes_prises'], 2)
        self.assertEqual(ind['commandes_livrees'], 1)
        self.assertEqual(ind['taux_livraison'], 75.0)   # 300 / 400

    def test_sans_donnees_taux_indefinis(self):
        ind = self._calc()
        for cle in ('taux_visite', 'taux_reussite', 'taux_realisation', 'taux_livraison'):
            self.assertIsNone(ind[cle])

    # ---- global + API ----
    def test_global_et_api(self):
        self._planning(self.clients[0], 1); self._planning(self.clients[1], 1)
        self._vente(self.clients[0], LUNDI, 100)
        autre = LivreurDistribution.objects.create(matricule='V2', nom='Yacine', telephone='0', statut='inactif')
        data = calculer_indicateurs(DEBUT, FIN, aujourd_hui=FIN)
        self.assertEqual([v['nom'] for v in data['vendeurs']], ['Ahmed'])   # inactif sans activite : masque
        self.assertEqual(data['global']['taux_visite'], 50.0)
        self.assertEqual(data['global']['taux_reussite'], 100.0)

        api = APIClient()
        self.assertIn(api.get('/API/distribution/indicateurs-performance/').status_code, (401, 403))
        api.force_authenticate(User.objects.create_user('u', password='x'))
        r = api.get('/API/distribution/indicateurs-performance/?date_debut=2026-09-07&date_fin=2026-09-13')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(r.json()['vendeurs']), 1)
        self.assertIn('definitions', r.json())
        r = api.get(f'/API/distribution/indicateurs-performance/?date_debut=2026-09-07&date_fin=2026-09-13&livreur_id={autre.id}')
        self.assertEqual([v['nom'] for v in r.json()['vendeurs']], ['Yacine'])
        self.assertEqual(api.get('/API/distribution/indicateurs-performance/?date_debut=13/09/2026').status_code, 400)
        self.assertEqual(api.get('/API/distribution/indicateurs-performance/?date_debut=2026-09-13&date_fin=2026-09-07').status_code, 400)
