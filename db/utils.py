from db.database import engine
from sqlalchemy import text
import pandas as pd

# Mapping colonnes DataFrame -> Base
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

# Inverse mapping
inverse_map = {v: k for k, v in COL_MAP.items()}

# Création des tables si elles n'existent pas
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

# Forcer UTF-8
def force_utf8(value):
    if isinstance(value, str):
        try:
            return value.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
        except Exception:
            return value
    return value

# Serie vers Dataframe
def _to_datetime_series(s: pd.Series, dayfirst: bool = True):
    return pd.to_datetime(s, errors="coerce", dayfirst=dayfirst)