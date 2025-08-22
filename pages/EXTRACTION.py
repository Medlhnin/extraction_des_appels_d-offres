import streamlit as st
from core.jobs import run_scraping_job
from components.notification import render_notification

st.title("1️⃣ Lancer le Scraping des Appels d'Offres")
st.write("Appuyez sur le bouton ci-dessous pour démarrer l'extraction des appels d'offres.")

if st.button("🚀 Démarrer le Scraping"):
    with st.spinner("🔎 Extraction en cours... Veuillez patienter."):
        run_scraping_job(use_streamlit=True)
