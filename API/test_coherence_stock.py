"""Cohérence du stock : stock par dépôt (ProductStock) et total produit (Produit.quantite)
doivent toujours rester alignés, quelle que soit l'opération (mouvement, transfert, achat,
inventaire, vente, bon de livraison, bon de transfert)."""
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from .models import (Achat, BonLivraison, Categorie, Client, Company, InventoryLine, InventorySession,
                     LigneLivraison, LigneTransfertStock, LigneVente, Produit, ProductStock, StockMove,
                     SystemConfig, TransfertStock, UserProfile, Vente, Warehouse)
from .stock_utils import StockInsuffisant, appliquer_mouvement, recalculer_quantite_produit


class BaseStock(TestCase):
    def setUp(self):
        self.societe = Company.objects.create(name='Société A', code='SOCA')
        self.autre = Company.objects.create(name='Société B', code='SOCB')
        cat = Categorie.objects.create(nom='Boissons')
        self.eau = Produit.objects.create(reference='EAU', code_barre='1', designation='Eau',
                                          prixU=Decimal('10'), categorie=cat)
        self.depot = Warehouse.objects.create(code='DEP1', name='Dépôt centre', company=self.societe)
        self.magasin = Warehouse.objects.create(code='MAG1', name='Magasin', company=self.societe)
        self.ferme = Warehouse.objects.create(code='OLD', name='Ancien dépôt', company=self.societe, is_active=False)
        self.etranger = Warehouse.objects.create(code='EXT', name='Dépôt société B', company=self.autre)
        ProductStock.objects.create(produit=self.eau, warehouse=self.depot, quantity=10)
        ProductStock.objects.create(produit=self.eau, warehouse=self.magasin, quantity=5)
        recalculer_quantite_produit(self.eau)
        cfg = SystemConfig.get_solo(self.societe)
        cfg.default_warehouse = self.depot
        cfg.save()
        self.user = User.objects.create_user('gerant', password='x', is_staff=True)
        UserProfile.objects.create(user=self.user, company=self.societe)
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def stock(self, entrepot, produit=None):
        ps = ProductStock.objects.filter(produit=produit or self.eau, warehouse=entrepot).first()
        return ps.quantity if ps else 0

    def total(self, produit=None):
        p = Produit.objects.get(pk=(produit or self.eau).pk)
        return p.quantite

    def assertCoherent(self, produit=None):
        p = produit or self.eau
        somme = sum(ProductStock.objects.filter(produit=p).values_list('quantity', flat=True))
        self.assertEqual(self.total(p), somme)


class HelperTests(BaseStock):
    def test_appliquer_mouvement_entree_sortie(self):
        appliquer_mouvement(self.eau, self.depot, -4, 'PERTE', note='casse')
        self.assertEqual(self.stock(self.depot), 6)
        self.assertEqual(self.total(), 11)
        self.assertEqual(StockMove.objects.count(), 1)

    def test_appliquer_mouvement_stock_insuffisant(self):
        with self.assertRaises(StockInsuffisant) as ctx:
            appliquer_mouvement(self.eau, self.magasin, -6, 'PERTE')
        self.assertIn('Stock insuffisant dans Magasin : 5 disponible(s)', ctx.exception.messages[0])
        self.assertEqual(self.stock(self.magasin), 5)
        self.assertFalse(StockMove.objects.exists())

    def test_recalcul_inclut_tous_les_depots(self):
        van = Warehouse.objects.create(code='VAN1', name='Van 1', company=self.societe, is_active=False)
        ProductStock.objects.create(produit=self.eau, warehouse=van, quantity=7)
        self.assertEqual(recalculer_quantite_produit(self.eau), 22)

    def test_commande_resync(self):
        Produit.objects.filter(pk=self.eau.pk).update(quantite=999)
        out = StringIO()
        call_command('resync_stock', '--dry-run', stdout=out)
        self.assertIn('EAU', out.getvalue())
        self.assertEqual(self.total(), 999)            # simulation : rien modifié
        call_command('resync_stock', stdout=StringIO())
        self.assertEqual(self.total(), 15)


class MouvementManuelTests(BaseStock):
    URL = '/API/stock-moves/'

    def test_sans_depot_utilise_depot_par_defaut(self):
        r = self.api.post(self.URL, {'produit': self.eau.id, 'delta': 3, 'source': 'CORR'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.stock(self.depot), 13)
        self.assertCoherent()

    def test_sans_depot_ni_defaut_refuse(self):
        SystemConfig.objects.filter(company=self.societe).update(default_warehouse=None)
        r = self.api.post(self.URL, {'produit': self.eau.id, 'delta': 3, 'source': 'CORR'}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn('Choisissez un dépôt', r.json()['detail'])
        self.assertFalse(StockMove.objects.exists())

    def test_stock_insuffisant_pas_de_mouvement_orphelin(self):
        r = self.api.post(self.URL, {'produit': self.eau.id, 'warehouse': self.magasin.id, 'delta': -50,
                                     'source': 'CORR'}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn('Stock insuffisant', r.json()['detail'])
        self.assertFalse(StockMove.objects.exists())
        self.assertEqual(self.stock(self.magasin), 5)


class TransfertTests(BaseStock):
    URL = '/API/mouvements/transfer/'

    def post(self, **data):
        base = {'produit': self.eau.id, 'quantite': 4, 'from_warehouse': self.depot.id, 'to_warehouse': self.magasin.id}
        base.update(data)
        return self.api.post(self.URL, base, format='json')

    def test_transfert_simple_avec_reference(self):
        r = self.post()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(r.json()['reference'].startswith('TRANS-'))
        self.assertEqual(self.stock(self.depot), 6)
        self.assertEqual(self.stock(self.magasin), 9)
        self.assertEqual(StockMove.objects.filter(ref_id=r.json()['reference']).count(), 2)
        self.assertCoherent()

    def test_depot_autre_societe_404(self):
        self.assertEqual(self.post(to_warehouse=self.etranger.id).status_code, 404)
        self.assertEqual(self.post(from_warehouse=self.etranger.id).status_code, 404)
        self.assertEqual(self.stock(self.depot), 10)

    def test_refus_destination_inactive_meme_depot_quantite_decimale(self):
        self.assertEqual(self.post(to_warehouse=self.ferme.id).status_code, 400)
        self.assertEqual(self.post(to_warehouse=self.depot.id).status_code, 400)
        r = self.post(quantite=2.7)
        self.assertEqual(r.status_code, 400)
        self.assertIn('entier', r.json()['detail'])
        self.assertFalse(StockMove.objects.exists())

    def test_stock_insuffisant(self):
        r = self.post(quantite=11)
        self.assertEqual(r.status_code, 400)
        self.assertIn('Stock insuffisant dans Dépôt centre', r.json()['detail'])

    def test_plusieurs_produits_tout_ou_rien(self):
        jus = Produit.objects.create(reference='JUS', code_barre='2', designation='Jus', prixU=Decimal('5'),
                                     categorie=self.eau.categorie)
        ProductStock.objects.create(produit=jus, warehouse=self.depot, quantity=3)
        r = self.api.post(self.URL, {'lignes': [{'produit': self.eau.id, 'quantite': 2}, {'produit': jus.id, 'quantite': 9}],
                                     'from_warehouse': self.depot.id, 'to_warehouse': self.magasin.id}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(self.stock(self.depot), 10)   # rien n'a bougé
        r = self.api.post(self.URL, {'lignes': [{'produit': self.eau.id, 'quantite': 2}, {'produit': jus.id, 'quantite': 3}],
                                     'from_warehouse': self.depot.id, 'to_warehouse': self.magasin.id}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(StockMove.objects.filter(ref_id=r.json()['reference']).count(), 4)
        self.assertEqual(self.stock(self.magasin, jus), 3)

    def test_perte_et_sortie_securisees(self):
        r = self.api.post('/API/mouvements/loss/', {'produit': self.eau.id, 'quantite': 1, 'type': 'CASSE',
                                                    'warehouse': self.etranger.id}, format='json')
        self.assertEqual(r.status_code, 404)
        r = self.api.post('/API/mouvements/outflow/', {'produit': self.eau.id, 'quantite': 1.5, 'type': 'DON',
                                                       'warehouse': self.depot.id}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.api.post('/API/mouvements/loss/', {'produit': self.eau.id, 'quantite': 2, 'type': 'CASSE',
                                                    'warehouse': self.depot.id}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.stock(self.depot), 8)
        self.assertCoherent()

    def test_liste_des_transferts_inclut_mouvements(self):
        r = self.post()
        ref = r.json()['reference']
        from django.test import RequestFactory
        from frontoffice.views import transferts_list
        req = RequestFactory().get('/transferts_list')
        req.user = self.user
        resp = transferts_list(req)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(ref, resp.content.decode())


class BonTransfertTests(BaseStock):
    def test_pas_de_stock_fantome(self):
        ProductStock.objects.filter(produit=self.eau, warehouse=self.depot).update(quantity=0)
        recalculer_quantite_produit(self.eau)   # total = 5 (magasin)
        t = TransfertStock.objects.create(entrepot_source=self.depot, entrepot_destination=self.magasin)
        LigneTransfertStock.objects.create(transfert=t, produit=self.eau, quantite=3)
        with self.assertRaises(ValidationError):
            t.valider(self.user)
        self.assertEqual(self.stock(self.depot), 0)
        self.assertEqual(self.total(), 5)

    def test_valider_met_a_jour_total_tous_depots(self):
        van = Warehouse.objects.create(code='VAN1', name='Van', company=self.societe)
        t = TransfertStock.objects.create(entrepot_source=self.depot, entrepot_destination=van)
        LigneTransfertStock.objects.create(transfert=t, produit=self.eau, quantite=4)
        t.valider(self.user)
        self.assertEqual(self.stock(self.depot), 6)
        self.assertEqual(self.stock(van), 4)
        self.assertEqual(self.total(), 15)   # le van compte aussi


class AchatTests(BaseStock):
    URL = '/API/achats/'

    def test_creation_modification_suppression(self):
        r = self.api.post(self.URL, {'produit': self.eau.id, 'quantite': 20, 'prix_achat': '3', 'date_Achat': '2026-11-20',
                                     'warehouse': self.magasin.id}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        aid = r.json()['id']
        self.assertEqual(self.stock(self.magasin), 25)
        r = self.api.patch(f'{self.URL}{aid}/', {'quantite': 12}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.stock(self.magasin), 17)
        r = self.api.patch(f'{self.URL}{aid}/', {'warehouse': self.depot.id}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.stock(self.magasin), 5)
        self.assertEqual(self.stock(self.depot), 22)
        r = self.api.delete(f'{self.URL}{aid}/')
        self.assertEqual(r.status_code, 204, r.content)
        self.assertEqual(self.stock(self.depot), 10)
        self.assertCoherent()

    def test_sans_depot_va_au_depot_par_defaut(self):
        r = self.api.post(self.URL, {'produit': self.eau.id, 'quantite': 2, 'prix_achat': '3'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.stock(self.depot), 12)
        self.assertEqual(Achat.objects.get().warehouse, self.depot)

    def test_suppression_refusee_si_stock_deja_sorti(self):
        r = self.api.post(self.URL, {'produit': self.eau.id, 'quantite': 3, 'prix_achat': '3', 'date_Achat': '2026-11-20',
                                     'warehouse': self.magasin.id}, format='json')
        appliquer_mouvement(self.eau, self.magasin, -8, 'PERTE')
        r = self.api.delete(f"{self.URL}{r.json()['id']}/")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertTrue(Achat.objects.exists())


class InventaireDepotTests(BaseStock):
    def test_creation_sans_date_et_validation_sur_le_depot(self):
        r = self.api.post('/API/inventaires/', {'note': 'test'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        session = InventorySession.objects.get(pk=r.json()['id'])
        self.assertEqual(session.warehouse, self.depot)
        InventoryLine.objects.create(session=session, produit=self.eau, snapshot_qty=15, counted_qty=8)
        r = self.api.post(f'/API/inventaires/{session.id}/validate/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.stock(self.depot), 8)
        self.assertEqual(self.stock(self.magasin), 5)    # l'autre dépôt n'est pas touché
        self.assertEqual(self.total(), 13)
        self.assertCoherent()

    def test_depot_choisi(self):
        r = self.api.post('/API/inventaires/', {'warehouse': self.magasin.id}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        r = self.api.post('/API/inventaires/', {'warehouse': self.etranger.id}, format='json')
        self.assertEqual(r.status_code, 400, r.content)


class VenteEtBLTests(BaseStock):
    def setUp(self):
        super().setUp()
        self.client_ = Client.objects.create(nom='Client', prenom='A', telephone='0')

    def test_vente_controle_le_stock_du_depot(self):
        v = Vente.objects.create(client=self.client_, statut='draft', warehouse=self.magasin, company=self.societe)
        LigneVente.objects.create(vente=v, produit=self.eau, quantite=6, prixU_snapshot=Decimal('10'))
        r = self.api.post(f'/API/ventes/{v.id}/complete/')
        self.assertEqual(r.status_code, 400, r.content)   # total 15 mais magasin = 5
        self.assertIn('Stock insuffisant dans Magasin', r.json()['detail'])
        v.refresh_from_db()
        self.assertEqual(v.statut, 'draft')
        LigneVente.objects.filter(vente=v).update(quantite=5)
        r = self.api.post(f'/API/ventes/{v.id}/complete/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.stock(self.magasin), 0)
        self.assertEqual(self.total(), 10)
        self.assertCoherent()

    def test_bl_sort_du_depot_par_defaut(self):
        bon = BonLivraison.objects.create(numero='BL1', client=self.client_, company=self.societe)
        LigneLivraison.objects.create(bon=bon, produit=self.eau, quantite=12, prixU_snapshot=Decimal('10'))
        r = self.api.post(f'/API/bons/{bon.id}/valider/')
        self.assertEqual(r.status_code, 400, r.content)   # dépôt par défaut = 10
        LigneLivraison.objects.filter(bon=bon).update(quantite=4)
        r = self.api.post(f'/API/bons/{bon.id}/valider/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.stock(self.depot), 6)
        self.assertCoherent()
