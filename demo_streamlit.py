import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
st.set_page_config(page_title="Démo Streamlit", layout="wide", page_icon="📊")

st.title("📊 Démo interactive — Streamlit")
st.caption("Explorez les données en temps réel, sans recharger la page.")

# ─────────────────────────────────────────
# DONNÉES FICTIVES
# ─────────────────────────────────────────
np.random.seed(42)
n = 200

df = pd.DataFrame({
    "age":      np.random.randint(18, 75, n),
    "revenu":   np.random.normal(2500, 800, n).round(0),
    "score":    np.random.normal(70, 15, n).round(1),
    "ville":    np.random.choice(["Paris", "Lyon", "Marseille", "Bordeaux", "Lille"], n),
    "genre":    np.random.choice(["Homme", "Femme"], n),
})

# ─────────────────────────────────────────
# SIDEBAR — FILTRES
# ─────────────────────────────────────────
st.sidebar.header("🔧 Filtres")

villes = st.sidebar.multiselect(
    "Villes",
    options=df["ville"].unique(),
    default=df["ville"].unique()
)

age_min, age_max = st.sidebar.slider(
    "Tranche d'âge",
    int(df["age"].min()),
    int(df["age"].max()),
    (25, 60)
)

genre_filtre = st.sidebar.radio("Genre", ["Tous", "Homme", "Femme"])

# Application des filtres
df_f = df[
    (df["ville"].isin(villes)) &
    (df["age"].between(age_min, age_max))
]
if genre_filtre != "Tous":
    df_f = df_f[df_f["genre"] == genre_filtre]

# ─────────────────────────────────────────
# MÉTRIQUES
# ─────────────────────────────────────────
st.subheader("Vue d'ensemble")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Personnes", len(df_f), delta=f"{len(df_f) - len(df)} vs total")
c2.metric("Âge moyen", f"{df_f['age'].mean():.1f} ans")
c3.metric("Revenu moyen", f"{df_f['revenu'].mean():.0f} €")
c4.metric("Score moyen", f"{df_f['score'].mean():.1f}")

st.divider()

# ─────────────────────────────────────────
# SECTION GRAPHIQUES — BOUTONS DE CHOIX
# ─────────────────────────────────────────
st.subheader("Choisissez un graphique")

col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
with col_btn1:
    btn_histo = st.button("📊 Histogramme — Âge")
with col_btn2:
    btn_bar = st.button("🏙️ Bar chart — Villes")
with col_btn3:
    btn_scatter = st.button("🔵 Scatter — Revenu vs Score")
with col_btn4:
    btn_pie = st.button("🥧 Camembert — Genre")

# Persistance du choix via session_state
if "graphique" not in st.session_state:
    st.session_state.graphique = "histo"

if btn_histo:
    st.session_state.graphique = "histo"
if btn_bar:
    st.session_state.graphique = "bar"
if btn_scatter:
    st.session_state.graphique = "scatter"
if btn_pie:
    st.session_state.graphique = "pie"

# Affichage du graphique sélectionné
fig, ax = plt.subplots(figsize=(10, 4))

if st.session_state.graphique == "histo":
    ax.hist(df_f["age"], bins=20, color="#E8624A", edgecolor="white")
    ax.set_title("Distribution des âges")
    ax.set_xlabel("Âge")
    ax.set_ylabel("Fréquence")

elif st.session_state.graphique == "bar":
    counts = df_f["ville"].value_counts()
    ax.bar(counts.index, counts.values, color="#4A90D9", edgecolor="white")
    ax.set_title("Nombre de personnes par ville")
    ax.set_ylabel("Nombre")

elif st.session_state.graphique == "scatter":
    colors = df_f["genre"].map({"Homme": "#4A90D9", "Femme": "#E8624A"})
    ax.scatter(df_f["revenu"], df_f["score"], alpha=0.5, c=colors, edgecolors="none")
    ax.set_title("Revenu vs Score (bleu = Homme, rouge = Femme)")
    ax.set_xlabel("Revenu (€)")
    ax.set_ylabel("Score")

elif st.session_state.graphique == "pie":
    counts = df_f["genre"].value_counts()
    ax.pie(counts, labels=counts.index, autopct="%1.1f%%",
           colors=["#4A90D9", "#E8624A"], startangle=90)
    ax.set_title("Répartition par genre")

st.pyplot(fig)

st.divider()

# ─────────────────────────────────────────
# TABLEAU INTERACTIF
# ─────────────────────────────────────────
with st.expander("📋 Voir les données filtrées"):
    st.dataframe(df_f.reset_index(drop=True), use_container_width=True)
    st.caption(f"{len(df_f)} lignes affichées")

# ─────────────────────────────────────────
# ZONE DE CALCUL EN DIRECT
# ─────────────────────────────────────────
st.subheader("🔢 Calcul en direct")

col_a, col_b = st.columns(2)
with col_a:
    seuil_revenu = st.number_input("Seuil de revenu (€)", value=2500, step=100)
with col_b:
    pct = (df_f["revenu"] >= seuil_revenu).mean() * 100
    st.metric(
        f"Personnes avec revenu ≥ {seuil_revenu} €",
        f"{pct:.1f} %",
        help="Recalculé instantanément à chaque changement"
    )