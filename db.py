# db.py
from __future__ import annotations

import traceback
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
import numpy as np


# ----------------------------------------------------------------------
# 1) Connexion
# ----------------------------------------------------------------------
DB_URL = "postgresql://postgres:your_password@localhost:5432/AppelOffre"
engine = create_engine(DB_URL, future=True, pool_pre_ping=True)

# ----------------------------------------------------------------------
# 2) Mapping colonnes DataFrame -> Base
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
    "Marché": "marche",
}

# ----------------------------------------------------------------------
# 3) Création des tables si elles n'existent pas
# ----------------------------------------------------------------------
def ensure_tables():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS appels_offres (
            id BIGSERIAL PRIMARY KEY,
            organisme     TEXT,
            date_poste    TIMESTAMP,
            type_offre    TEXT,
            ville         TEXT,
            numero_ordre  TEXT,
            numero_ao     TEXT,
            date_limite   TIMESTAMP,
            caution       NUMERIC,
            estimation    NUMERIC,
            description   TEXT,
            marche        TEXT,
            UNIQUE (numero_ordre, date_poste)
        );
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS scraping_metadata (
            id SERIAL PRIMARY KEY,
            last_scraping TIMESTAMP NOT NULL
        );
        """))

# ----------------------------------------------------------------------
# 4) Utils
# ----------------------------------------------------------------------
def force_utf8(value):
    if isinstance(value, str):
        try:
            return value.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
        except Exception:
            return value
    return value

def _to_datetime_series(s: pd.Series, dayfirst: bool = True):
    return pd.to_datetime(s, errors="coerce", dayfirst=dayfirst)

# ----------------------------------------------------------------------
# 5) Lecture / écriture de la date de dernier scraping
# ----------------------------------------------------------------------
def get_last_scraping_date():
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT last_scraping FROM scraping_metadata ORDER BY id DESC LIMIT 1")
        ).fetchone()
        return row[0] if row else None

def update_last_scraping_meta_data(num_new_ao: int):
    ts = datetime.now()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO scraping_metadata (last_scraping, new_ao_count) VALUES (:ts, :num_new_ao)"),
            {"ts": ts, "num_new_ao": num_new_ao}
        )

# ----------------------------------------------------------------------
# 6) Save + marquage is_new (en mémoire uniquement)
# ----------------------------------------------------------------------
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
    last_scraping_date = get_last_scraping_date()
    if last_scraping_date is None:
        df["is_new"] = True
    else:
        df["is_new"] = df["date_poste"] > last_scraping_date

    df = df.replace({pd.NaT: None, np.nan: None})
    # SQL d'insertion (sans RETURNING is_new)
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

    inverse_map = {v: k for k, v in COL_MAP.items()}
    df = df.rename(columns=inverse_map)

    return df
