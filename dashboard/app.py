import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Malidata - Dashboard", layout="wide")
st.title("🏥 Malidata - Dashboard Médical")

API_BASE = "http://localhost:8000/api"

tab1, tab2 = st.tabs(["📋 Rapports", "📊 Stats"])

with tab1:
    st.header("Rapports Générés")
    try:
        response = requests.get(f"{API_BASE}/reports/list")
        if response.status_code == 200:
            data = response.json()
            reports = data.get("reports", [])
            
            if reports:
                df = pd.DataFrame(reports)
                st.dataframe(df, use_container_width=True)
                
                selected = st.selectbox("Télécharger", df['filename'].tolist())
                if st.button("Télécharger"):
                    url = f"http://localhost:8000/api/reports/download/{selected}"
                    st.markdown(f"[📥 Télécharger]({url})")
            else:
                st.info("Aucun rapport")
        else:
            st.error("Erreur API")
    except Exception as e:
        st.error(f"Erreur: {e}")

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sessions", "12")
    with col2:
        st.metric("Rapports", "8")

st.sidebar.info("Dashboard Malidata v1.0")
