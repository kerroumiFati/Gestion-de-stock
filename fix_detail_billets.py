import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.db import connection

# Supprimer l'ancienne colonne detail_billets_json
with connection.cursor() as cursor:
    try:
        # SQLite ne supporte pas DROP COLUMN directement
        # On doit recréer la table sans cette colonne

        # 1. Créer une table temporaire avec les bonnes colonnes
        cursor.execute("""
            CREATE TABLE API_rapportcaissemobile_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fonds_depart DECIMAL NOT NULL,
                total_especes DECIMAL NOT NULL,
                total_cartes DECIMAL NOT NULL,
                total_cheques DECIMAL NOT NULL,
                total_credits DECIMAL NOT NULL,
                total_encaissements DECIMAL NOT NULL,
                carburant DECIMAL NOT NULL,
                reparations DECIMAL NOT NULL,
                autres_depenses DECIMAL NOT NULL,
                total_depenses DECIMAL NOT NULL,
                solde_final_theorique DECIMAL NOT NULL,
                solde_final_reel DECIMAL NOT NULL,
                ecart DECIMAL NOT NULL,
                detail_billets TEXT,
                justification_ecart TEXT NOT NULL,
                statut VARCHAR(20) NOT NULL,
                date_validation DATETIME,
                a_des_anomalies BOOLEAN NOT NULL,
                notes_anomalies TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                tournee_id BIGINT NOT NULL UNIQUE,
                valide_par_id INTEGER,
                company_id INTEGER
            )
        """)

        # 2. Copier les données
        cursor.execute("""
            INSERT INTO API_rapportcaissemobile_new
            SELECT
                id, fonds_depart, total_especes, total_cartes, total_cheques,
                total_credits, total_encaissements, carburant, reparations,
                autres_depenses, total_depenses, solde_final_theorique,
                solde_final_reel, ecart, detail_billets, justification_ecart,
                statut, date_validation, a_des_anomalies, notes_anomalies,
                created_at, updated_at, tournee_id, valide_par_id, company_id
            FROM API_rapportcaissemobile
        """)

        # 3. Supprimer l'ancienne table
        cursor.execute("DROP TABLE API_rapportcaissemobile")

        # 4. Renommer la nouvelle table
        cursor.execute("ALTER TABLE API_rapportcaissemobile_new RENAME TO API_rapportcaissemobile")

        print("Colonne detail_billets_json supprimee avec succes!")

    except Exception as e:
        print(f"Erreur: {e}")
        print("La colonne a peut-etre deja ete supprimee")
