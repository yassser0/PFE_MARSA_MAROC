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

# --- VUE PRINCIPALE ---
tabs = st.tabs(["🏗️ Vue Globale 3D", "🔍 Vue Détail Bloc", "📊 Statistiques"])

try:
    response = requests.get(f"{API_URL}/yard")
    if response.status_code == 200:
        yard_data = response.json()
        
        # Helper pour ajouter des cubes
        def add_cube_trace(fig, x_coords, y_coords, z_coords, color, name, hover_texts, offset=(0,0)):
            if not x_coords: return
            X, Y, Z, I, J, K = [], [], [], [], [], []
            dx, dy, dz = 0.8, 0.8, 0.9 
            ox, oy = offset
            for idx, (x, y, z) in enumerate(zip(x_coords, y_coords, z_coords)):
                ax, ay = x + ox, y + oy # Apply spatial offset
                offset_idx = idx * 8
                X.extend([ax, ax+dx, ax+dx, ax, ax, ax+dx, ax+dx, ax])
                Y.extend([ay, ay, ay+dy, ay+dy, ay, ay, ay+dy, ay+dy])
                Z.extend([z, z, z, z, z+dz, z+dz, z+dz, z+dz])
                i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
                j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
                k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]
                I.extend([v + offset_idx for v in i]); J.extend([v + offset_idx for v in j]); K.extend([v + offset_idx for v in k])
            
            formatted_hover_texts = []
            for t in hover_texts: formatted_hover_texts.extend([t] * 8)
            mesh = go.Mesh3d(
                x=X, y=Y, z=Z, i=I, j=J, k=K, color=color, opacity=0.9,
                flatshading=True, name=name, showscale=False,
                text=formatted_hover_texts, hoverinfo='text' if hover_texts else 'name'
            )
            fig.add_trace(mesh)

        # --- TAB 1 : VUE GLOBALE 3D ---
        with tabs[0]:
            st.subheader("Terminal à Conteneurs - Vue 3D Réaliste (TC3)")
            st.caption("Visualisation de l'ensemble du parc selon la disposition réelle.")
            
            fig_global = go.Figure()
            last_placed = st.session_state.last_placed
            
            for block in yard_data['blocks']:
                # Coordonnées du bloc
                bx, by = block['x'], block['y']
                
                # Dessiner le sol du bloc
                bw, bl = block['width'], block['length']
                fig_global.add_trace(go.Mesh3d(
                    x=[bx, bx+bw, bx+bw, bx], y=[by, by, by+bl, by+bl], z=[0, 0, 0, 0],   
                    i=[0, 0], j=[1, 2], k=[2, 3], color='gray', opacity=0.1, hoverinfo='skip'
                ))
                
                # Ajouter l'ID du bloc
                fig_global.add_trace(go.Scatter3d(
                    x=[bx+bw/2], y=[by+bl/2], z=[yard_data['max_height'] + 1],
                    mode='text', text=[f"Bloc {block['block_id']}"],
                    textfont=dict(color="white", size=10), showlegend=False
                ))

                x_norm, y_norm, z_norm, text_norm = [], [], [], []
                x_last, y_last, z_last, text_last = [], [], [], []
                
                for stack in block['stacks']:
                    for s in stack.get('slots', []):
                        if not s.get('is_free'):
                            tier_idx = s['tier'] - 1
                            # Dans le bloc, x=row, y=0 (on pourrait améliorer le positionnement interne)
                            # On distribue les rangées le long de la "length" du bloc
                            row_y_offset = (stack['row'] - 1) * 1.1
                            
                            details = s.get('container_details')
                            hover = f"<b>{s['container_id']}</b><br>Bloc {block['block_id']}, R{stack['row']}, T{s['tier']}"
                            if details:
                                hover += f"<br>Type: {details.get('type')}<br>Taille: {details.get('size')}ft<br>Poids: {details.get('weight')}t<br>Départ: {details.get('departure_time')}"
                            
                            is_recent = last_placed and last_placed['block'] == block['block_id'] and last_placed['row'] == stack['row'] and last_placed['tier'] == s['tier']
                            
                            if is_recent:
                                x_last.append(0); y_last.append(row_y_offset); z_last.append(tier_idx); text_last.append(hover)
                            else:
                                x_norm.append(0); y_norm.append(row_y_offset); z_norm.append(tier_idx); text_norm.append(hover)
                
                add_cube_trace(fig_global, x_norm, y_norm, z_norm, color='#2ca02c', name=f'B-{block["block_id"]}', hover_texts=text_norm, offset=(bx, by))
                if x_last:
                    add_cube_trace(fig_global, x_last, y_last, z_last, color='#d62728', name='Nouveau', hover_texts=text_last, offset=(bx, by))

            fig_global.update_layout(
                scene=dict(
                    xaxis=dict(title="X (m)", backgroundcolor="rgb(20, 20, 20)"),
                    yaxis=dict(title="Y (m)", backgroundcolor="rgb(20, 20, 20)"),
                    zaxis=dict(title="Niveau", range=[0, yard_data['max_height'] + 2]),
                    aspectmode='data'
                ),
                margin=dict(l=0, r=0, b=0, t=0), height=700,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_global, use_container_width=True)

        # --- TAB 2 : VUE DÉTAIL BLOC ---
        with tabs[1]:
            st.subheader("Détails d'un Bloc")
            blocks_ids = [b['block_id'] for b in yard_data['blocks']]
            sel_block_id = st.selectbox("Choisir le bloc à inspecter :", blocks_ids)
            
            block_data = next((b for b in yard_data['blocks'] if b['block_id'] == sel_block_id), None)
            if block_data:
                fig_detail = go.Figure()
                x_d, y_d, z_d, t_d = [], [], [], []
                for stack in block_data['stacks']:
                    for s in stack['slots']:
                        if not s['is_free']:
                            x_d.append(stack['row']-1); y_d.append(0); z_d.append(s['tier']-1)
                            details = s.get('container_details')
                            hover = f"<b>{s['container_id']}</b><br>Bloc {sel_block_id}, R{stack['row']}, T{s['tier']}"
                            if details:
                                hover += f"<br>Type: {details.get('type')}<br>Taille: {details.get('size')}ft<br>Poids: {details.get('weight')}t<br>Départ: {details.get('departure_time')}"
                            t_d.append(hover)
                
                add_cube_trace(fig_detail, x_d, y_d, z_d, color='#2ca02c', name='Stack', hover_texts=t_d)
                
                max_r = block_data['n_rows']
                fig_detail.update_layout(
                    scene=dict(
                        xaxis=dict(title='Rangée', range=[-1, max_r]),
                        yaxis=dict(title='', range=[-1, 1], showticklabels=False),
                        zaxis=dict(title='Niveau', range=[0, yard_data['max_height'] + 1]),
                        aspectmode='manual', aspectratio=dict(x=2, y=0.5, z=1)
                    ),
                    margin=dict(l=0, r=0, b=0, t=0), height=500
                )
                st.plotly_chart(fig_detail, use_container_width=True)

        # --- TAB 3 : ANALYTICS ---
        with tabs[2]:
            st.subheader("Performance du Yard")
            k1, k2, k3 = st.columns(3)
            k1.metric("Occupation Globale", f"{yard_data['occupancy_rate']*100:.1f}%")
            k2.metric("Slots Occupés", yard_data['used_slots'])
            k3.metric("Hauteur Moyenne", f"{yard_data['average_stack_height']:.2f}")
            
            occ_df = pd.DataFrame([{"Bloc": b['block_id'], "Occupation": b['occupancy']*100} for b in yard_data['blocks']])
            st.plotly_chart(px.bar(occ_df, x="Bloc", y="Occupation", color="Occupation", color_continuous_scale="RdYlGn_r"))

except requests.exceptions.ConnectionError:
    st.warning("🚨 API non accessible. Veuillez lancer `python main.py api`.")


