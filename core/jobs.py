# core/jobs.py
import streamlit as st
from core.extract import extract_aos
from db.queries import save_and_mark_new
from db.queries import update_last_scraping_meta_data

def run_scraping_job(use_streamlit=True):
    try:
        df_extracted = extract_aos()
        print(df_extracted.columns)
        df = save_and_mark_new(df_extracted)
        print(df.columns)
        num_new_ao = len(df[df['is_new'] == True])

        # Sauvegarde des métadonnées
        st.session_state["ao_data"] = df
        st.session_state["num_new_ao"] = num_new_ao
        update_last_scraping_meta_data(num_new_ao)
        if use_streamlit:
            st.success(f"✅ {num_new_ao} nouveaux appels d'offres détectés et enregistrés.")

        return df, num_new_ao

    except Exception as e:
        if use_streamlit:
            st.error(f"❌ Une erreur est survenue : {e}")
        else:
            print(f"[ERREUR] Scraping échoué : {e}")
        return None, 0
