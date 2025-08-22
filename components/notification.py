# components.py
import streamlit as st
import logging
def render_notification():
    """Affiche une notification avec le nombre d'AO nouveaux"""
    if "num_new_ao" in st.session_state and st.session_state["num_new_ao"] >= 0:
        logging.info(f"Notification: {st.session_state['num_new_ao']} nouveaux appels d'offres détectés.")
        st.markdown(
            f"""
            <div 
                style="
                    background-color:#2563EB;
                    padding:10px;
                    border-radius:8px;
                    margin-bottom:10px;
                    max-width: 30%;
                "
            >
                🔔 <b>{st.session_state['num_new_ao']} nouveaux appels d'offres détectés</b>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        logging.info("Aucun nouvel appel d'offres détecté.")
