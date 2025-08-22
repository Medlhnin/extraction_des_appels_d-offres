from db.database import engine
from sqlalchemy import text
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import datetime
from core.jobs import run_scraping_job

logging.basicConfig(level=logging.INFO)

scheduler = BackgroundScheduler()

def get_config():
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT enabled, scraping_time FROM scraping_config WHERE id = 1;")
        )
        row = result.fetchone()
        return row


def update_config(enabled, scraping_time):
    with engine.begin() as conn:
        # Essayer d’update
        result = conn.execute(
            text("""
                UPDATE scraping_config
                SET enabled = :enabled, scraping_time = :scraping_time
                WHERE id = 1;
            """),
            {"enabled": enabled, "scraping_time": scraping_time}
        )

        # Si aucune ligne affectée → insérer une nouvelle config
        if result.rowcount == 0:
            conn.execute(
                text("""
                    INSERT INTO scraping_config (id, enabled, scraping_time)
                    VALUES (1, :enabled, :scraping_time);
                """),
                {"enabled": enabled, "scraping_time": scraping_time}
            )

        # Vérification
        check = conn.execute(
            text("SELECT enabled, scraping_time FROM scraping_config WHERE id = 1;")
        )
        row = check.fetchone()

    if row and row[0] == enabled and str(row[1]) == str(scraping_time):
        return True
    return False

def job_scraping():
    logging.info(f"[{datetime.datetime.now()}] Lancement de l'extraction automatique...")
    try:
        print("⏳ Tâche planifiée : démarrage du scraping...")
        run_scraping_job(use_streamlit=True)
    except Exception as e:
        logging.error(f"Erreur lors du scraping : {e}")

def schedule_job():
    row = get_config()
    if row:
        enabled, scraping_time = row
        scheduler.remove_all_jobs()
        if enabled:
            hour = scraping_time.hour
            minute = scraping_time.minute
            scheduler.add_job(job_scraping, 'cron', hour=hour, minute=minute, id="scraping_job")
            logging.info(f"Scraping planifié tous les jours à {scraping_time}.")
        else:
            logging.info("Planification désactivée.")

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
    schedule_job()
