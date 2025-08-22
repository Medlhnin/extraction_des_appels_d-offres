from sqlalchemy import create_engine

# 1) Connexion
DB_URL = "postgresql://postgres:your_password@localhost:5432/AppelOffre"
engine = create_engine(DB_URL, future=True, pool_pre_ping=True)