import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# Configuration de la page
st.set_page_config(
    page_title="Marsa Maroc - Optimisation Yard",
    page_icon="image.png",
    layout="wide"
)

# --- Configuration du Mode Live (Auto-Refresh) ---
# Si le mode live est activé, la page se recharge toutes les 2 secondes (2000 ms)
live_mode = st.sidebar.checkbox("Activer le Streaming Live", value=False, help="Cochez pour voir les conteneurs s'empiler en direct.")
if live_mode:
    st_autorefresh(interval=2000, limit=None, key="data_streaming")


# Constantes API
API_URL = "http://127.0.0.1:8000"

# Initialiser la variable d'état pour le dernier conteneur placé
if 'last_placed' not in st.session_state:
    st.session_state.last_placed = None
    
st.title("🏗️ Tableau de Bord - Optimisation du Yard")



# --- BARRE LATÉRALE ---
st.sidebar.header("Configuration du Yard")
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

# --- Housekeeping (Tabu Search) ---
st.sidebar.header("🔧 Housekeeping (Off-Peak)")
st.sidebar.caption("Réorganise le yard pour éliminer les rehandles existants.")

if st.sidebar.button("▶ Lancer le Tabu Search", use_container_width=True, type="primary"):
    with st.sidebar:
        with st.spinner("Tabu Search en cours..."):
            try:
                hk_resp = requests.post(f"{API_URL}/yard/housekeeping", json={
                    "max_iterations": 200,
                    "tabu_tenure": 15,
                    "max_no_improve": 50,
                })
                if hk_resp.status_code == 200:
                    hk = hk_resp.json()
                    if hk["rehandles_reduced"] > 0:
                        st.success(f"✅ {hk['rehandles_reduced']} rehandle(s) éliminé(s) en {hk['moves_made']} mouvements")
                        col_a, col_b = st.columns(2)
                        col_a.metric("Avant", hk["initial_rehandles"], delta=None)
                        col_b.metric("Après", hk["final_rehandles"],
                                     delta=f"-{hk['rehandles_reduced']}", delta_color="inverse")
                        st.progress(hk["improvement_pct"] / 100,
                                    text=f"Amélioration : {hk['improvement_pct']}%")
                    else:
                        st.info("✅ Yard déjà optimal — aucun rehandle détecté.")
                else:
                    st.error(f"Erreur API : {hk_resp.text}")
            except requests.exceptions.ConnectionError:
                st.error("🚨 API non accessible.")

st.sidebar.divider()

st.sidebar.header(" Nouveau Conteneur")
with st.sidebar.form("placement_form"):
    # Définition des zones dédiées
    st.markdown("**Zones Dédiées (Optionnel)**")
    
    zones_20ft = st.multiselect("Blocs 20ft", options=["A", "B", "C", "D"], default=["A", "B"])
    zones_40ft = st.multiselect("Blocs 40ft", options=["A", "B", "C", "D"], default=["C", "D"])
    
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
        "departure_time": departure_dt,
        "zones_20ft": zones_20ft if c_size == 20 else [],
        "zones_40ft": zones_40ft if c_size == 40 else []
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
st.header("État actuel du Yard")

if st.button(" Rafraîchir les données"):
    with st.spinner("Réinitialisation du Yard..."):
        try:
            requests.post(
                f"{API_URL}/yard/init", 
                json={"blocks": 4, "rows": 10, "max_height": 4} # Valeurs par défaut ou on pourrait réutiliser les valeurs actuelles
            )
            st.session_state.last_placed = None
        except Exception as e:
            pass
    st.rerun()

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
        
        # Filtre par bloc
        blocks = [b['block_id'] for b in yard_data['blocks']]
        selected_block = st.selectbox("Sélectionner un Bloc à visualiser :", blocks)
        
        # Trouver les données du bloc sélectionné
        block_data = next((b for b in yard_data['blocks'] if b['block_id'] == selected_block), None)
        
        if block_data:
            fig = go.Figure()

            def add_cube_trace(fig, x_coords, y_coords, z_coords, color, name, hover_texts):
                """Ajoute un groupe de conteneurs comme un seul Mesh3d pour la performance."""
                if not x_coords: return
                
                X, Y, Z, I, J, K = [], [], [], [], [], []
                # Ajuster la taille des cubes pour laisser un petit espace entre eux
                dx, dy, dz = 0.8, 0.8, 0.9 
                
                for idx, (x, y, z) in enumerate(zip(x_coords, y_coords, z_coords)):
                    offset = idx * 8
                    X.extend([x, x+dx, x+dx, x, x, x+dx, x+dx, x])
                    Y.extend([y, y, y+dy, y+dy, y, y, y+dy, y+dy])
                    Z.extend([z, z, z, z, z+dz, z+dz, z+dz, z+dz])
                    
                    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
                    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
                    k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]
                    
                    I.extend([v + offset for v in i])
                    J.extend([v + offset for v in j])
                    K.extend([v + offset for v in k])
                
                # Formatage du hovertext : Répéter chaque texte 8 fois (pour les 8 sommets de chaque cube)
                formatted_hover_texts = []
                for t in hover_texts:
                    formatted_hover_texts.extend([t] * 8)

                mesh = go.Mesh3d(
                    x=X, y=Y, z=Z,
                    i=I, j=J, k=K,
                    color=color,
                    opacity=0.9,
                    flatshading=True,
                    name=name,
                    showscale=False,
                    text=formatted_hover_texts,
                    hoverinfo='text' if hover_texts else 'name'
                )
                fig.add_trace(mesh)

            # Séparer les conteneurs normaux du "dernier placé" pour les colorer différemment
            last_placed = st.session_state.last_placed
            
            x_norm, y_norm, z_norm, text_norm = [], [], [], []
            x_last, y_last, z_last, text_last = [], [], [], []
            
            for stack in block_data['stacks']:
                slots = stack.get('slots', [])
                for s in slots:
                    if not s.get('is_free'):
                        tier_index = s['tier'] - 1 # 0-indexed for 3D coordinates
                        row_index = stack['row'] - 1 # 0-indexed
                        
                        # Assembler le texte de survol
                        hover_info = f"<b>{s.get('container_id', 'Inconnu')}</b><br>"
                        details = s.get('container_details')
                        if details:
                            hover_info += f"Type: {details.get('type')}<br>"
                            hover_info += f"Taille: {details.get('size')}ft<br>"
                            hover_info += f"Poids: {details.get('weight')}t<br>"
                            hover_info += f"Départ: {details.get('departure_time')}"
                        else:
                            hover_info += "<i>(Détails non disponibles)</i>"

                        is_last = False
                        if last_placed and last_placed['block'] == selected_block:
                            if last_placed['row'] == stack['row'] and last_placed['tier'] == s['tier']:
                                is_last = True
                                
                        if is_last:
                            x_last.append(row_index)
                            y_last.append(0)
                            z_last.append(tier_index)
                            text_last.append(hover_info)
                        else:
                            x_norm.append(row_index)
                            y_norm.append(0)
                            z_norm.append(tier_index)
                            text_norm.append(hover_info)

            # Ajouter tous les conteneurs normaux
            add_cube_trace(fig, x_norm, y_norm, z_norm, color='#2ca02c', name=f'Conteneurs', hover_texts=text_norm)
            
            # Ajouter le dernier conteneur en évidence (Rouge)
            if x_last:
                add_cube_trace(fig, x_last, y_last, z_last, color='#d62728', name='Nouveau Conteneur', hover_texts=text_last)
                st.info(f"👉 Le dernier conteneur vient d'être posé en rouge (Bloc {last_placed['block']}, Rangée {last_placed['row']}, Hauteur {last_placed['tier']}).")

            # Dessiner le sol du bloc pour le repère visuel
            max_r = yard_data['n_rows']
            fig.add_trace(go.Mesh3d(
                x=[-0.5, max_r-0.5, max_r-0.5, -0.5],
                y=[-0.5, -0.5, 1.5, 1.5],
                z=[0, 0, 0, 0],   
                i=[0, 0], j=[1, 2], k=[2, 3],
                color='gray', opacity=0.3, name='Sol', hoverinfo='skip'
            ))

            fig.update_layout(
                scene=dict(
                    xaxis=dict(title='Rangée', range=[-1, yard_data['n_rows']], dtick=1),
                    yaxis=dict(title='', range=[-1, 2], showticklabels=False), # Cacher l'axe Y (un seul bloc)
                    zaxis=dict(title='Niveau', range=[0, yard_data['max_height'] + 1], dtick=1),
                    aspectmode='manual',
                    aspectratio=dict(x=2, y=0.5, z=1) # Allonger selon les rangées
                ),
                title=f"Vue 3D - Bloc {selected_block}",
                margin=dict(l=0, r=0, b=0, t=40)
            )

            st.plotly_chart(fig, use_container_width=True)
        
        # --- Liste détaillée des blocs ---
        with st.expander("Voir les détails chiffrés par bloc"):
            for block in yard_data['blocks']:
                st.markdown(f"**Bloc {block['block_id']}** — Occupation : {block['occupancy']*100:.1f}%")

except requests.exceptions.ConnectionError:
    st.warning("⚠️ L'API n'est pas accessible. Lancez `python main.py api` pour afficher les données du yard.")


