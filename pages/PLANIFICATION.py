# Planification.py
import streamlit as st
from core.scheduler import update_config, get_config, schedule_job
import datetime
from components.notification import render_notification

st.title("⚙️ Planification du Scraping")

row = get_config()
enabled = row[0] if row else False
scraping_time = str(row[1]) if row else "12:00"


st.checkbox("Activer la planification", value=enabled, key="enabled")
st.time_input(
    "Heure d'exécution",
    value=scraping_time if scraping_time is not None else datetime.time(9, 0),
    key="scraping_time",
    step=60  
)

if st.button("💾 Sauvegarder"):
    ok = update_config(st.session_state.enabled, st.session_state.scraping_time)
    if ok:
        schedule_job() 
        st.success("✅ Configuration mise à jour et planification relancée.")
    else:
        st.error("❌ Erreur lors de la mise à jour.")
