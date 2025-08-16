import streamlit as st
import pandas as pd
import io
from datetime import datetime
from Extract_data_from_sodipress import extract_aos
from db import save_and_mark_new
from db import update_last_scraping_meta_data
from db import COL_MAP
import psycopg2

# Configuration de la page
st.set_page_config(page_title="Gestion des Appels d'Offres", layout="wide")

# Styles CSS personnalisés (Dégradé Bleu-Blanc)
st.markdown(
    """
    <style>
    body {
        background: linear-gradient(to right, #e6f2ff, #ffffff);
        color: #000;
    }
    .stDataFrame tbody tr {
        background-color: #ffffff;
        color: #000000;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar pour la navigation
st.sidebar.title("🔧 Configuration")
st.sidebar.subheader("🔄 Workflow de Scraping")
scraping_action = st.sidebar.selectbox("Action :", ["Lancer le Scraping",
                                                    "Charger les Données Extraites",
                                                    "Automatisation"])

# Contenu principal
st.title("🚀 Gestion et Visualisation des Appels d'Offres")

# Section de gestion du scraping
if scraping_action == "Lancer le Scraping":
    st.subheader("1️⃣ Lancer le Scraping des Appels d'Offres")
    st.write("Appuyez sur le bouton ci-dessous pour démarrer l'extraction des appels d'offres.")

    if st.button("🚀 Démarrer le Scraping"):
        with st.spinner("🔎 Extraction en cours... Veuillez patienter."):
            try:
                df_extracted = extract_aos()
                df_extracted = save_and_mark_new(df_extracted)
                num_new_ao = len(df_extracted[df_extracted['is_new'] == True])
                st.session_state["ao_data"] = df_extracted
                st.success(f"✅ {num_new_ao} nouveaux appels d'offres détectés et enregistrés.")
                update_last_scraping_meta_data(num_new_ao)
            except Exception as e:
                st.error(f"❌ Une erreur est survenue : {e}")

# Chargement des Données Extraites
if scraping_action == "Charger les Données Extraites":
    st.subheader("1️⃣ Initialiser les Données")
    if st.button("📊 Charger les Données Extraites"):
        file_path = st.file_uploader("📂 Charger un fichier Excel", type=["xlsx"])

        if file_path:
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                st.session_state["ao_data"] = df
                st.success("✅ Les données ont été chargées avec succès.")
            except Exception as e:
                st.error(f"❌ Erreur lors du chargement des données : {e}")
        else:
            st.info("ℹ️ Veuillez sélectionner un fichier Excel.")

# Si les données sont disponibles
if "ao_data" in st.session_state:
    df = st.session_state["ao_data"]
    
    # Traitement des colonnes
    if 'Estimation' in df.columns:
        # Conversion robuste des valeurs numériques (garder les décimales)
        df['Estimation'] = df['Estimation'].astype(str).str.replace('\s+', '', regex=True)
        df['Estimation'] = df['Estimation'].str.replace('\u00a0', '')  
        df['Estimation'] = df['Estimation'].str.replace(',', '.').str.replace('[^0-9.]', '', regex=True)
        df['Estimation'] = pd.to_numeric(df['Estimation'], errors='coerce').fillna(0)

    if 'Caution' in df.columns:
        df['Caution'] = df['Caution'].astype(str).str.replace('\s+', '', regex=True)
        df['Caution'] = df['Caution'].str.replace('\u00a0', '') 
        df['Caution'] = df['Caution'].str.replace(',', '.').str.replace('[^0-9.]', '', regex=True)
        df['Caution'] = pd.to_numeric(df['Caution'], errors='coerce').fillna(0)

    if 'Date Limite' in df.columns:
        # Convertir Date Limite en format datetime et gérer les valeurs vides
        df['Date Limite'] = pd.to_datetime(df['Date Limite'], errors='coerce', dayfirst=True)
        df['Marché'] = df['Date Limite'].apply(lambda x: "🔴 Dépassé" if pd.isna(x) or x < datetime.now() else "🟢 En Cours")
        df['is_new'] = df['is_new'].apply(lambda x : "🔔" if x == True else "🔕")
    # Visualisation
    st.subheader("2️⃣ Visualiser et Filtrer les Appels d'Offres")

    # Section de filtrage avancé
    st.write("🎯 **Filtrer les Appels d'Offres**")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        search_description = st.text_input("🔍 Rechercher par Description")
    with col2:
        search_organisme = st.text_input("🔍 Rechercher par Organisme")
    with col3:
        if 'Ville' in df.columns:
            filter_ville = st.selectbox("🏙️ Filtrer par Ville", options=["Toutes"] + sorted(df['Ville'].dropna().unique().tolist()))
        else:
            filter_ville = "Toutes"   
    with col4:
        if 'Marché' in df.columns:
            filter_marche = st.selectbox("🏷️ Filtrer par Marché", options=["Tous", "🟢 En Cours", "🔴 Dépassé"])
        else:
            filter_marche = "Tous"

        if 'is_new' in df.columns:
            filter_is_new = st.selectbox("🔔 Filtrer par Nouveaux Appels d'Offres", options=["Tous", "🔔 Nouveaux", "🔕 Anciens"])
        else:
            filter_is_new = "Tous"


    # Application des filtres
    filtered_df = df.copy()

    if search_description:
        if 'Description' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Description'].str.contains(search_description, case=False, na=False)]

    if search_organisme:
        if 'Organisme' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Organisme'].str.contains(search_organisme, case=False, na=False)]

    if filter_ville != "Toutes" and 'Ville' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Ville'] == filter_ville]

    if filter_marche != "Tous" and 'Marché' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Marché'] == filter_marche]

    if filter_is_new != "Tous" and 'is_new' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['is_new'] == (filter_is_new == "🔔 Nouveaux")]

    st.write(f"🔍 **{len(filtered_df)} appels d'offres trouvés après filtrage**")

    # Styles de mise en forme
    def color_estimation(val):
        if pd.notna(val):
            if val >= 500_000:
                return "color: #d9534f; font-weight: bold;"  # Rouge (grande AO)
            elif val < 100_000:
                return "color: #5cb85c; font-weight: bold;"  # Vert (petite AO)
        return ""

    def color_market(val):
        if val == "🔴 Dépassé":
            return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
        elif val == "🟢 En Cours":
            return "background-color: #d4edda; color: #155724; font-weight: bold;"
        return ""

    def color_new_ao(val):
        if val == "🔔":
            return "background-color: #fff3cd; color: #856404; font-weight: bold;"
        elif val == "🔕":
            return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
        return ""

    # Application des styles
    styled_df = filtered_df.style.applymap(color_estimation, subset=['Estimation']) \
                                 .applymap(color_market, subset=['Marché']) \
                                 .applymap(color_new_ao, subset=['is_new'])

    st.dataframe(styled_df, use_container_width=True)

    # Section de téléchargement
    st.subheader("3️⃣ Télécharger les Résultats")
    excel_buffer = io.BytesIO()
    filtered_df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)

    st.download_button(
        label="📥 Télécharger les résultats en Excel",
        data=excel_buffer,
        file_name=f"Appels_Offres_Filtrés_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("ℹ️ Veuillez lancer le scraping ou charger les données pour commencer.")





