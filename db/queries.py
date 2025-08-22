import logging
from db.database import engine
from sqlalchemy import text
from datetime import datetime
import pandas as pd
import numpy as np

from db.utils import ensure_tables, force_utf8, _to_datetime_series, COL_MAP, inverse_map
from sqlalchemy.exc import IntegrityError
import traceback

# Lecture de la date de dernier scraping
def get_last_scraping_date():
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT last_scraping FROM scraping_metadata ORDER BY id DESC LIMIT 1")
        ).fetchone()
        return row[0] if row else None

# Ecriture de la date de dernier scraping et du nombre de nouvelles AO
def update_last_scraping_meta_data(num_new_ao: int):
    ts = datetime.now()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO scraping_metadata (last_scraping, new_ao_count) VALUES (:ts, :num_new_ao)"),
            {"ts": ts, "num_new_ao": num_new_ao}
        )

# 6) Save + marquage is_new (en mémoire uniquement)
def save_and_mark_new(df: pd.DataFrame, table_name: str = "appels_offres") -> pd.DataFrame:
    """
    - Renomme les colonnes selon COL_MAP
    - Convertit les dates
    - Calcule is_new = date_poste > last_scraping_date (en mémoire, pas en base)
    - Insère en base avec ON CONFLICT (numero_ordre, date_poste)
    - Retourne uniquement les lignes is_new=True
    """
    ensure_tables()

    # Harmoniser les colonnes
    df = df.rename(columns=COL_MAP)

    # S'assurer que toutes les colonnes existent
    for col in COL_MAP.values():
        if col not in df.columns:
            df[col] = None

    # Convertir dates
    df["date_poste"] = _to_datetime_series(df["date_poste"], dayfirst=True)
    if "date_limite" in df.columns:
        df["date_limite"] = _to_datetime_series(df["date_limite"], dayfirst=True)

    # Valeurs numériques
    for num_col in ["caution", "estimation"]:
        if num_col in df.columns:
            df[num_col] = pd.to_numeric(df[num_col], errors="coerce")

    # Valeur par défaut 'marche'
    if "marche" in df.columns:
        df["marche"] = df["marche"].fillna("Non spécifié")

    # Calcul de is_new par rapport à la dernière date de scraping
    df = calculate_is_new(df)

    df = df.replace({pd.NaT: None, np.nan: None})
    
    insert_sql = f"""
        INSERT INTO {table_name} (
            organisme, date_poste, type_offre, ville, numero_ordre,
            numero_ao, date_limite, caution, estimation, description,
            marche
        )
        VALUES (
            :organisme, :date_poste, :type_offre, :ville, :numero_ordre,
            :numero_ao, :date_limite, :caution, :estimation, :description,
            :marche
        )
        ON CONFLICT (numero_ordre, date_poste)
        DO UPDATE SET
            organisme   = EXCLUDED.organisme,
            type_offre  = EXCLUDED.type_offre,
            ville       = EXCLUDED.ville,
            numero_ao   = EXCLUDED.numero_ao,
            date_limite = EXCLUDED.date_limite,
            caution     = EXCLUDED.caution,
            estimation  = EXCLUDED.estimation,
            description = EXCLUDED.description,
            marche      = EXCLUDED.marche;
    """

    # Insertion ligne par ligne
    try:
        with engine.begin() as conn:
            for _, row in df.iterrows():
                data = {k: force_utf8(v) for k, v in row.to_dict().items() if k in COL_MAP.values()}
                conn.execute(text(insert_sql), data)
    except IntegrityError as e:
        print("\n⛔ IntegrityError:", e)
        print(traceback.format_exc())

    df = df.rename(columns=inverse_map)

    return df

def load_last_scraping_results() -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql_table("appels_offres", conn)
        df = calculate_is_new(df)
        df = df.rename(columns=inverse_map)
        return df

def calculate_is_new(df: pd.DataFrame) -> pd.DataFrame:
    last_scraping_date = get_last_scraping_date()
    if last_scraping_date is None:
        df["is_new"] = True
        logging.info("Aucune date de dernier scraping trouvée. Tous les AO sont marqués comme nouveaux.")
    else:
        df["is_new"] = df["date_poste"] > last_scraping_date
    return df