import logging
import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db.queries import load_last_scraping_results
from components.notification import render_notification

render_notification()
st.title("📊 Visualisation et Téléchargement des Appels d'Offres")


# --- Récupération des données ---
df = None
if "ao_data" in st.session_state:
    df = st.session_state["ao_data"]
    logging.info("Chargement des données depuis la session Streamlit.")
else:
    logging.info("Données non disponibles en session. Chargement depuis la base...")
    df = load_last_scraping_results()   

if df is not None and not df.empty:

    # Copy DataFrame for filtering
    df_display = df.copy()

    # --- Nettoyage des colonnes ---
    if 'Estimation' in df_display.columns:
        df_display['Estimation'] = pd.to_numeric(
            df_display['Estimation'].astype(str)
              .str.replace(r'\s+', '', regex=True)
              .str.replace('\u00a0', '')
              .str.replace(',', '.')
              .str.replace('[^0-9.]', '', regex=True),
            errors='coerce'
        ).fillna(0)

    if 'Caution' in df_display.columns:
        df_display['Caution'] = pd.to_numeric(
            df_display['Caution'].astype(str)
              .str.replace(r'\s+', '', regex=True)
              .str.replace('\u00a0', '')
              .str.replace(',', '.')
              .str.replace('[^0-9.]', '', regex=True),
            errors='coerce'
        ).fillna(0)

    if 'Date Limite' in df_display.columns:
        df_display['Date Limite'] = pd.to_datetime(df_display['Date Limite'], errors='coerce', dayfirst=True)
        df_display['Marché'] = df_display['Date Limite'].apply(
            lambda x: "🔴 Dépassé" if pd.isna(x) or x < datetime.now() else "🟢 En Cours"
        )

    if 'is_new' in df_display.columns:
        df_display['is_new'] = df_display['is_new'].apply(lambda x: "🔔" if bool(x) else "🔕")


    # --- Filtrage ---
    st.subheader("🎯 Filtrer les Appels d'Offres")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        search_description = st.text_input("🔍 Rechercher par Description")
    with col2:
        search_organisme = st.text_input("🔍 Rechercher par Organisme")
    with col3:
        filter_ville = st.selectbox(
            "🏙️ Filtrer par Ville",
            options=["Toutes"] + sorted(df['Ville'].dropna().unique().tolist()) if 'Ville' in df.columns else ["Toutes"]
        )
    with col4:
        filter_marche = st.selectbox(
            "🏷️ Filtrer par Marché",
            options=["Tous", "🟢 En Cours", "🔴 Dépassé"] if 'Marché' in df.columns else ["Tous"]
        )
    with col5:
        filter_is_new = st.selectbox(
            "🔔 Filtrer par Nouveaux AO",
            options=["Tous", "🔔 Nouveaux", "🔕 Anciens"] if 'is_new' in df.columns else ["Tous"]
        )

    filtered_df = df_display.copy()
    if search_description and 'Description' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Description'].str.contains(search_description, case=False, na=False)]
    if search_organisme and 'Organisme' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Organisme'].str.contains(search_organisme, case=False, na=False)]
    if filter_ville != "Toutes" and 'Ville' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Ville'] == filter_ville]
    if filter_marche != "Tous" and 'Marché' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Marché'] == filter_marche]
    if filter_is_new != "Tous" and 'is_new' in filtered_df.columns:
        if filter_is_new == "🔔 Nouveaux":
            filtered_df = filtered_df[filtered_df['is_new'] == "🔔"]
        else:
            filtered_df = filtered_df[filtered_df['is_new'] == "🔕"]



    # --- Résultats ---
    st.write(f"🔍 **{len(filtered_df)} appels d'offres trouvés après filtrage**")

    # 🎲 Visualisation du tableau
    st.subheader("📋 Tableau des Appels d'Offres")
    st.dataframe(filtered_df, use_container_width=True)

    # --- Téléchargement ---
    st.subheader("📥 Télécharger les résultats")
    excel_buffer = io.BytesIO()
    filtered_df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)

    st.download_button(
        label="📥 Télécharger en Excel",
        data=excel_buffer,
        file_name=f"Appels_Offres_Filtrés_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("⚠️ Aucune donnée disponible. Lancez le scraping manuel ou attendez le scraping planifié.")
