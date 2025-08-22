import logging
import streamlit as st
from core.scheduler import start_scheduler
# Configuration de l'application
st.set_page_config(page_title="Gestion des Appels d'Offres", layout="wide")

from pages import EXTRACTION, PLANIFICATION, VISUALISATION

# --- HEADER / TITRE ---
st.markdown(
    """
    <h1 style='text-align: center; color: #2E86C1;'>🏠 HOME - Application de Gestion des Appels d'Offres</h1>
    <hr style="margin-top:0.5em; margin-bottom:1.5em;">
    """,
    unsafe_allow_html=True
)

# --- GUIDE UTILISATEUR ---
st.markdown(
    """
    <div style="font-size: 16px; line-height: 1.6;">

    👋 Bienvenue dans l’application **Gestion des Appels d’Offres**.  
    Cette application vous permet d’**extraire, planifier et visualiser** vos données d’appels d’offres.

    ### 🚀 Guide d’utilisation :
    - **📥 Extraction :**  
      Lancez le processus d’extraction des appels d’offres depuis les sources configurées.  
      → Utilisez l’heure d’exécution par défaut : **`{}`h00**.

    - **🗓️ Planification :**  
      Définissez une planification automatique pour exécuter les extractions périodiquement.  

    - **📊 Visualisation :**  
      Consultez et analysez vos données grâce aux graphiques et rapports générés.  

    ---

    ### 🎯 Astuces :
    ✅ Utilisez la **barre latérale** pour naviguer entre les différentes pages.  
    ✅ Vous pouvez modifier l’heure par défaut d’exécution dans la section **Planification**.  
    ✅ L’application est en mode **large** pour une meilleure expérience sur grand écran.  

    </div>
    """,
    unsafe_allow_html=True
)

# --- SIDEBAR ---
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Aller à :",
    ["HOME", "Extraction", "Planification", "Visualisation"],
    index=0  
)

# --- ROUTAGE DES PAGES ---
if page == "EXTRACTION":
    EXTRACTION.app()
elif page == "PLANIFICATION":
    PLANIFICATION.app()
elif page == "VISUALISATION":
    VISUALISATION.app()

start_scheduler()
logging.info("✅ Scheduler démarré.")