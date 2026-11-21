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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
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
# RAPPORTS SPÉCIFIQUES
# ======================

def generate_stock_valuation_excel(warehouse_id=None, company=TOUTES_ENTREPRISES):
    """
    Rapport de valorisation du stock (Excel)
    Montre la valeur totale du stock par produit
    """
    gen = ExcelReportGenerator()
    gen.ws.title = "Valorisation Stock"

    # Titre
    current_row = gen.add_title("RAPPORT DE VALORISATION DU STOCK")
    current_row = gen.add_metadata(current_row)

    if warehouse_id:
        # Stock par entrepôt spécifique
        warehouse = _filtrer_entreprise(Warehouse.objects.all(), company).get(pk=warehouse_id)
        gen.ws[f'A{current_row}'] = f"Entrepôt: {warehouse.name}"
        current_row += 2

        product_stocks = ProductStock.objects.filter(
            warehouse=warehouse,
            quantity__gt=0,
            produit__is_active=True,
        ).select_related('produit', 'produit__categorie')
    else:
        # Tous les entrepôts - calculer la somme des stocks
        gen.ws[f'A{current_row}'] = "Tous les entrepôts"
        current_row += 2

        # Obtenir tous les stocks groupés par produit
        product_stocks = _filtrer_entreprise(ProductStock.objects.filter(
            quantity__gt=0,
            produit__is_active=True,
        ), company, 'warehouse__company').select_related('produit', 'produit__categorie')

    # En-têtes
    headers = ['Référence', 'Désignation', 'Catégorie', 'Qté Stock', 'Prix Unit.', 'Valeur Stock', 'Statut']
    gen.set_column_widths([15, 30, 20, 12, 15, 18, 15])
    current_row = gen.add_header_row(headers, current_row)

    # Regrouper les stocks par produit et calculer les totaux
    from collections import defaultdict
    product_totals = defaultdict(int)

    for ps in product_stocks:
        product_totals[ps.produit.id] += ps.quantity

    # Données
    data_rows = []
    total_value = Decimal('0.00')
    total_qty = 0

    # Récupérer les produits avec stock
    products = Produit.objects.filter(
        id__in=product_totals.keys(),
        is_active=True
    ).select_related('categorie')

    for product in products:
        qty = product_totals[product.id]
        if qty <= 0:
            continue

        unit_price = product.prixU or Decimal('0.00')
        value = qty * unit_price
        total_value += value
        total_qty += qty

        data_rows.append([
            product.reference,
            product.designation,
            product.categorie.nom if product.categorie else 'N/A',
            qty,
            float(unit_price),
            float(value),
            product.get_stock_status()
        ])

    current_row = gen.add_data_rows(data_rows, current_row, number_columns=[4, 5, 6])

    # Total
    gen.add_total_row(current_row, 3, "TOTAL", {
        4: total_qty,
        6: float(total_value)
    })

    return gen.save_to_buffer()


def generate_stock_valuation_pdf(warehouse_id=None, company=TOUTES_ENTREPRISES):
    """
    Rapport de valorisation du stock (PDF)
    """
    gen = PDFReportGenerator("RAPPORT DE VALORISATION DU STOCK", orientation='landscape')
    gen.add_title()
    gen.add_metadata()

    if warehouse_id:
        # Stock par entrepôt spécifique
        warehouse = _filtrer_entreprise(Warehouse.objects.all(), company).get(pk=warehouse_id)
        gen.elements.append(Paragraph(f"<b>Entrepôt:</b> {warehouse.name}", gen.styles['Normal']))
        gen.elements.append(Spacer(1, 12))

        product_stocks = ProductStock.objects.filter(
            warehouse=warehouse,
            quantity__gt=0,
            produit__is_active=True,
        ).select_related('produit', 'produit__categorie')
    else:
        # Tous les entrepôts
        gen.elements.append(Paragraph("<b>Tous les entrepôts</b>", gen.styles['Normal']))
        gen.elements.append(Spacer(1, 12))

        product_stocks = _filtrer_entreprise(ProductStock.objects.filter(
            quantity__gt=0,
            produit__is_active=True,
        ), company, 'warehouse__company').select_related('produit', 'produit__categorie')

    # Regrouper les stocks par produit
    from collections import defaultdict
    product_totals = defaultdict(int)

    for ps in product_stocks:
        product_totals[ps.produit.id] += ps.quantity

    # Récupérer les produits avec stock
    products = Produit.objects.filter(
        id__in=product_totals.keys(),
        is_active=True
    ).select_related('categorie')

    # Tableau
    table_data = [['Référence', 'Désignation', 'Catégorie', 'Qté', 'Prix Unit.', 'Valeur Stock', 'Statut']]

    total_value = Decimal('0.00')
    total_qty = 0

    for product in products:
        qty = product_totals[product.id]
        unit_price = product.prixU or Decimal('0.00')
        value = qty * unit_price
        total_value += value
        total_qty += qty

        table_data.append([
            product.reference,
            product.designation[:30],
            product.categorie.nom if product.categorie else 'N/A',
            str(qty),
            f"{unit_price:.2f}",
            f"{value:.2f}",
            product.get_stock_status()
        ])

    # Ligne de total
    table_data.append(['', '', 'TOTAL', str(total_qty), '', f"{total_value:.2f}", ''])

    gen.add_table(table_data, col_widths=[1.2*inch, 2.5*inch, 1.3*inch, 0.8*inch, 1*inch, 1.2*inch, 1*inch])

    # Résumé
    summary_data = [
        ['Nombre de produits en stock:', str(len(products))],
        ['Quantité totale:', str(total_qty)],
        ['Valeur totale du stock:', f"{total_value:.2f}"]
    ]
    gen.add_summary_box(summary_data)

    return gen.build()


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


def generate_inventory_report_excel(company=TOUTES_ENTREPRISES):
    """
    Rapport d'inventaire complet (Excel)
    """
    gen = ExcelReportGenerator()
    gen.ws.title = "Inventaire"

    # Titre
    current_row = gen.add_title("RAPPORT D'INVENTAIRE COMPLET")
    current_row = gen.add_metadata(current_row)

    # En-têtes
    headers = ['Référence', 'Code Barre', 'Désignation', 'Catégorie', 'Fournisseur', 'Qté', 'Seuil Alerte', 'Prix Unit.', 'Statut']
    gen.set_column_widths([15, 15, 30, 20, 20, 10, 12, 15, 15])
    current_row = gen.add_header_row(headers, current_row)

    # Données
    products = _filtrer_entreprise(Produit.objects.filter(is_active=True), company).select_related('categorie', 'fournisseur').order_by('reference')

    data_rows = []
    for product in products:
        data_rows.append([
            product.reference,
            product.code_barre or '',
            product.designation,
            product.categorie.nom if product.categorie else '',
            product.fournisseur.libelle if product.fournisseur else '',
            product.quantite,
            product.seuil_alerte or 0,
            float(product.prixU or 0),
            product.get_stock_status()
        ])

    gen.add_data_rows(data_rows, current_row, number_columns=[6, 7, 8])

    return gen.save_to_buffer()


def generate_inventory_report_pdf(company=TOUTES_ENTREPRISES):
    """
    Rapport d'inventaire complet (PDF)
    """
    gen = PDFReportGenerator("RAPPORT D'INVENTAIRE COMPLET", orientation='landscape')
    gen.add_title()
    gen.add_metadata()

    products = _filtrer_entreprise(Produit.objects.filter(is_active=True), company).select_related('categorie', 'fournisseur').order_by('reference')

    # Tableau
    table_data = [['Réf.', 'Désignation', 'Catégorie', 'Fournisseur', 'Qté', 'Seuil', 'Prix', 'Statut']]

    for product in products:
        table_data.append([
            product.reference,
            product.designation[:25],
            product.categorie.nom[:15] if product.categorie else '',
            product.fournisseur.libelle[:15] if product.fournisseur else '',
            str(product.quantite),
            str(product.seuil_alerte or 0),
            f"{product.prixU or 0:.2f}",
            product.get_stock_status()
        ])

    gen.add_table(table_data, col_widths=[0.9*inch, 2*inch, 1.2*inch, 1.2*inch, 0.7*inch, 0.7*inch, 0.9*inch, 1*inch])

    # Statistiques
    rupture = products.filter(quantite=0).count()
    critique = products.filter(quantite__gt=0, quantite__lte=F('seuil_critique')).count()
    alerte = products.filter(quantite__gt=F('seuil_critique'), quantite__lte=F('seuil_alerte')).count()
    normal = products.filter(quantite__gt=F('seuil_alerte')).count()

    summary_data = [
        ['Produits en rupture:', str(rupture)],
        ['Produits en critique:', str(critique)],
        ['Produits en alerte:', str(alerte)],
        ['Produits normaux:', str(normal)],
        ['Total produits:', str(products.count())]
    ]
    gen.add_summary_box(summary_data)

    return gen.build()


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
