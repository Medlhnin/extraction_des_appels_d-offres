from __future__ import annotations

import traceback
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

# ----------------------------------------------------------------------
# 1. Configuration connexion
#    ➜ adaptez le mot de passe, l’hôte, le port et la base si nécessaire
# ----------------------------------------------------------------------
DB_URL = "postgresql://postgres:your_password@localhost:5432/AppelOffre"
engine = create_engine(DB_URL, future=True, pool_pre_ping=True)

# ----------------------------------------------------------------------
# 2. Correspondance DataFrame ➜ colonnes SQL
#    (ajoutez / modifiez si le scraping évolue)
# ----------------------------------------------------------------------
COL_MAP = {
    "Organisme": "organisme",
    "Date de Poste": "date_poste",
    "Type d'AO": "type_offre",
    "Ville": "ville",
    "Numéro d'ordre": "numero_ordre",
    "Numéro AO": "numero_ao",
    "Date Limite": "date_limite",
    "Caution": "caution",
    "Estimation": "estimation",
    "Description": "description",
    "Marché": "marche",           # ajouté depuis la logique Streamlit
}

# ----------------------------------------------------------------------
# 3. Outils
# ----------------------------------------------------------------------
def force_utf8(value):
    """Tente de convertir énigmatiques encodages latin‑1 en UTF‑8, sinon renvoie intact."""
    if isinstance(value, str):
        try:
            return value.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
        except Exception:
            return value
    return value


# ----------------------------------------------------------------------
# 4. Fonction principale : save_and_mark_new
# ----------------------------------------------------------------------
def save_and_mark_new(df: pd.DataFrame, table_name: str = "appels_offres") -> pd.DataFrame:
    """
    Enregistre les AO dans `table_name`.
    • Ajoute/renomme les colonnes pour correspondre aux champs SQL.
    • Déduplique sur (numero_ordre, date_poste) : si déjà présent → is_new = FALSE.
    Retourne un DataFrame des entrées effectivement insérées comme « nouvelles ».
    """
    # -- 4‑1. Harmonisation des colonnes
    df = df.rename(columns=COL_MAP)

    for col in COL_MAP.values():
        if col not in df.columns:
            df[col] = None

    # Valeur par défaut pour 'marche'
    df["marche"] = df.get("marche").fillna("Non spécifié")

    # -- 4‑2. Connexion
    conn = engine.connect()
    new_entries = []

    for idx, row in df.iterrows():
        try:
            # Nettoyage encodage
            data = {k: force_utf8(v) for k, v in row.to_dict().items()}
            data["is_new"] = True

            insert_stmt = text(f"""
                INSERT INTO {table_name} (
                    organisme, date_poste, type_offre, ville, numero_ordre,
                    numero_ao, date_limite, caution, estimation, description,
                    marche, is_new
                )
                VALUES (
                    :organisme, :date_poste, :type_offre, :ville, :numero_ordre,
                    :numero_ao, :date_limite, :caution, :estimation, :description,
                    :marche, :is_new
                )
                ON CONFLICT (numero_ordre, date_poste)
                DO UPDATE SET is_new = FALSE
                RETURNING *;
            """)

            result = conn.execute(insert_stmt, data)
            new_entries.append(dict(result.fetchone()))

        except IntegrityError:  # autre conflit de clé unique
            conn.rollback()
            continue

        except Exception as e:
            print(f"\n⛔ ERREUR FATALE à la ligne {idx} : {e}")
            print(f"📌 Données brutes : {row.to_dict()}")
            print(traceback.format_exc())
            conn.rollback()
            continue

    conn.commit()
    conn.close()

    return pd.DataFrame(new_entries)
