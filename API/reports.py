"""
Module de génération de rapports Excel et PDF
"""
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
                                KeepTogether)
from reportlab.pdfgen import canvas

from django.db.models import Sum, Count, F, Q
from django.utils import timezone

from .models import Produit, Vente, LigneVente, Achat, StockMove, ProductStock, Warehouse


# Périmètre « toutes les entreprises » : réservé au staff / superuser, comme dans
# TenantFilterMixin (API/mixins.py). Valeur par défaut des générateurs.
TOUTES_ENTREPRISES = object()


def perimetre_rapport(request):
    """Entreprise à laquelle limiter un rapport, selon les mêmes règles que l'API :
    staff / superuser -> toutes ; sinon l'entreprise de l'utilisateur (None s'il n'en a pas)."""
    user = request.user
    if user.is_superuser or user.is_staff:
        return TOUTES_ENTREPRISES
    return getattr(request, 'company', None)


def _filtrer_entreprise(qs, company, champ='company'):
    """Limite `qs` à l'entreprise (+ données partagées sans entreprise)."""
    if company is TOUTES_ENTREPRISES:
        return qs
    if company is None:
        return qs.filter(**{f'{champ}__isnull': True})
    return qs.filter(Q(**{champ: company}) | Q(**{f'{champ}__isnull': True}))


ORIGINES = {'pc': 'PC', 'telephone': 'Téléphone', 'commande': 'Commande livrée'}
_PAIEMENTS = {'especes': 'Espèces', 'espece': 'Espèces', 'cheque': 'Chèque', 'credit': 'À crédit',
              'carte': 'Carte', 'virement': 'Virement'}


def _periode(qs, champ, start_date, end_date):
    """Filtre sur la DATE (jour entier inclus). Avant : `date_vente__lte=fin` excluait toutes les
    ventes du dernier jour après minuit."""
    if start_date:
        qs = qs.filter(**{f'{champ}__date__gte': start_date})
    if end_date:
        qs = qs.filter(**{f'{champ}__date__lte': end_date})
    return qs


def _perimetre_ventes(qs, company):
    """`company` : TOUTES_ENTREPRISES, None (comptes sans entreprise) ou une entreprise."""
    return _filtrer_entreprise(qs, company)


def ventes_toutes_origines(start_date=None, end_date=None, company=TOUTES_ENTREPRISES):
    """Toutes les ventes de la période, quelle que soit leur origine : ventes du PC (validées),
    ventes faites sur le téléphone, commandes livrées. Avant : seules les ventes du PC.
    Chaque élément : origine, numero, date, client, paiement, ht, ttc, remise (du plus récent au plus ancien)."""
    from .distribution_models import VenteTourneeMobile, CommandeClient
    z = Decimal('0.00')
    docs = []

    pc = _periode(_perimetre_ventes(Vente.objects.filter(statut='completed'), company), 'date_vente',
                  start_date, end_date).select_related('client')
    for v in pc:
        docs.append({'origine': 'pc', 'numero': v.numero, 'date': v.date_vente, 'client': v.client,
                     'paiement': v.get_type_paiement_display(), 'ht': v.total_ht or z,
                     'ttc': v.total_ttc or z, 'remise': v.remise_percent or z})

    tel = _periode(_perimetre_ventes(VenteTourneeMobile.objects.all(), company), 'date_vente',
                   start_date, end_date).select_related('client')
    for v in tel:
        docs.append({'origine': 'telephone', 'numero': v.numero_vente, 'date': v.date_vente, 'client': v.client,
                     'paiement': _PAIEMENTS.get(v.type_paiement, v.type_paiement or ''),
                     'ht': v.montant_ht or v.montant_total or z, 'ttc': v.montant_total or z, 'remise': z})

    cmd = _periode(_perimetre_ventes(CommandeClient.objects.filter(statut='delivered'), company),
                   'date_livraison_reelle', start_date, end_date).select_related('client')
    for c in cmd:
        docs.append({'origine': 'commande', 'numero': c.reference, 'date': c.date_livraison_reelle,
                     'client': c.client, 'paiement': _PAIEMENTS.get(c.type_paiement, c.type_paiement or ''),
                     'ht': c.montant_total_ht or z, 'ttc': c.montant_total_ttc or z, 'remise': z})

    docs.sort(key=lambda d: d['date'] or timezone.now(), reverse=True)
    return docs


def quantites_vendues(company=None, start_date=None, end_date=None):
    """Quantités vendues et chiffre d'affaires HT par produit, toutes origines confondues.
    `company` : None = toutes les entreprises (même convention que _get_profit_data).
    Renvoie ({produit_id: {'qte', 'ca'}}, {origine: ca})."""
    from collections import defaultdict
    from .distribution_models import LigneVenteTourneeMobile, LigneCommandeClient
    perim = TOUTES_ENTREPRISES if company is None else company
    par_produit = defaultdict(lambda: {'qte': Decimal('0'), 'ca': Decimal('0')})
    par_origine = {'pc': Decimal('0'), 'telephone': Decimal('0'), 'commande': Decimal('0')}

    def ajouter(origine, pid, qte, ca):
        qte, ca = Decimal(str(qte or 0)), Decimal(str(ca or 0))
        par_produit[pid]['qte'] += qte
        par_produit[pid]['ca'] += ca
        par_origine[origine] += ca

    lignes_pc = LigneVente.objects.filter(
        vente__in=_periode(_filtrer_entreprise(Vente.objects.filter(statut='completed'), perim, 'company'),
                           'date_vente', start_date, end_date))
    for pid, q, prix in lignes_pc.values_list('produit_id', 'quantite', 'prixU_snapshot'):
        ajouter('pc', pid, q, Decimal(str(q or 0)) * Decimal(str(prix or 0)))

    from .distribution_models import VenteTourneeMobile, CommandeClient
    lignes_tel = LigneVenteTourneeMobile.objects.filter(
        vente__in=_periode(_filtrer_entreprise(VenteTourneeMobile.objects.all(), perim), 'date_vente',
                           start_date, end_date))
    for pid, q, ht in lignes_tel.values_list('produit_id', 'quantite', 'montant_ht'):
        ajouter('telephone', pid, q, ht)

    lignes_cmd = LigneCommandeClient.objects.filter(
        commande__in=_periode(_filtrer_entreprise(CommandeClient.objects.filter(statut='delivered'), perim),
                              'date_livraison_reelle', start_date, end_date))
    for pid, q, ht in lignes_cmd.values_list('produit_id', 'quantite', 'montant_ht'):
        ajouter('commande', pid, q, ht)

    return par_produit, par_origine


class ExcelReportGenerator:
    """Générateur de rapports Excel avec styles professionnels"""

    def __init__(self):
        self.wb = Workbook()
        self.ws = self.wb.active

        # Styles
        self.header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        self.header_font = Font(bold=True, color="FFFFFF", size=12)
        self.title_font = Font(bold=True, size=14)
        self.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

    def set_column_widths(self, widths):
        """Définir les largeurs de colonnes"""
        for idx, width in enumerate(widths, start=1):
            self.ws.column_dimensions[get_column_letter(idx)].width = width

    def add_title(self, title, row=1):
        """Ajouter un titre au rapport"""
        self.ws.merge_cells(f'A{row}:F{row}')
        cell = self.ws[f'A{row}']
        cell.value = title
        cell.font = self.title_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        return row + 1

    def add_metadata(self, row, company_name="GestionStock", date=None):
        """Ajouter métadonnées du rapport"""
        if date is None:
            date = timezone.now().strftime('%d/%m/%Y %H:%M')

        self.ws[f'A{row}'] = "Date:"
        self.ws[f'B{row}'] = date
        self.ws[f'A{row+1}'] = "Société:"
        self.ws[f'B{row+1}'] = company_name
        return row + 3

    def add_header_row(self, headers, row):
        """Ajouter une ligne d'en-tête"""
        for col_idx, header in enumerate(headers, start=1):
            cell = self.ws.cell(row=row, column=col_idx)
            cell.value = header
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = self.border
        return row + 1

    def add_data_rows(self, data, start_row, number_columns=None):
        """Ajouter des lignes de données"""
        if number_columns is None:
            number_columns = []

        for row_idx, row_data in enumerate(data, start=start_row):
            for col_idx, value in enumerate(row_data, start=1):
                cell = self.ws.cell(row=row_idx, column=col_idx)
                cell.value = value
                cell.border = self.border
                cell.alignment = Alignment(horizontal='right' if col_idx in number_columns else 'left')

                # Format numbers
                if col_idx in number_columns and isinstance(value, (int, float, Decimal)):
                    if isinstance(value, Decimal) or isinstance(value, float):
                        cell.number_format = '#,##0.00'
                    else:
                        cell.number_format = '#,##0'

        return start_row + len(data)

    def add_total_row(self, row, label_col, label, value_cols_values):
        """Ajouter une ligne de total"""
        cell = self.ws.cell(row=row, column=label_col)
        cell.value = label
        cell.font = Font(bold=True)
        cell.border = self.border
        cell.alignment = Alignment(horizontal='right')

        for col_idx, value in value_cols_values.items():
            cell = self.ws.cell(row=row, column=col_idx)
            cell.value = value
            cell.font = Font(bold=True)
            cell.border = self.border
            cell.alignment = Alignment(horizontal='right')
            if isinstance(value, (int, float, Decimal)):
                if isinstance(value, Decimal) or isinstance(value, float):
                    cell.number_format = '#,##0.00'
                else:
                    cell.number_format = '#,##0'

        return row + 1

    def save_to_buffer(self):
        """Sauvegarder dans un buffer BytesIO"""
        buffer = BytesIO()
        self.wb.save(buffer)
        buffer.seek(0)
        return buffer


class PDFReportGenerator:
    """Générateur de rapports PDF avec styles professionnels"""

    def __init__(self, title, orientation='portrait'):
        self.buffer = BytesIO()
        pagesize = landscape(A4) if orientation == 'landscape' else A4
        self.doc = SimpleDocTemplate(self.buffer, pagesize=pagesize,
                                     rightMargin=30, leftMargin=30,
                                     topMargin=30, bottomMargin=30)
        self.elements = []
        self.styles = getSampleStyleSheet()
        self.title = title

        # Styles personnalisés
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#366092'),
            spaceAfter=30,
            alignment=1  # Center
        )

    def add_title(self, title=None):
        """Ajouter un titre"""
        if title is None:
            title = self.title
        self.elements.append(Paragraph(title, self.title_style))
        self.elements.append(Spacer(1, 12))

    def add_metadata(self, company_name="GestionStock", date=None):
        """Ajouter métadonnées"""
        if date is None:
            date = timezone.now().strftime('%d/%m/%Y %H:%M')

        metadata_style = ParagraphStyle(
            'Metadata',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.grey
        )

        self.elements.append(Paragraph(f"<b>Date:</b> {date}", metadata_style))
        self.elements.append(Paragraph(f"<b>Société:</b> {company_name}", metadata_style))
        self.elements.append(Spacer(1, 20))

    def add_table(self, data, col_widths=None):
        """Ajouter un tableau"""
        table = Table(data, colWidths=col_widths)

        # Style du tableau
        table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Corps du tableau
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

            # Grille
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),

            # Alternance de couleurs
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))

        self.elements.append(table)
        self.elements.append(Spacer(1, 20))

    def add_summary_box(self, summary_data):
        """Ajouter un encadré de résumé"""
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F4F8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))

        self.elements.append(summary_table)
        self.elements.append(Spacer(1, 20))

    def build(self):
        """Construire le document PDF"""
        self.doc.build(self.elements)
        self.buffer.seek(0)
        return self.buffer


# ======================
# ÉTAT DU STOCK (valorisation + inventaire) : outils communs PDF / Excel
# ======================
#
# Règles communes aux deux rapports :
# - la quantité affichée vient TOUJOURS de ProductStock (somme des dépôts retenus) et le statut
#   est calculé à partir de CETTE quantité (avant : quantité ProductStock mais statut calculé
#   sur Produit.quantite -> « 258 … out_of_stock ») ;
# - « Tous les entrepôts » = dépôts ACTIFS uniquement ; les vans sont identifiés comme tels et
#   une répartition par dépôt est toujours jointe ; `par_depot=True` détaille produit par dépôt ;
# - valorisation au prix de vente (fiche produit) par défaut ; `prix='achat'` = prix d'achat
#   moyen pondéré des achats enregistrés (réservé : contrôlé par la vue).

PRIX_VENTE = 'vente'
PRIX_ACHAT = 'achat'

# code -> (libellé, couleur du texte, fond Excel)
STATUTS_STOCK = {
    'rupture': ('Rupture', '#C0392B', 'FADBD8'),
    'critique': ('Critique', '#D35400', 'FDEBD0'),
    'alerte': ('Alerte', '#9A7D0A', 'FCF3CF'),
    'normal': ('Normal', '#1E8449', 'D5F5E3'),
}
_NBSP = ' '


def statut_stock(qty, seuil_alerte, seuil_critique):
    """Statut (rupture / critique / alerte / normal) d'une quantité, mêmes règles que Produit."""
    qty = qty or 0
    if qty <= 0:
        return 'rupture'
    if qty <= (seuil_critique or 0):
        return 'critique'
    if qty <= (seuil_alerte or 0):
        return 'alerte'
    return 'normal'


def fmt_nombre(valeur, decimales=0):
    """1234567.5 -> '1 234 567,50' (format français, espaces insécables)."""
    texte = f"{float(valeur or 0):,.{decimales}f}"
    return texte.replace(',', _NBSP).replace('.', ',')


def fmt_da(valeur):
    return f"{fmt_nombre(valeur, 2)}{_NBSP}DA"


def nom_societe(company):
    """Nom à imprimer sur les rapports : nom du ticket (Paramètres) sinon nom de l'entreprise.
    Sans entreprise précise : l'entreprise unique s'il n'y en a qu'une."""
    from .models import Company, SystemConfig
    if company is TOUTES_ENTREPRISES or company is None:
        ids = list(Company.objects.values_list('pk', flat=True)[:2])
        company = Company.objects.filter(pk=ids[0]).first() if len(ids) == 1 else None
    cfg = SystemConfig.objects.filter(company=company).first()
    nom = (getattr(cfg, 'ticket_company_name', '') or '').strip()
    if nom:
        return nom
    return company.name if company is not None else ''


def nom_societe_rapport(request):
    """Nom de la société de l'utilisateur qui demande le rapport."""
    from .models import SystemConfig
    company = getattr(request, 'company', None) or SystemConfig.company_of_user(getattr(request, 'user', None))
    return nom_societe(company)


def parametres_etat_stock(request):
    """Paramètres GET des états du stock : (warehouse_id, par_depot, prix).
    `prix=achat` est réservé aux administrateurs qui ont déverrouillé le tableau des bénéfices
    (le coût d'achat révèle les marges) : lève AccesRefuse sinon. Warehouse.DoesNotExist si
    l'identifiant de dépôt est invalide."""
    wid = (request.GET.get('warehouse') or '').strip() or None
    if wid is not None and not wid.isdigit():
        raise Warehouse.DoesNotExist(wid)
    par_depot = (request.GET.get('par_depot') or '').lower() in ('1', 'true', 'oui', 'on')
    prix = PRIX_ACHAT if request.GET.get('prix') == PRIX_ACHAT else PRIX_VENTE
    if prix == PRIX_ACHAT:
        from .benefices_acces import verifier_acces
        verifier_acces(request)
    return wid, par_depot, prix


def _ids_vans(depots):
    """Dépôts qui sont des vans : code contenant « van », même convention que le reste de
    l'application (stock van des livreurs, chargement, ensure_default_warehouse)."""
    return {d.pk for d in depots if 'van' in (d.code or '').lower()}


def _depots_rapport(company, warehouse_id):
    """(dépôts retenus, ids des vans, libellé du filtre). Un dépôt précis s'il est demandé
    (Warehouse.DoesNotExist s'il n'est pas visible), sinon tous les dépôts ACTIFS."""
    qs = _filtrer_entreprise(Warehouse.objects.all(), company)
    if warehouse_id:
        depots = [qs.get(pk=warehouse_id)]
    else:
        depots = list(qs.filter(is_active=True).order_by('name'))
    vans = _ids_vans(depots)
    if warehouse_id:
        d = depots[0]
        libelle = f"{'Van' if d.pk in vans else 'Dépôt'} : {d.name}" + ('' if d.is_active else ' (inactif)')
    else:
        nb_vans = sum(1 for d in depots if d.pk in vans)
        libelle = f"Tous les dépôts actifs ({len(depots) - nb_vans} dépôt(s), {nb_vans} van(s))"
    return depots, vans, libelle


def _prix_achat_moyens(produit_ids, company):
    """Prix d'achat moyen pondéré par les quantités, par pièce, à partir des achats enregistrés."""
    from collections import defaultdict
    cumul = defaultdict(lambda: [Decimal('0'), Decimal('0')])
    achats = _filtrer_entreprise(Achat.objects.filter(produit_id__in=produit_ids), company)
    for a in achats:
        prix = Decimal(str(a.get_prix_unitaire_piece() or 0))
        qte = Decimal(str(a.quantite or 0))
        if prix > 0 and qte > 0:
            cumul[a.produit_id][0] += prix * qte
            cumul[a.produit_id][1] += qte
    return {pid: (t / q).quantize(Decimal('0.01')) for pid, (t, q) in cumul.items() if q}


def _prix_unitaires(produits, prix, company):
    if prix == PRIX_ACHAT:
        return _prix_achat_moyens([p.pk for p in produits], company)
    return {p.pk: (p.prixU or Decimal('0.00')) for p in produits}


def _libelle_prix(prix):
    if prix == PRIX_ACHAT:
        return "Prix d'achat moyen pondéré (achats enregistrés)"
    return "Prix de vente (prix unitaire de la fiche produit)"


def _ligne_produit(p, qty, pu):
    pu = Decimal(pu or 0)
    return {
        'reference': p.reference or '',
        'code_barre': p.code_barre or '',
        'designation': p.designation or '',
        'categorie': p.categorie.nom if p.categorie_id else '',
        'fournisseur': p.fournisseur.libelle if p.fournisseur_id else '',
        'qty': int(qty or 0),
        'seuil': p.seuil_alerte or 0,
        'pu': pu,
        'valeur': (pu * int(qty or 0)).quantize(Decimal('0.01')),
        'statut': statut_stock(qty, p.seuil_alerte, p.seuil_critique),
    }


def donnees_etat_stock(company=TOUTES_ENTREPRISES, warehouse_id=None, par_depot=False,
                       prix=PRIX_VENTE, inclure_zero=False):
    """Données d'un état du stock.

    inclure_zero=False (valorisation) : produits en stock seulement ;
    inclure_zero=True (inventaire) : tous les produits actifs, même à 0.
    Retourne un dict : groupes [(dépôt|None, lignes)], lignes (à plat, avec 'depot'/'type_depot'),
    repartition (par dépôt), totaux, libellé du filtre, libellé du prix, nb produits sans prix."""
    from collections import defaultdict
    depots, vans, libelle_filtre = _depots_rapport(company, warehouse_id)

    stocks = ProductStock.objects.filter(warehouse__in=depots, produit__is_active=True)
    qty_pd = defaultdict(int)          # (produit, dépôt) -> qté
    for pid, wid, q in stocks.values_list('produit_id', 'warehouse_id', 'quantity'):
        qty_pd[(pid, wid)] += q or 0

    if inclure_zero:
        produits_qs = _filtrer_entreprise(Produit.objects.filter(is_active=True), company)
    else:
        produits_qs = Produit.objects.filter(pk__in={pid for (pid, _), q in qty_pd.items() if q > 0})
    produits = list(produits_qs.select_related('categorie', 'fournisseur').order_by('reference', 'designation'))
    pu = _prix_unitaires(produits, prix, company)
    sans_prix = sum(1 for p in produits if not pu.get(p.pk))

    def infos_depot(d):
        return {'nom': d.name, 'code': d.code, 'van': d.pk in vans, 'actif': d.is_active,
                'type': 'Van' if d.pk in vans else 'Dépôt'}

    groupes, lignes, repartition = [], [], []
    for d in depots:
        info = infos_depot(d)
        lignes_d = []
        for p in produits:
            q = qty_pd.get((p.pk, d.pk), 0)
            if q > 0:
                lignes_d.append(_ligne_produit(p, q, pu.get(p.pk)))
        repartition.append(dict(info, nb_produits=len(lignes_d), qty=sum(l['qty'] for l in lignes_d),
                                valeur=sum((l['valeur'] for l in lignes_d), Decimal('0.00'))))
        if par_depot and lignes_d:
            groupes.append((info, lignes_d))
            lignes.extend(dict(l, depot=info['nom'], type_depot=info['type']) for l in lignes_d)

    if not par_depot:
        ids = [d.pk for d in depots]
        lignes_g = []
        for p in produits:
            q = sum(qty_pd.get((p.pk, wid), 0) for wid in ids)
            if q > 0 or inclure_zero:
                lignes_g.append(_ligne_produit(p, q, pu.get(p.pk)))
        groupes = [(None, lignes_g)]
        lignes = lignes_g

    total_qty = sum(l['qty'] for l in lignes)
    total_valeur = sum((l['valeur'] for l in lignes), Decimal('0.00'))
    nb_statuts = {k: 0 for k in STATUTS_STOCK}
    for l in lignes:
        nb_statuts[l['statut']] += 1
    return {
        'groupes': groupes, 'lignes': lignes, 'repartition': repartition,
        'total_qty': total_qty, 'total_valeur': total_valeur,
        'nb_produits': len({l['reference'] for l in lignes}) if par_depot else len(lignes),
        'nb_statuts': nb_statuts, 'filtre': libelle_filtre, 'prix': _libelle_prix(prix),
        'sans_prix': sans_prix, 'par_depot': par_depot, 'multi_depots': len(depots) > 1,
    }


# ---------- PDF ----------

class _CanvasNumerote(canvas.Canvas):
    """Canvas qui imprime « Page X / Y » et la date de génération en pied de chaque page."""

    pied_gauche = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages)
        for etat in self._pages:
            self.__dict__.update(etat)
            self._pied(total)
            super().showPage()
        super().save()

    def _pied(self, total):
        largeur, _ = self._pagesize
        self.saveState()
        self.setStrokeColor(colors.HexColor('#B0B7C3'))
        self.setLineWidth(0.5)
        self.line(28, 22, largeur - 28, 22)
        self.setFont('Helvetica', 7.5)
        self.setFillColor(colors.HexColor('#5D6D7E'))
        self.drawString(28, 12, self.pied_gauche)
        self.drawRightString(largeur - 28, 12, f"Page {self._pageNumber} / {total}")
        self.restoreState()


def _canvas_avec_pied(texte):
    return type('CanvasPied', (_CanvasNumerote,), {'pied_gauche': texte})


_BLEU = colors.HexColor('#1F4E79')
_BLEU_CLAIR = colors.HexColor('#DCE6F1')
_GRIS_LIGNE = colors.HexColor('#F4F6F8')


def _styles_pdf():
    base = getSampleStyleSheet()['Normal']
    mk = lambda nom, **kw: ParagraphStyle(nom, parent=base, **kw)
    return {
        'titre': mk('t', fontName='Helvetica-Bold', fontSize=15, leading=18, textColor=_BLEU),
        'societe': mk('s', fontName='Helvetica-Bold', fontSize=11, leading=13, textColor=colors.HexColor('#2C3E50')),
        'meta': mk('m', fontSize=8.5, leading=11, textColor=colors.HexColor('#34495E')),
        'meta_d': mk('md', fontSize=8.5, leading=11, textColor=colors.HexColor('#34495E'), alignment=2),
        'th': mk('th', fontName='Helvetica-Bold', fontSize=8, leading=9.5, textColor=colors.white),
        'th_c': mk('thc', fontName='Helvetica-Bold', fontSize=8, leading=9.5, textColor=colors.white, alignment=1),
        'th_d': mk('thd', fontName='Helvetica-Bold', fontSize=8, leading=9.5, textColor=colors.white, alignment=2),
        'td': mk('td', fontSize=7.8, leading=9.2),
        'td_d': mk('tdd', fontSize=7.8, leading=9.2, alignment=2),
        'td_c': mk('tdc', fontName='Helvetica-Bold', fontSize=7.5, leading=9.2, alignment=1),
        'grp': mk('g', fontName='Helvetica-Bold', fontSize=8.5, leading=10.5, textColor=_BLEU),
        'tot': mk('tt', fontName='Helvetica-Bold', fontSize=8.2, leading=10),
        'tot_d': mk('ttd', fontName='Helvetica-Bold', fontSize=8.2, leading=10, alignment=2),
        'h2': mk('h2', fontName='Helvetica-Bold', fontSize=10.5, leading=13, textColor=_BLEU, spaceBefore=4),
        'note': mk('n', fontSize=7.5, leading=9.5, textColor=colors.HexColor('#5D6D7E')),
    }


def _esc(texte):
    return (str(texte).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def _cellule_pdf(col, ligne, st):
    cle, typ = col[1], col[3]
    v = ligne.get(cle)
    if typ == 'int':
        return Paragraph(fmt_nombre(v), st['td_d'])
    if typ == 'da':
        return Paragraph(fmt_da(v), st['td_d'])
    if typ == 'statut':
        lib, coul, _ = STATUTS_STOCK[v]
        return Paragraph(f'<font color="{coul}">{lib}</font>', st['td_c'])
    return Paragraph(_esc(v or ''), st['td'])


def _ligne_total_pdf(colonnes, libelle, valeurs, st):
    """Ligne de total : libellé dans la 1re colonne (fusionnée jusqu'à la 1re colonne chiffrée)."""
    cellules = []
    for i, col in enumerate(colonnes):
        if i == 0:
            cellules.append(Paragraph(_esc(libelle), st['tot']))
        elif col[1] in valeurs:
            v = valeurs[col[1]]
            cellules.append(Paragraph(fmt_da(v) if col[3] == 'da' else fmt_nombre(v), st['tot_d']))
        else:
            cellules.append('')
    premiere = next(i for i, c in enumerate(colonnes) if c[1] in valeurs)
    return cellules, max(premiere - 1, 0)


def _pdf_etat_stock(titre, societe, donnees, colonnes, sommes, resume):
    """colonnes : [(entête, clé, poids de largeur, type text|int|da|statut)] ;
    sommes : clés totalisées ; resume : [(libellé, valeur texte)] encadré final."""
    buffer = BytesIO()
    page = landscape(A4)
    marge = 28
    doc = SimpleDocTemplate(buffer, pagesize=page, leftMargin=marge, rightMargin=marge,
                            topMargin=24, bottomMargin=34, title=titre, author=societe or 'GestionStock')
    st = _styles_pdf()
    largeur = page[0] - 2 * marge
    poids = sum(c[2] for c in colonnes)
    largeurs = [largeur * c[2] / poids for c in colonnes]
    maintenant = timezone.localtime(timezone.now())

    el = []
    # En-tête : titre + société à gauche, date / filtre à droite
    gauche = [Paragraph(_esc(titre), st['titre'])]
    if societe:
        gauche.append(Paragraph(_esc(societe), st['societe']))
    droite = [Paragraph(f"<b>Date du rapport :</b> {maintenant:%d/%m/%Y à %H:%M}", st['meta_d']),
              Paragraph(f"<b>Périmètre :</b> {_esc(donnees['filtre'])}", st['meta_d']),
              Paragraph(f"<b>Valorisation :</b> {_esc(donnees['prix'])}", st['meta_d'])]
    entete = Table([[gauche, droite]], colWidths=[largeur * 0.5, largeur * 0.5])
    entete.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                                ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                ('LINEBELOW', (0, 0), (-1, 0), 1.2, _BLEU),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
    el += [entete, Spacer(1, 8)]

    # Tableau principal
    data = [[Paragraph(_esc(c[0]), st['th_d'] if c[3] in ('int', 'da') else
                       st['th_c'] if c[3] == 'statut' else st['th']) for c in colonnes]]
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), _BLEU),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#D5D8DC')),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#85929E')),
    ]
    n_ligne = 0
    for info, lignes in donnees['groupes']:
        if info is not None:
            r = len(data)
            lib = (f"Van : {info['nom']}  (stock embarqué du véhicule)" if info['van']
                   else f"Dépôt : {info['nom']}") + ('' if info['actif'] else ' (inactif)')
            data.append([Paragraph(_esc(lib), st['grp'])] + [''] * (len(colonnes) - 1))
            style += [('SPAN', (0, r), (-1, r)), ('BACKGROUND', (0, r), (-1, r), _BLEU_CLAIR),
                      ('LINEABOVE', (0, r), (-1, r), 0.8, _BLEU)]
            n_ligne = 0
        for ligne in lignes:
            r = len(data)
            data.append([_cellule_pdf(c, ligne, st) for c in colonnes])
            if n_ligne % 2:
                style.append(('BACKGROUND', (0, r), (-1, r), _GRIS_LIGNE))
            n_ligne += 1
        if info is not None:
            r = len(data)
            cellules, fin = _ligne_total_pdf(colonnes, f"Sous-total {info['nom']}",
                                             {k: sum((l[k] for l in lignes), 0) for k in sommes}, st)
            data.append(cellules)
            style += [('SPAN', (0, r), (fin, r)), ('BACKGROUND', (0, r), (-1, r), colors.HexColor('#EEF3F9'))]
    if len(data) == 1:
        r = len(data)
        data.append([Paragraph('Aucun produit en stock pour ce périmètre.', st['td'])] + [''] * (len(colonnes) - 1))
        style.append(('SPAN', (0, r), (-1, r)))
    r = len(data)
    cellules, fin = _ligne_total_pdf(colonnes, 'TOTAL GÉNÉRAL',
                                     {k: donnees['total_qty'] if k == 'qty' else donnees['total_valeur']
                                      for k in sommes}, st)
    data.append(cellules)
    style += [('SPAN', (0, r), (fin, r)), ('BACKGROUND', (0, r), (-1, r), _BLEU_CLAIR),
              ('LINEABOVE', (0, r), (-1, r), 1.2, _BLEU),
              ('TOPPADDING', (0, r), (-1, r), 4), ('BOTTOMPADDING', (0, r), (-1, r), 4)]
    table = Table(data, colWidths=largeurs, repeatRows=1)
    table.setStyle(TableStyle(style))
    el += [table, Spacer(1, 10)]

    # Répartition par dépôt (dépôts et vans distingués)
    if donnees['multi_depots'] and not donnees['par_depot']:
        rep = [r for r in donnees['repartition'] if r['nb_produits']]
        if rep:
            titre_rep = Paragraph('Répartition par dépôt (dépôts actifs, vans signalés)', st['h2'])
            lignes_r = [[Paragraph(h, st['th_d'] if i >= 2 else st['th'])
                         for i, h in enumerate(['Dépôt', 'Type', 'Produits', 'Quantité', 'Valeur'])]]
            for r in rep:
                lignes_r.append([Paragraph(_esc(r['nom']), st['td']), Paragraph(r['type'], st['td']),
                                 Paragraph(fmt_nombre(r['nb_produits']), st['td_d']),
                                 Paragraph(fmt_nombre(r['qty']), st['td_d']),
                                 Paragraph(fmt_da(r['valeur']), st['td_d'])])
            lignes_r.append([Paragraph('TOTAL', st['tot']), '', '',
                             Paragraph(fmt_nombre(sum(r['qty'] for r in rep)), st['tot_d']),
                             Paragraph(fmt_da(sum((r['valeur'] for r in rep), Decimal('0'))), st['tot_d'])])
            t = Table(lignes_r, colWidths=[200, 60, 60, 80, 120], repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), _BLEU), ('BACKGROUND', (0, -1), (-1, -1), _BLEU_CLAIR),
                ('LINEABOVE', (0, -1), (-1, -1), 1, _BLEU), ('SPAN', (0, -1), (2, -1)),
                ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#D5D8DC')),
                ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#85929E')),
                ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ]))
            el += [KeepTogether([titre_rep, Spacer(1, 3), t]), Spacer(1, 10)]

    # Synthèse
    if resume:
        t = Table([[Paragraph(_esc(k), st['tot']), Paragraph(v, st['tot_d'])] for k, v in resume],
                  colWidths=[200, 130], hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F2F7FC')),
                               ('BOX', (0, 0), (-1, -1), 0.8, _BLEU),
                               ('LINEBELOW', (0, 0), (-1, -2), 0.25, colors.HexColor('#C9D6E3')),
                               ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
        el.append(t)
    if donnees['sans_prix']:
        el += [Spacer(1, 6), Paragraph(f"{donnees['sans_prix']} produit(s) sans prix connu sont valorisés à 0 DA.",
                                       st['note'])]

    pied = f"Généré le {maintenant:%d/%m/%Y à %H:%M}" + (f" — {societe}" if societe else '') + f" — {titre.capitalize()}"
    doc.build(el, canvasmaker=_canvas_avec_pied(pied))
    buffer.seek(0)
    return buffer


# ---------- Excel ----------

_XL_FMT = {'int': '#,##0', 'da': '#,##0.00 "DA"'}


def _xlsx_etat_stock(titre, societe, donnees, colonnes, sommes, nom_feuille):
    """colonnes : [(entête, clé, largeur Excel, type text|int|da|statut)]."""
    from openpyxl.worksheet.properties import PageSetupProperties
    wb = Workbook()
    ws = wb.active
    ws.title = nom_feuille
    n = len(colonnes)
    der = get_column_letter(n)
    fin = Side(style='thin', color='BFC9D4')
    bord = Border(left=fin, right=fin, top=fin, bottom=fin)
    entete_fill = PatternFill('solid', start_color='1F4E79', end_color='1F4E79')
    total_fill = PatternFill('solid', start_color='DCE6F1', end_color='DCE6F1')
    maintenant = timezone.localtime(timezone.now()).replace(tzinfo=None, microsecond=0)

    ws.merge_cells(f'A1:{der}1')
    ws['A1'] = titre
    ws['A1'].font = Font(bold=True, size=15, color='1F4E79')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 24
    meta = [('Société', societe or '—'), ('Date du rapport', maintenant),
            ('Périmètre', donnees['filtre']), ('Valorisation', donnees['prix'])]
    for i, (k, v) in enumerate(meta, start=2):
        ws.cell(row=i, column=1, value=f'{k} :').font = Font(bold=True, color='34495E')
        c = ws.cell(row=i, column=2, value=v)
        if isinstance(v, datetime):
            c.number_format = 'dd/mm/yyyy hh:mm'
            c.alignment = Alignment(horizontal='left')
        ws.merge_cells(start_row=i, start_column=2, end_row=i, end_column=n)
    h = len(meta) + 3          # ligne d'en-tête (une ligne vide avant)

    for j, col in enumerate(colonnes, start=1):
        c = ws.cell(row=h, column=j, value=col[0])
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = entete_fill
        c.border = bord
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.column_dimensions[get_column_letter(j)].width = col[2]
    ws.row_dimensions[h].height = 30

    r = h
    for ligne in donnees['lignes']:
        r += 1
        for j, col in enumerate(colonnes, start=1):
            cle, typ = col[1], col[3]
            v = ligne.get(cle)
            c = ws.cell(row=r, column=j)
            c.border = bord
            if typ == 'statut':
                lib, coul, fond = STATUTS_STOCK[v]
                c.value = lib
                c.font = Font(bold=True, color=coul.lstrip('#'))
                c.fill = PatternFill('solid', start_color=fond, end_color=fond)
                c.alignment = Alignment(horizontal='center')
            elif typ in _XL_FMT:
                c.value = float(v) if typ == 'da' else int(v or 0)
                c.number_format = _XL_FMT[typ]
            else:
                c.value = v or ''
                c.alignment = Alignment(vertical='top', wrap_text=False)
    premiere, derniere = h + 1, max(r, h + 1)

    # Total : SOUS.TOTAL(9, …) = somme qui suit les filtres automatiques
    r = derniere + 1
    ws.cell(row=r, column=1, value='TOTAL')
    for j, col in enumerate(colonnes, start=1):
        c = ws.cell(row=r, column=j)
        c.font = Font(bold=True)
        c.fill = total_fill
        c.border = Border(left=fin, right=fin, top=Side(style='medium', color='1F4E79'), bottom=fin)
        if col[1] in sommes:
            L = get_column_letter(j)
            c.value = f'=SUBTOTAL(9,{L}{premiere}:{L}{derniere})'
            c.number_format = _XL_FMT[col[3]]
    ws.cell(row=r + 1, column=1,
            value='Le total suit les filtres (SOUS.TOTAL) : filtrez une colonne pour obtenir un sous-total.'
            ).font = Font(italic=True, size=8, color='7F8C8D')

    ws.freeze_panes = ws.cell(row=h + 1, column=1)
    ws.auto_filter.ref = f'A{h}:{der}{derniere}'
    ws.print_title_rows = f'{h}:{h}'
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.oddFooter.left.text = f'{societe} — {titre}' if societe else titre
    ws.oddFooter.right.text = 'Page &P / &N'

    # Feuille « Par dépôt »
    rep = [x for x in donnees['repartition'] if x['nb_produits']]
    if rep:
        wd = wb.create_sheet('Par dépôt')
        ent = ['Dépôt', 'Code', 'Type', 'Produits', 'Quantité', 'Valeur']
        for j, (t, w) in enumerate(zip(ent, [32, 12, 10, 12, 14, 20]), start=1):
            c = wd.cell(row=1, column=j, value=t)
            c.font, c.fill, c.border = Font(bold=True, color='FFFFFF'), entete_fill, bord
            c.alignment = Alignment(horizontal='center')
            wd.column_dimensions[get_column_letter(j)].width = w
        for i, x in enumerate(rep, start=2):
            for j, (v, f) in enumerate([(x['nom'], None), (x['code'], None), (x['type'], None),
                                        (x['nb_produits'], '#,##0'), (x['qty'], '#,##0'),
                                        (float(x['valeur']), _XL_FMT['da'])], start=1):
                c = wd.cell(row=i, column=j, value=v)
                c.border = bord
                if f:
                    c.number_format = f
        t = len(rep) + 2
        wd.cell(row=t, column=1, value='TOTAL')
        for j in range(1, 7):
            c = wd.cell(row=t, column=j)
            c.font, c.fill, c.border = Font(bold=True), total_fill, bord
        for j, f in ((5, '#,##0'), (6, _XL_FMT['da'])):
            L = get_column_letter(j)
            c = wd.cell(row=t, column=j, value=f'=SUM({L}2:{L}{t - 1})')
            c.number_format = f
        wd.freeze_panes = 'A2'
        wd.page_setup.orientation = 'landscape'

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


# ======================
# RAPPORTS SPÉCIFIQUES
# ======================

_TITRE_VALORISATION = "État de valorisation du stock"


def _colonnes_valorisation(donnees, prix, excel=False):
    lib_pu = "Prix d'achat moyen" if prix == PRIX_ACHAT else 'Prix de vente unit.'
    cols = []
    if excel and donnees['par_depot']:
        cols += [('Dépôt', 'depot', 22, 'text'), ('Type', 'type_depot', 9, 'text')]
    cols += [('Référence', 'reference', 16 if excel else 11, 'text'),
             ('Désignation', 'designation', 42 if excel else 30, 'text'),
             ('Catégorie', 'categorie', 20 if excel else 14, 'text'),
             ('Qté', 'qty', 10 if excel else 7, 'int'),
             (lib_pu, 'pu', 18 if excel else 12, 'da'),
             ('Valeur du stock', 'valeur', 20 if excel else 14, 'da'),
             ('Statut', 'statut', 12 if excel else 8, 'statut')]
    return cols


def generate_stock_valuation_excel(warehouse_id=None, company=TOUTES_ENTREPRISES, par_depot=False,
                                   prix=PRIX_VENTE, societe=None):
    """Valorisation du stock (Excel) : une ligne par produit (ou par produit et dépôt)."""
    d = donnees_etat_stock(company, warehouse_id, par_depot, prix)
    societe = nom_societe(company) if societe is None else societe
    return _xlsx_etat_stock(_TITRE_VALORISATION.upper(), societe, d,
                            _colonnes_valorisation(d, prix, excel=True), ('qty', 'valeur'), 'Valorisation stock')


def generate_stock_valuation_pdf(warehouse_id=None, company=TOUTES_ENTREPRISES, par_depot=False,
                                 prix=PRIX_VENTE, societe=None):
    """Valorisation du stock (PDF A4 paysage)."""
    d = donnees_etat_stock(company, warehouse_id, par_depot, prix)
    societe = nom_societe(company) if societe is None else societe
    resume = [('Produits en stock', fmt_nombre(d['nb_produits'])),
              ('Quantité totale', fmt_nombre(d['total_qty'])),
              ('Valeur totale du stock', fmt_da(d['total_valeur']))]
    return _pdf_etat_stock(_TITRE_VALORISATION.upper(), societe, d,
                           _colonnes_valorisation(d, prix), ('qty', 'valeur'), resume)


def generate_sales_report_excel(start_date=None, end_date=None, company=TOUTES_ENTREPRISES):
    """
    Rapport des ventes (Excel)
    """
    gen = ExcelReportGenerator()
    gen.ws.title = "Rapport Ventes"

    # Titre
    current_row = gen.add_title("RAPPORT DES VENTES")

    # Période
    if start_date and end_date:
        gen.ws.merge_cells(f'A{current_row}:F{current_row}')
        cell = gen.ws[f'A{current_row}']
        cell.value = f"Période: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
        cell.alignment = Alignment(horizontal='center')
        current_row += 1

    current_row = gen.add_metadata(current_row)

    # Toutes les origines : PC, téléphone, commandes livrées
    docs = ventes_toutes_origines(start_date, end_date, company)

    # En-têtes
    headers = ['Origine', 'N° Vente', 'Date', 'Client', 'Type Paiement', 'HT', 'TTC', 'Remise %']
    gen.set_column_widths([16, 18, 12, 25, 15, 15, 15, 12])
    current_row = gen.add_header_row(headers, current_row)

    # Données
    data_rows = []
    total_ht = Decimal('0.00')
    total_ttc = Decimal('0.00')
    par_origine = {k: Decimal('0.00') for k in ORIGINES}

    for d in docs:
        total_ht += d['ht']
        total_ttc += d['ttc']
        par_origine[d['origine']] += d['ttc']
        data_rows.append([
            ORIGINES[d['origine']],
            d['numero'],
            d['date'].strftime('%d/%m/%Y') if d['date'] else '',
            f"{d['client'].nom} {d['client'].prenom or ''}".strip() if d['client'] else 'N/A',
            d['paiement'],
            float(d['ht']),
            float(d['ttc']),
            float(d['remise']),
        ])

    current_row = gen.add_data_rows(data_rows, current_row, number_columns=[6, 7, 8])

    # Total
    current_row = gen.add_total_row(current_row, 5, "TOTAL", {
        6: float(total_ht),
        7: float(total_ttc)
    })
    # Sous-totaux par origine
    for cle, libelle in ORIGINES.items():
        current_row = (current_row or 0) + 1
        gen.ws.cell(row=current_row, column=5, value=f'dont {libelle}')
        gen.ws.cell(row=current_row, column=7, value=float(par_origine[cle]))

    return gen.save_to_buffer()


def generate_sales_report_pdf(start_date=None, end_date=None, company=TOUTES_ENTREPRISES):
    """
    Rapport des ventes (PDF)
    """
    gen = PDFReportGenerator("RAPPORT DES VENTES", orientation='landscape')
    gen.add_title()

    # Période
    if start_date and end_date:
        period_style = ParagraphStyle('Period', parent=gen.styles['Normal'], fontSize=11, alignment=1)
        gen.elements.append(Paragraph(
            f"<b>Période:</b> {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
            period_style
        ))
        gen.elements.append(Spacer(1, 12))

    gen.add_metadata()

    # Toutes les origines : PC, téléphone, commandes livrées
    docs = ventes_toutes_origines(start_date, end_date, company)

    # Tableau
    table_data = [['Origine', 'N° Vente', 'Date', 'Client', 'Paiement', 'Montant HT', 'Montant TTC', 'Remise %']]

    total_ht = Decimal('0.00')
    total_ttc = Decimal('0.00')
    count_ventes = 0
    par_origine = {k: Decimal('0.00') for k in ORIGINES}

    for d in docs:
        total_ht += d['ht']
        total_ttc += d['ttc']
        par_origine[d['origine']] += d['ttc']
        count_ventes += 1
        table_data.append([
            ORIGINES[d['origine']],
            d['numero'],
            d['date'].strftime('%d/%m/%Y') if d['date'] else '',
            f"{d['client'].nom} {d['client'].prenom or ''}".strip()[:25] if d['client'] else 'N/A',
            d['paiement'],
            f"{d['ht']:.2f}",
            f"{d['ttc']:.2f}",
            f"{d['remise']:.1f}%"
        ])

    # Ligne de total
    table_data.append(['', '', '', '', 'TOTAL', f"{total_ht:.2f}", f"{total_ttc:.2f}", ''])

    gen.add_table(table_data, col_widths=[1.1*inch, 1.2*inch, 0.9*inch, 1.7*inch, 0.9*inch, 1.1*inch, 1.1*inch, 0.7*inch])

    # Résumé
    ticket_moyen = total_ttc / count_ventes if count_ventes > 0 else Decimal('0.00')
    summary_data = [
        ['Nombre de ventes:', str(count_ventes)],
        ['Chiffre d\'affaires HT:', f"{total_ht:.2f}"],
        ['Chiffre d\'affaires TTC:', f"{total_ttc:.2f}"],
        ['  dont ventes PC:', f"{par_origine['pc']:.2f}"],
        ['  dont ventes téléphone:', f"{par_origine['telephone']:.2f}"],
        ['  dont commandes livrées:', f"{par_origine['commande']:.2f}"],
        ['Ticket moyen:', f"{ticket_moyen:.2f}"]
    ]
    gen.add_summary_box(summary_data)

    return gen.build()


_TITRE_INVENTAIRE = "État du stock — inventaire complet"


def _colonnes_inventaire(excel=False):
    return [('Référence', 'reference', 16 if excel else 10, 'text'),
            ('Code-barres', 'code_barre', 16 if excel else 11, 'text'),
            ('Désignation', 'designation', 40 if excel else 25, 'text'),
            ('Catégorie', 'categorie', 18 if excel else 11, 'text'),
            ('Fournisseur', 'fournisseur', 18 if excel else 11, 'text'),
            ('Qté', 'qty', 9 if excel else 6, 'int'),
            ('Seuil alerte', 'seuil', 10 if excel else 6, 'int'),
            ('Prix de vente unit.', 'pu', 16 if excel else 10, 'da'),
            ('Valeur du stock', 'valeur', 18 if excel else 11.5, 'da'),
            ('Statut', 'statut', 11 if excel else 7, 'statut')]


def generate_inventory_report_excel(company=TOUTES_ENTREPRISES, warehouse_id=None, societe=None):
    """Inventaire complet (Excel) : tous les produits actifs, même à 0, quantités ProductStock."""
    d = donnees_etat_stock(company, warehouse_id, inclure_zero=True)
    societe = nom_societe(company) if societe is None else societe
    return _xlsx_etat_stock(_TITRE_INVENTAIRE.upper(), societe, d, _colonnes_inventaire(excel=True),
                            ('qty', 'valeur'), 'Inventaire')


def generate_inventory_report_pdf(company=TOUTES_ENTREPRISES, warehouse_id=None, societe=None):
    """Inventaire complet (PDF A4 paysage) avec synthèse des statuts."""
    d = donnees_etat_stock(company, warehouse_id, inclure_zero=True)
    societe = nom_societe(company) if societe is None else societe
    resume = [(f'Produits en {STATUTS_STOCK[k][0].lower()}' if k != 'normal' else 'Produits au niveau normal',
               f'<font color="{STATUTS_STOCK[k][1]}">{fmt_nombre(d["nb_statuts"][k])}</font>')
              for k in ('rupture', 'critique', 'alerte', 'normal')]
    resume += [('Total produits', fmt_nombre(len(d['lignes']))),
               ('Quantité totale', fmt_nombre(d['total_qty'])),
               ('Valeur totale (prix de vente)', fmt_da(d['total_valeur']))]
    return _pdf_etat_stock(_TITRE_INVENTAIRE.upper(), societe, d, _colonnes_inventaire(), ('qty', 'valeur'), resume)


# ======================
# RAPPORT DES BÉNÉFICES
# ======================

def _get_profit_data(company=None, start_date=None, end_date=None):
    """Calcule prix_vente - prix_achat_moyen par produit. Retourne (list_rows, total_benefice).

    Chaque ligne porte aussi le BÉNÉFICE RÉALISÉ sur ce qui a été vendu (ventes du PC, ventes du
    téléphone, commandes livrées) : CA HT vendu - quantité vendue x prix d'achat moyen.
    Avant : seul le bénéfice potentiel sur le stock était calculé, sans aucune vente.

    `company` : limite aux produits et achats de cette entreprise (produits partages,
    sans entreprise, compris). None = toutes les entreprises (usage interne uniquement)."""
    from collections import defaultdict
    from django.db.models import Q

    achats = Achat.objects.all()
    stocks = ProductStock.objects.filter(quantity__gt=0, produit__is_active=True)
    products = Produit.objects.filter(is_active=True)
    if company is not None:
        achats = achats.filter(company=company)
        products = products.filter(Q(company=company) | Q(company__isnull=True))
        stocks = stocks.filter(produit__in=products)

    # Prix d'achat moyen par produit (normalisé à la pièce)
    product_prix_achat = defaultdict(list)
    for achat in achats:
        prix_piece = achat.get_prix_unitaire_piece()
        if prix_piece:
            product_prix_achat[achat.produit_id].append(Decimal(str(prix_piece)))

    # Stock total par produit (tous entrepôts)
    product_qty = defaultdict(int)
    for ps in stocks:
        product_qty[ps.produit_id] += ps.quantity

    products = products.select_related('categorie').order_by('designation')

    vendus, _ = quantites_vendues(company, start_date, end_date)

    rows = []
    total_benefice = Decimal('0.00')

    for product in products:
        prix_vente = product.prixU or Decimal('0.00')
        prix_achats = product_prix_achat.get(product.id, [])
        avg_achat = sum(prix_achats) / len(prix_achats) if prix_achats else Decimal('0.00')
        avg_achat = Decimal(str(round(float(avg_achat), 2)))

        benefice_unit = prix_vente - avg_achat
        qty = product_qty.get(product.id, 0)
        benefice_total = benefice_unit * qty
        total_benefice += benefice_total

        v = vendus.get(product.id, {'qte': Decimal('0'), 'ca': Decimal('0')})
        rows.append({
            'reference': product.reference,
            'designation': product.designation,
            'prix_vente': prix_vente,
            'avg_achat': avg_achat,
            'benefice_unit': benefice_unit,
            'qty': qty,
            'benefice_total': benefice_total,
            'qte_vendue': v['qte'],
            'ca_vendu': v['ca'],
            'benefice_realise': v['ca'] - v['qte'] * avg_achat,
        })

    return rows, total_benefice


def generate_profit_report_excel(company=None):
    """Rapport des bénéfices par produit (Excel) — prix vente - prix achat moyen."""
    gen = ExcelReportGenerator()
    gen.ws.title = "Bénéfices"

    # Titre sur 7 colonnes
    gen.ws.merge_cells('A1:G1')
    cell = gen.ws['A1']
    cell.value = "RAPPORT DES BÉNÉFICES PAR PRODUIT"
    cell.font = gen.title_font
    cell.alignment = Alignment(horizontal='center', vertical='center')
    current_row = 2
    current_row = gen.add_metadata(current_row)

    headers = ['Référence', 'Désignation', 'Prix Vente', 'Prix Achat Moy.', 'Bénéfice Unit.', 'Qté Stock',
               'Bénéfice estimé (stock)', 'Qté vendue', 'CA HT vendu', 'Bénéfice réalisé']
    gen.set_column_widths([15, 30, 13, 15, 14, 11, 20, 12, 15, 17])
    current_row = gen.add_header_row(headers, current_row)

    rows, total_benefice = _get_profit_data(company)
    data_rows = [
        [r['reference'], r['designation'], float(r['prix_vente']), float(r['avg_achat']),
         float(r['benefice_unit']), r['qty'], float(r['benefice_total']),
         float(r['qte_vendue']), float(r['ca_vendu']), float(r['benefice_realise'])]
        for r in rows
    ]
    current_row = gen.add_data_rows(data_rows, current_row, number_columns=[3, 4, 5, 6, 7, 8, 9, 10])

    gen.add_total_row(current_row, 6, "TOTAL", {
        7: float(total_benefice),
        9: float(sum((r['ca_vendu'] for r in rows), Decimal('0'))),
        10: float(sum((r['benefice_realise'] for r in rows), Decimal('0'))),
    })

    return gen.save_to_buffer()


def generate_profit_report_pdf(company=None):
    """Rapport des bénéfices par produit (PDF) — prix vente - prix achat moyen."""
    gen = PDFReportGenerator("RAPPORT DES BÉNÉFICES PAR PRODUIT", orientation='landscape')
    gen.add_title()
    gen.add_metadata()

    rows, total_benefice = _get_profit_data(company)

    table_data = [['Réf.', 'Désignation', 'Prix V.', 'Achat moy.', 'Bénéf. U.', 'Stock', 'Estimé (stock)',
                   'Vendu', 'CA HT vendu', 'Réalisé']]
    for r in rows:
        table_data.append([
            r['reference'],
            r['designation'][:24],
            f"{r['prix_vente']:.2f}",
            f"{r['avg_achat']:.2f}",
            f"{r['benefice_unit']:.2f}",
            str(r['qty']),
            f"{r['benefice_total']:.2f}",
            f"{r['qte_vendue']:.0f}",
            f"{r['ca_vendu']:.2f}",
            f"{r['benefice_realise']:.2f}",
        ])
    total_realise = sum((r['benefice_realise'] for r in rows), Decimal('0'))
    total_ca = sum((r['ca_vendu'] for r in rows), Decimal('0'))
    table_data.append(['', '', '', '', 'TOTAL', '', f"{total_benefice:.2f}", '', f"{total_ca:.2f}", f"{total_realise:.2f}"])

    gen.add_table(table_data, col_widths=[0.8*inch, 1.9*inch, 0.8*inch, 0.9*inch, 0.8*inch, 0.6*inch,
                                          1*inch, 0.6*inch, 1*inch, 1*inch])

    products_positive = sum(1 for r in rows if r['benefice_unit'] > 0)
    products_negative = sum(1 for r in rows if r['benefice_unit'] < 0)
    summary_data = [
        ['Total produits analysés:', str(len(rows))],
        ['Produits bénéficiaires:', str(products_positive)],
        ['Produits déficitaires:', str(products_negative)],
        ['Bénéfice total estimé (sur le stock):', f"{total_benefice:.2f}"],
        ['Chiffre d\'affaires HT vendu (PC + téléphone + commandes):', f"{total_ca:.2f}"],
        ['Bénéfice réalisé sur les ventes:', f"{total_realise:.2f}"],
    ]
    gen.add_summary_box(summary_data)

    return gen.build()
