import streamlit as st
import requests
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker

# ==========================================
# 1. MODELISATION DE LA BASE DE DONNEES (SUPABASE)
# ==========================================

# Verification de la presence du secret
if "SUPABASE_URL" not in st.secrets:
    st.error("La chaine de connexion Supabase est introuvable. Verifiez votre fichier .streamlit/secrets.toml")
    st.stop()

DATABASE_URL = st.secrets["SUPABASE_URL"]

# SQLAlchemy 1.4+ exige 'postgresql://' et refuse l'ancien format 'postgres://' parfois fourni par defaut
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Creation du moteur (Supabase utilise souvent un pooler, pool_pre_ping evite les deconnexions intempestives)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
Base = declarative_base()


class ReleveMeteo(Base):
    __tablename__ = 'releves_meteo'

    id = Column(Integer, primary_key=True)
    ville = Column(String, nullable=False)
    date_heure = Column(String, nullable=False)
    temperature = Column(Float, nullable=False)
    humidite = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint('ville', 'date_heure', name='uix_ville_dateheure'),
    )


# Cree la table dans Supabase si elle n'existe pas encore
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ==========================================
# 2. LOGIQUE D'AUTOMATISATION ET DONNEES
# ==========================================
VILLES_CIBLES = [
    {"nom": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"nom": "Londres", "lat": 51.5074, "lon": -0.1278},
    {"nom": "New York", "lat": 40.7128, "lon": -74.0060},
    {"nom": "Tokyo", "lat": 35.6762, "lon": 139.6503},
    {"nom": "Sydney", "lat": -33.8688, "lon": 151.2093},
    {"nom": "Dubai", "lat": 25.2048, "lon": 55.2708},
    {"nom": "Rio", "lat": -22.9068, "lon": -43.1729}
]


def synchroniser_ville(index_ville):
    if index_ville >= len(VILLES_CIBLES):
        return False, "Toutes les villes de la liste ont ete synchronisees."

    ville = VILLES_CIBLES[index_ville]

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": ville["lat"],
        "longitude": ville["lon"],
        "hourly": "temperature_2m,relative_humidity_2m",
        "timezone": "auto",
        "forecast_days": 1  # On recupere les 24h a venir
    }

    reponse = requests.get(url, params=params)
    if reponse.status_code != 200:
        return False, "Erreur de connexion a l'API Open-Meteo"

    donnees = reponse.json().get("hourly", {})
    temps = donnees.get("time", [])
    temperatures = donnees.get("temperature_2m", [])
    humidites = donnees.get("relative_humidity_2m", [])

    session = Session()
    nouveaux = 0
    doublons = 0

    # Insertion des donnees horaires
    for i in range(len(temps)):
        horodatage = temps[i]
        temp = temperatures[i]
        hum = humidites[i]

        existe = session.query(ReleveMeteo).filter_by(
            ville=ville["nom"],
            date_heure=horodatage
        ).first()

        if existe:
            doublons += 1
        else:
            nouveau = ReleveMeteo(
                ville=ville["nom"],
                date_heure=horodatage,
                temperature=temp,
                humidite=hum
            )
            session.add(nouveau)
            nouveaux += 1

    session.commit()
    session.close()
    return True, f"Extraction terminee pour {ville['nom']} : {nouveaux} ajouts, {doublons} ignores."


# ==========================================
# 3. INTERFACE UTILISATEUR (DASHBOARD)
# ==========================================
st.set_page_config(layout="wide", page_title="Dashboard Meteo")

st.title("Observatoire Meteorologique International")
st.write("Ce tableau de bord agrege les previsions horaires. Ajoutez de nouvelles villes pour enrichir l'analyse.")

# Initialisation du pointeur d'index pour savoir quelle ville extraire
if 'index_ville' not in st.session_state:
    st.session_state.index_ville = 0

# --- PANNEAU LATERAL (CONTROLES) ---
st.sidebar.header("Collecte de donnees")

if st.session_state.index_ville < len(VILLES_CIBLES):
    prochaine_ville = VILLES_CIBLES[st.session_state.index_ville]["nom"]
    st.sidebar.write(f"Ville : **{prochaine_ville}**")
else:
    st.sidebar.write("Toutes les cibles sont atteintes.")

if st.sidebar.button("Collecter la ville suivante", use_container_width=True):
    with st.spinner("Connexion a l'API..."):
        succes, message = synchroniser_ville(st.session_state.index_ville)
        if succes:
            st.sidebar.success(message)
            st.session_state.index_ville += 1
        else:
            st.sidebar.error(message)

st.sidebar.divider()

if st.sidebar.button("Reinitialiser la base de donnees", type="primary", use_container_width=True):
    session = Session()
    session.query(ReleveMeteo).delete()
    session.commit()
    session.close()
    st.session_state.index_ville = 0
    st.rerun()

# --- CORPS DU DASHBOARD ---
session = Session()
enregistrements = session.query(ReleveMeteo).all()
session.close()

if not enregistrements:
    st.info("La base de donnees est vide. Utilisez le panneau lateral pour commencer la collecte.")
else:
    df = pd.DataFrame([
        {
            "Ville": r.ville,
            "Date/Heure": r.date_heure,
            "Temperature (°C)": r.temperature,
            "Humidite (%)": r.humidite
        }
        for r in enregistrements
    ])

    # Formatage de la date pour un meilleur affichage
    df['Date/Heure'] = pd.to_datetime(df['Date/Heure'])

    # 1. Indicateurs cles
    st.subheader("Apercu global")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Lignes en base", len(df))
    col2.metric("Villes couvertes", df["Ville"].nunique())
    col3.metric("Temp. Maximale", f"{df['Temperature (°C)'].max()} °C")
    col4.metric("Temp. Minimale", f"{df['Temperature (°C)'].min()} °C")

    st.divider()

    # 2. Zone d'analyse avec filtres
    col_filtre, col_vide = st.columns([1, 2])
    with col_filtre:
        villes_dispo = df["Ville"].unique()
        villes_selectionnees = st.multiselect(
            "Filtrer l'affichage par ville :",
            options=villes_dispo,
            default=villes_dispo
        )

    df_filtre = df[df["Ville"].isin(villes_selectionnees)]

    if not df_filtre.empty:
        # 3. Visualisations
        col_graph1, col_graph2 = st.columns(2)

        with col_graph1:
            st.subheader("Evolution des Temperatures (24h)")
            # Pivot pour avoir une colonne par ville afin que le line_chart fasse plusieurs courbes
            df_pivot_temp = df_filtre.pivot(index='Date/Heure', columns='Ville', values='Temperature (°C)')
            st.line_chart(df_pivot_temp)

        with col_graph2:
            st.subheader("Evolution de l'Humidite (24h)")
            df_pivot_hum = df_filtre.pivot(index='Date/Heure', columns='Ville', values='Humidite (%)')
            st.line_chart(df_pivot_hum)

        # 4. Tableau detaille
        st.subheader("Donnees brutes")
        st.dataframe(df_filtre.sort_values(by=["Date/Heure", "Ville"]), use_container_width=True, hide_index=True)
    else:
        st.warning("Aucune ville selectionnee.")
