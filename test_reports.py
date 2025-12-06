"""
Script de test pour les exports de rapports
Execute avec: python test_reports.py
"""

import os
import sys
import django

# Fix pour l'encodage Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.reports import (
    generate_stock_valuation_excel,
    generate_stock_valuation_pdf,
    generate_sales_report_excel,
    generate_sales_report_pdf,
    generate_inventory_report_excel,
    generate_inventory_report_pdf
)
from datetime import datetime, timedelta


def test_stock_valuation_excel():
    """Test export Excel valorisation du stock"""
    print("🧪 Test: Stock Valuation (Excel)...", end=' ')
    try:
        buffer = generate_stock_valuation_excel()
        assert buffer.tell() == 0, "Buffer devrait être à la position 0"
        assert len(buffer.getvalue()) > 0, "Le fichier Excel devrait contenir des données"
        print("✅ OK")
        return True
    except Exception as e:
        print(f"❌ ÉCHEC: {e}")
        return False


def test_stock_valuation_pdf():
    """Test export PDF valorisation du stock"""
    print("🧪 Test: Stock Valuation (PDF)...", end=' ')
    try:
        buffer = generate_stock_valuation_pdf()
        assert buffer.tell() == 0, "Buffer devrait être à la position 0"
        assert len(buffer.getvalue()) > 0, "Le fichier PDF devrait contenir des données"
        # Vérifier le magic number PDF
        content = buffer.getvalue()
        assert content.startswith(b'%PDF'), "Le fichier devrait commencer par %PDF"
        print("✅ OK")
        return True
    except Exception as e:
        print(f"❌ ÉCHEC: {e}")
        return False


def test_sales_report_excel():
    """Test export Excel rapport de ventes"""
    print("🧪 Test: Sales Report (Excel)...", end=' ')
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        buffer = generate_sales_report_excel(start_date, end_date)
        assert buffer.tell() == 0, "Buffer devrait être à la position 0"
        assert len(buffer.getvalue()) > 0, "Le fichier Excel devrait contenir des données"
        print("✅ OK")
        return True
    except Exception as e:
        print(f"❌ ÉCHEC: {e}")
        return False


def test_sales_report_pdf():
    """Test export PDF rapport de ventes"""
    print("🧪 Test: Sales Report (PDF)...", end=' ')
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        buffer = generate_sales_report_pdf(start_date, end_date)
        assert buffer.tell() == 0, "Buffer devrait être à la position 0"
        assert len(buffer.getvalue()) > 0, "Le fichier PDF devrait contenir des données"
        content = buffer.getvalue()
        assert content.startswith(b'%PDF'), "Le fichier devrait commencer par %PDF"
        print("✅ OK")
        return True
    except Exception as e:
        print(f"❌ ÉCHEC: {e}")
        return False


def test_inventory_report_excel():
    """Test export Excel inventaire complet"""
    print("🧪 Test: Inventory Report (Excel)...", end=' ')
    try:
        buffer = generate_inventory_report_excel()
        assert buffer.tell() == 0, "Buffer devrait être à la position 0"
        assert len(buffer.getvalue()) > 0, "Le fichier Excel devrait contenir des données"
        print("✅ OK")
        return True
    except Exception as e:
        print(f"❌ ÉCHEC: {e}")
        return False


def test_inventory_report_pdf():
    """Test export PDF inventaire complet"""
    print("🧪 Test: Inventory Report (PDF)...", end=' ')
    try:
        buffer = generate_inventory_report_pdf()
        assert buffer.tell() == 0, "Buffer devrait être à la position 0"
        assert len(buffer.getvalue()) > 0, "Le fichier PDF devrait contenir des données"
        content = buffer.getvalue()
        assert content.startswith(b'%PDF'), "Le fichier devrait commencer par %PDF"
        print("✅ OK")
        return True
    except Exception as e:
        print(f"❌ ÉCHEC: {e}")
        return False


def test_save_samples():
    """Génère des exemples de fichiers pour inspection manuelle"""
    print("\n📦 Génération d'exemples de fichiers...")

    output_dir = "sample_reports"
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Stock valuation
        excel_buffer = generate_stock_valuation_excel()
        with open(f"{output_dir}/stock_valuation_sample.xlsx", "wb") as f:
            f.write(excel_buffer.getvalue())
        print(f"  ✅ {output_dir}/stock_valuation_sample.xlsx")

        pdf_buffer = generate_stock_valuation_pdf()
        with open(f"{output_dir}/stock_valuation_sample.pdf", "wb") as f:
            f.write(pdf_buffer.getvalue())
        print(f"  ✅ {output_dir}/stock_valuation_sample.pdf")

        # Sales report
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        excel_buffer = generate_sales_report_excel(start_date, end_date)
        with open(f"{output_dir}/sales_report_sample.xlsx", "wb") as f:
            f.write(excel_buffer.getvalue())
        print(f"  ✅ {output_dir}/sales_report_sample.xlsx")

        pdf_buffer = generate_sales_report_pdf(start_date, end_date)
        with open(f"{output_dir}/sales_report_sample.pdf", "wb") as f:
            f.write(pdf_buffer.getvalue())
        print(f"  ✅ {output_dir}/sales_report_sample.pdf")

        # Inventory report
        excel_buffer = generate_inventory_report_excel()
        with open(f"{output_dir}/inventory_sample.xlsx", "wb") as f:
            f.write(excel_buffer.getvalue())
        print(f"  ✅ {output_dir}/inventory_sample.xlsx")

        pdf_buffer = generate_inventory_report_pdf()
        with open(f"{output_dir}/inventory_sample.pdf", "wb") as f:
            f.write(pdf_buffer.getvalue())
        print(f"  ✅ {output_dir}/inventory_sample.pdf")

        print(f"\n✅ Tous les exemples générés dans le dossier '{output_dir}/'")
        return True

    except Exception as e:
        print(f"❌ Erreur lors de la génération: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("🧪 TESTS DES EXPORTS DE RAPPORTS")
    print("=" * 60)
    print()

    # Stats de la base de données
    from API.models import Produit, Vente, Client

    print("📊 Statistiques de la base de données:")
    print(f"  - Produits actifs: {Produit.objects.filter(is_active=True).count()}")
    print(f"  - Ventes complétées: {Vente.objects.filter(statut='completed').count()}")
    print(f"  - Clients: {Client.objects.count()}")
    print()

    # Exécuter les tests
    tests = [
        test_stock_valuation_excel,
        test_stock_valuation_pdf,
        test_sales_report_excel,
        test_sales_report_pdf,
        test_inventory_report_excel,
        test_inventory_report_pdf,
    ]

    results = []
    for test in tests:
        results.append(test())

    # Résumé
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"📊 RÉSUMÉ: {passed}/{total} tests réussis")

    if passed == total:
        print("🎉 Tous les tests sont passés!")
    else:
        print("⚠️ Certains tests ont échoué")

    print("=" * 60)
    print()

    # Générer des exemples
    if passed == total:
        test_save_samples()

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
