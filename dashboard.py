import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Configuration de la page
st.set_page_config(
    page_title="Marsa Maroc - Optimisation Yard",
    page_icon="🚢",
    layout="wide"
)

# Constantes API
API_URL = "http://127.0.0.1:8000"

# Initialiser la variable d'état pour le dernier conteneur placé
if 'last_placed' not in st.session_state:
    st.session_state.last_placed = None

st.title("🚢 Tableau de Bord : Optimisation du Container Yard")
st.markdown("Interface utilisateur pour visualiser le parc en 3D et placer de nouveaux conteneurs via l'API.")

# --- BARRE LATÉRALE ---
st.sidebar.header("⚙️ Configuration du Yard")
with st.sidebar.form("config_form"):
    blocks = st.number_input("Nombre de blocs", min_value=1, max_value=20, value=4)
    rows = st.number_input("Nombre de rangées par bloc", min_value=1, max_value=50, value=10)
    height = st.number_input("Hauteur maximum", min_value=1, max_value=8, value=4)
    
    init_btn = st.form_submit_button("Initialiser / Réinitialiser le Yard")

if init_btn:
    with st.spinner("Initialisation du Yard..."):
        try:
            # Appel à la (future) nouvelle route API pour réinitialiser le yard
            response = requests.post(
                f"{API_URL}/yard/init", 
                json={"blocks": blocks, "rows": rows, "max_height": height}
            )
            if response.status_code == 200:
                data = response.json()
                st.sidebar.success(f"✅ {data['message']} (Capacité : {data['total_capacity']})")
                # Réinitialiser le dernier conteneur placé puisqu'on a un nouveau yard
                st.session_state.last_placed = None
            else:
                st.sidebar.error(f"Erreur : {response.json().get('detail', 'Inconnue')}")
        except requests.exceptions.ConnectionError:
            st.sidebar.error("🚨 Impossible de se connecter à l'API.")

st.sidebar.divider()

st.sidebar.header("📦 Nouveau Conteneur")
with st.sidebar.form("placement_form"):
    c_size = st.selectbox("Taille (EVP)", options=[20, 40])
    c_weight = st.slider("Poids (Tonnes)", min_value=5.0, max_value=30.0, value=15.0, step=0.5)
    c_type = st.selectbox("Type", options=["import", "export", "transshipment"])
    
    # Date de départ par défaut : dans 7 jours
    default_date = datetime.now() + timedelta(days=7)
    c_date = st.date_input("Date prévue de départ", value=default_date)
    c_time = st.time_input("Heure", value=datetime.strptime("10:00", "%H:%M").time())
    
    submit = st.form_submit_button("Trouver le meilleur emplacement")

if submit:
    departure_dt = datetime.combine(c_date, c_time).isoformat()
    payload = {
        "size": c_size,
        "weight": c_weight,
        "type": c_type,
        "departure_time": departure_dt
    }
    
    with st.spinner("Analyse par le moteur d'optimisation..."):
        try:
            response = requests.post(f"{API_URL}/containers/place", json=payload)
            if response.status_code == 200:
                data = response.json()
                st.session_state.last_placed = data['best_slot']
                st.success(f"✅ Conteneur {data['container_id']} placé avec succès dans le Bloc {data['best_slot']['block']}, Rangée {data['best_slot']['row']}, Hauteur {data['best_slot']['tier']} !")
                
                # Afficher les détails du placement
                col1, col2, col3 = st.columns(3)
                col1.metric("Emplacement Optimal", data['best_slot']['position_key'])
                col2.metric("Score Global", round(data['best_score'], 2))
                
                bd = data['score_breakdown']
                col3.metric("Rehandles Estimés", int(bd['rehandle_score'] / 3.0))
                
                with st.expander("Voir le détail du score"):
                    st.json(bd)
            else:
                st.error(f"Erreur : {response.json().get('detail', 'Inconnue')}")
        except requests.exceptions.ConnectionError:
            st.error("🚨 Impossible de se connecter à l'API. Assurez-vous que `python main.py api` tourne en arrière-plan.")

st.divider()

# --- VUE PRINCIPALE : État du Yard ---
st.header("🗺️ État actuel du Yard")

if st.button("🔄 Rafraîchir les données"):
    pass # Re-trigger du script

try:
    response = requests.get(f"{API_URL}/yard")
    if response.status_code == 200:
        yard_data = response.json()
        
        # --- KPIs Globaux ---
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Capacité Totale", f"{yard_data['total_capacity']} slots")
        kpi2.metric("Slots Occupés", yard_data['used_slots'])
        kpi3.metric("Taux d'Occupation", f"{yard_data['occupancy_rate'] * 100:.1f} %")
        kpi4.metric("Hauteur Moyenne", f"{yard_data['average_stack_height']:.2f}")

        # --- Visualisation 3D avec Plotly ---
        st.subheader("Visualisation des Blocs")
        
        # Préparer les données pour le graphique
        plot_data = []
        for block in yard_data['blocks']:
            for stack in block['stacks']:
                # The API returns 'slots' list which contains 'container_id'
                slots = stack.get('slots', [])
                containers_in_stack = [s.get('container_id') for s in slots if not s.get('is_free')]
                container_ids_str = "<br>".join([f"Niv {i+1}: {cid}" for i, cid in enumerate(containers_in_stack)])
                
                plot_data.append({
                    "Bloc": block['block_id'],
                    "Rangée": stack['row'],
                    "Hauteur": stack['current_height'],
                    "Max": stack['max_height'],
                    "Conteneurs": container_ids_str if container_ids_str else "Vide"
                })
        
        df = pd.DataFrame(plot_data)
        
        # Filtre par bloc
        blocks = df['Bloc'].unique()
        selected_block = st.selectbox("Sélectionner un Bloc à visualiser :", blocks)
        
        df_block = df[df['Bloc'] == selected_block]
        
        # Graphique en barres 3D simulé / Histogramme
        fig = px.bar(
            df_block, 
            x='Rangée', 
            y='Hauteur', 
            title=f"Hauteur des piles - Bloc {selected_block}",
            labels={'Rangée': 'Numéro de rangée', 'Hauteur': 'Conteneurs empilés'},
            color='Hauteur',
            color_continuous_scale="Viridis",
            range_y=[0, yard_data['max_height'] + 1],
            hover_data={"Conteneurs": True, "Bloc": False, "Max": False}
        )
        # Ajouter une ligne pour la capacité max
        fig.add_hline(y=yard_data['max_height'], line_dash="dash", line_color="red", annotation_text="Hauteur Maximum")
        
        # Mettre en évidence le dernier conteneur placé (si on regarde son bloc)
        last_placed = st.session_state.last_placed
        if last_placed and last_placed['block'] == selected_block:
            fig.add_annotation(
                x=last_placed['row'],
                y=last_placed['tier'],  # pointer vers le haut du conteneur
                text="📍 NOUVEAU",
                showarrow=True,
                arrowhead=2,
                arrowcolor="red",
                arrowsize=1.5,
                arrowwidth=2,
                font=dict(color="red", size=14, family="Arial Black")
            )
            
            # Message informatif pour l'utilisateur
            st.info(f"👉 Le dernier conteneur vient d'être posé à l'emplacement indiqué par la flèche rouge (Bloc {last_placed['block']}, Rangée {last_placed['row']}, Hauteur {last_placed['tier']}).")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # --- Liste détaillée des blocs ---
        with st.expander("Voir les détails chiffrés par bloc"):
            for block in yard_data['blocks']:
                st.markdown(f"**Bloc {block['block_id']}** — Occupation : {block['occupancy']*100:.1f}%")

except requests.exceptions.ConnectionError:
    st.warning("⚠️ L'API n'est pas accessible. Lancez `python main.py api` pour afficher les données du yard.")

st.markdown("---")
st.caption("Projet de Fin d'Études — Optimisation Yard 3D Marsa Maroc")
