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
perf_mode = st.sidebar.checkbox("Mode Performance 3D", value=False, help="Dessine des points légers au lieu de cubes complexes. Recommandé pour tester avec > 500 conteneurs.")
if live_mode:
    st_autorefresh(interval=2000, limit=None, key="data_streaming")


# Constantes API
API_URL = "http://127.0.0.1:8000"

# Initialiser les variables d'état pour la navigation
if 'last_placed' not in st.session_state:
    st.session_state.last_placed = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Vue Globale 3D"
if 'selected_block' not in st.session_state:
    st.session_state.selected_block = "A"

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Global Theme Overrides */
    .stApp {
        background-color: #0E1117;
    }
    
    /* KPI Cards - Glassmorphism */
    .kpi-card {
        background: rgba(30, 35, 45, 0.7);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-5px);
        border: 1px solid rgba(44, 160, 44, 0.5); /* Highlight on hover */
    }
    .kpi-title {
        color: #8B949E;
        font-size: 0.9rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }
    .kpi-value {
        color: #FFFFFF;
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }
    .kpi-delta {
        font-size: 0.85rem;
        margin-top: 5px;
    }
    .delta-up { color: #2ca02c; }
    .delta-down { color: #d62728; }
    
    /* Styling for the Placement Result Box */
    .placement-success {
        background: rgba(44, 160, 44, 0.1);
        border-left: 4px solid #2ca02c;
        padding: 15px;
        border-radius: 4px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("Marsa Maroc - Yard Intelligence")

# --- FETCH GLOBAL DATA EARLY FOR HEADER KPIS ---
yard_data = None
try:
    import time as _time
    # Ajout d'un paramètre timestamp pour forcer le contournement du cache (cache-buster)
    resp = requests.get(f"{API_URL}/yard?_t={_time.time()}")
    if resp.status_code == 200:
        yard_data = resp.json()
except requests.exceptions.ConnectionError:
    st.error("🚨 API non accessible. Veuillez lancer `python main.py api`.")

# --- GLOBAL KPI HEADER ---
if yard_data:
    kpi_cols = st.columns(4)
    
    with kpi_cols[0]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Occupation Globale</div>
            <div class="kpi-value">{yard_data['occupancy_rate']*100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_cols[1]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Slots Occupés</div>
            <div class="kpi-value">{yard_data['used_slots']}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_cols[2]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Capacité Totale</div>
            <div class="kpi-value">{yard_data['total_capacity']}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_cols[3]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Hauteur Moyenne</div>
            <div class="kpi-value">{yard_data['average_stack_height']:.1f}</div>
        </div>
        """, unsafe_allow_html=True)


# --- BARRE LATÉRALE ---
st.sidebar.header("Configuration du Yard")
with st.sidebar.form("config_form"):
    blocks = st.number_input("Nombre de blocs", min_value=1, max_value=20, value=4)
    bays = st.number_input("Nombre de bays par bloc", min_value=1, max_value=50, value=10)
    rows = st.number_input("Nombre de rangées par bloc", min_value=1, max_value=50, value=3)
    height = st.number_input("Hauteur maximum", min_value=1, max_value=8, value=4)
    
    init_btn = st.form_submit_button("Initialiser / Réinitialiser le Yard")

if init_btn:
    with st.spinner("Initialisation du Yard..."):
        try:
            # Appel à la (future) nouvelle route API pour réinitialiser le yard
            response = requests.post(
                f"{API_URL}/yard/init", 
                json={"blocks": blocks, "bays": bays, "rows": rows, "max_height": height}
            )
            if response.status_code == 200:
                data = response.json()
                st.sidebar.success(f"✅ {data['message']} (Capacité : {data['total_capacity']})")
                # Réinitialiser le dernier conteneur placé puisqu'on a un nouveau yard
                st.session_state.last_placed = None
                st.rerun() # Rafraîchissement automatique après initialisation
            else:
                st.sidebar.error(f"Erreur : {response.json().get('detail', 'Inconnue')}")
        except requests.exceptions.ConnectionError:
            st.sidebar.error("🚨 Impossible de se connecter à l'API.")

if st.sidebar.button("Vider le Yard & Actualiser", use_container_width=True, type="primary"):
    with st.spinner("Nettoyage en cours..."):
        try:
            requests.post(f"{API_URL}/yard/init", json={"blocks": 4, "bays": 10, "rows": 3, "max_height": 4})
        except requests.exceptions.ConnectionError:
            pass
    st.session_state.last_placed = None
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

st.sidebar.caption(f"Dernière actualisation : {datetime.now().strftime('%H:%M:%S')}")
st.sidebar.divider()

# --- Housekeeping (Tabu Search) ---
st.sidebar.header("🔧 Housekeeping (Off-Peak)")
st.sidebar.caption("Réorganise le yard pour éliminer les rehandles existants.")

if st.sidebar.button("▶ Lancer le Tabu Search pour Réorganise le yard", use_container_width=True, type="primary"):
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

# --- Recherche de Conteneur ---
st.sidebar.header("🔍 Recherche de Conteneur")
search_input = st.sidebar.text_input("ID ou Localisation (ex: A-B01-R1-T1)", key="search_input")

if search_input:
    # On stocke la recherche dans le session_state pour que la vue 3D puisse l'utiliser
    st.session_state.search_query = search_input.strip().upper()
else:
    st.session_state.search_query = None

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
                st.markdown(f"""
                <div class="placement-success">
                    <h4 style="margin: 0; color: #2ca02c;">✅ Conteneur {data['container_id']} placé avec succès !</h4>
                    <p style="margin: 5px 0 0 0;">Bloc <b>{data['best_slot']['block']}</b> | Rangée <b>{data['best_slot']['row']}</b> | Niveau <b>{data['best_slot']['tier']}</b></p>
                </div>
                """, unsafe_allow_html=True)
                
                # Afficher les détails du placement
                st.write("") # espacement
                col1, col2, col3 = st.columns(3)
                col1.metric("Clé Position", data['best_slot']['position_key'])
                col2.metric("Score Global", round(data['best_score'], 2))
                
                bd = data['score_breakdown']
                col3.metric("Rehandles Estimés", int(bd['rehandle_score'] / 3.0))
                
                with st.expander("📊 Détail Calcul Algorithmique"):
                    st.json(bd)
            else:
                st.error(f"Erreur : {response.json().get('detail', 'Inconnue')}")
        except requests.exceptions.ConnectionError:
            st.error("🚨 Impossible de se connecter à l'API. Assurez-vous que `python main.py api` tourne en arrière-plan.")

st.markdown("---")

if yard_data:
        
        # Helper pour ajouter des cubes
        def add_cube_trace(fig, x_coords, y_coords, z_coords, color, name, hover_texts, offset=(0,0)):
            if not x_coords: return
            
            if perf_mode:
                # Mode Performance (Scatter3d)
                X, Y, Z = [], [], []
                ox, oy = offset
                for x, y, z in zip(x_coords, y_coords, z_coords):
                    X.append(x + ox + 0.4)
                    Y.append(y + oy + 0.4)
                    Z.append(z + 0.45)
                
                scatter = go.Scatter3d(
                    x=X, y=Y, z=Z,
                    mode='markers',
                    marker=dict(symbol='square', size=12, color=color, opacity=0.9),
                    name=name,
                    text=hover_texts,
                    hoverinfo='text' if hover_texts else 'name'
                )
                fig.add_trace(scatter)
                return

            X, Y, Z, I, J, K = [], [], [], [], [], []
            dx, dy, dz = 0.8, 1.3, 0.9 
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

        # --- NAVIGATION ---
        # Comme st.tabs ne permet pas la navigation programmatique, nous utilisons un menu personnalisé
        tabs_list = ["Vue Globale 3D", "Vue Détail Bloc", "Heatmap & Analytique"]
        active_idx = tabs_list.index(st.session_state.active_tab) if st.session_state.active_tab in tabs_list else 0

        # Utilisation de colonnes pour simuler des onglets horizontaux propres
        st.session_state.active_tab = st.radio(
            "Vue Principale", 
            tabs_list, 
            index=active_idx, 
            horizontal=True,
            label_visibility="collapsed"
        )
        st.write("") # Petit espacement

        if st.session_state.active_tab == "Vue Globale 3D":
            st.markdown("### Visualisation du TC3")
            
            
            # Déplacement de la Navigation Rapide au-dessus de la carte pour une meilleure accessibilité UX
            cols = st.columns(len(yard_data['blocks']))
            for i, block in enumerate(yard_data['blocks']):
                with cols[i]:
                    if st.button(f"Inspecter block {block['block_id']}", use_container_width=True, key=f"nav_btn_{block['block_id']}"):
                        st.session_state.selected_block = block['block_id']
                        st.session_state.active_tab = "Vue Détail Bloc"
                        st.rerun()

            fig_global = go.Figure()
            last_placed = st.session_state.last_placed
            
            for block in yard_data['blocks']:
                # Coordonnées du bloc
                bx, by = block['x'], block['y']
                
                # Dessiner le sol du bloc
                bw, bl = block['width'], block['length']
                # Sol du bloc (Mesh3d)
                fig_global.add_trace(go.Mesh3d(
                    x=[bx, bx+bw, bx+bw, bx], y=[by, by, by+bl, by+bl], z=[0.01, 0.01, 0.01, 0.01],   
                    i=[0, 0], j=[1, 2], k=[2, 3], color='gray', opacity=0.1, 
                    hoverinfo='skip',
                    name=f"Sol {block['block_id']}"
                ))

                # Le sol du bloc est cliquable (via le clickmode, même si moins fiable)
                
                # Ajouter l'ID du bloc
                fig_global.add_trace(go.Scatter3d(
                    x=[bx+bw/2], y=[by+bl/2], z=[yard_data['max_height'] + 1],
                    mode='text', text=[f"Bloc {block['block_id']}"],
                    textfont=dict(color="white", size=10), showlegend=False
                ))

                x_norm, y_norm, z_norm, text_norm = [], [], [], []
                x_last, y_last, z_last, text_last = [], [], [], []
                x_search, y_search, z_search, text_search = [], [], [], []
                
                for stack in block['stacks']:
                    for s in stack.get('slots', []):
                        if not s.get('is_free'):
                            tier_idx = s['tier'] - 1
                            row_x_offset = (stack['row'] - 1) * 2.5
                            bay_y_offset = (stack['bay'] - 1) * 1.5
                            
                            details = s.get('container_details')
                            hover = f"<b>{s['container_id']}</b>"
                            if details:
                                hover += f"<br>Type: {details.get('type')}<br>Taille: {details.get('size')}ft<br>Poids: {details.get('weight')}t<br>Départ: {details.get('departure_time')}<br>Localisation: {details.get('location')}"
                            
                            is_recent = last_placed and last_placed['block'] == block['block_id'] and last_placed['bay'] == stack['bay'] and last_placed['row'] == stack['row'] and last_placed['tier'] == s['tier']
                            
                            content = s.get('container_id', '')
                            loc_str = details.get('location', '') if details else ""
                            is_match = st.session_state.search_query and (st.session_state.search_query == content or st.session_state.search_query == loc_str)
                            
                            if is_match:
                                x_search.append(row_x_offset); y_search.append(bay_y_offset); z_search.append(tier_idx); text_search.append(hover)
                            elif is_recent:
                                x_last.append(row_x_offset); y_last.append(bay_y_offset); z_last.append(tier_idx); text_last.append(hover)
                            else:
                                x_norm.append(row_x_offset); y_norm.append(bay_y_offset); z_norm.append(tier_idx); text_norm.append(hover)
                
                add_cube_trace(fig_global, x_norm, y_norm, z_norm, color='#2ca02c', name=f'B-{block["block_id"]}', hover_texts=text_norm, offset=(bx, by))
                if x_last:
                    add_cube_trace(fig_global, x_last, y_last, z_last, color='#d62728', name='Nouveau', hover_texts=text_last, offset=(bx, by))
                if x_search:
                    add_cube_trace(fig_global, x_search, y_search, z_search, color='#00fdff', name='Trouvé', hover_texts=text_search, offset=(bx, by))

            fig_global.update_layout(
                clickmode='event+select',
                scene=dict(
                    xaxis=dict(title="Axe Transversal (X: Rangées)", backgroundcolor="rgba(0,0,0,0)", gridcolor="#333", showbackground=False),
                    yaxis=dict(title="Axe Longitudinal (Y: Bays)", backgroundcolor="rgba(0,0,0,0)", gridcolor="#333", showbackground=False),
                    zaxis=dict(title="Élévation (Z: Niveaux)", range=[0, yard_data['max_height'] + 2], backgroundcolor="rgba(0,0,0,0)", gridcolor="#333", showbackground=False),
                    aspectmode='data'
                ),
                margin=dict(l=0, r=0, b=0, t=0), height=700,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                modebar=dict(bgcolor='rgba(0,0,0,0.5)', color='white')
            )
            
            # Rendu avec capture d'événements
            event = st.plotly_chart(fig_global, use_container_width=True, on_select="rerun", key="global_map")
            
            # Gestion de la redirection au clic
            if event and "selection" in event and event["selection"]["points"]:
                point = event["selection"]["points"][0]
                
                # Récupération sécurisée du customdata (qui peut être une liste ou une valeur simple)
                cd = point.get("customdata")
                clicked_block = None
                
                if isinstance(cd, list) and len(cd) > 0:
                    clicked_block = cd[0]
                elif isinstance(cd, str):
                    clicked_block = cd
                
                if clicked_block and str(clicked_block) in [b['block_id'] for b in yard_data['blocks']]:
                    st.session_state.selected_block = str(clicked_block)
                    st.session_state.active_tab = "Vue Détail Bloc"
                    st.rerun()

        # --- TAB 2 : VUE DÉTAIL BLOC ---
        elif st.session_state.active_tab == "Vue Détail Bloc":
            st.subheader("Détails d'un Bloc")
            blocks_ids = [b['block_id'] for b in yard_data['blocks']]
            
            # Synchroniser le selectbox avec l'état de la session
            default_idx = blocks_ids.index(st.session_state.selected_block) if st.session_state.selected_block in blocks_ids else 0
            st.session_state.selected_block = st.selectbox("Choisir le bloc à inspecter :", blocks_ids, index=default_idx)
            
            block_data = next((b for b in yard_data['blocks'] if b['block_id'] == st.session_state.selected_block), None)
            if block_data:
                fig_detail = go.Figure()
                x_d, y_d, z_d, t_d = [], [], [], []
                xs, ys, zs, ts = [], [], [], [] # for searched
                for stack in block_data['stacks']:
                    for s in stack['slots']:
                        if not s['is_free']:
                            tier_idx = s['tier'] - 1
                            details = s.get('container_details')
                            hover = f"<b>{s['container_id']}</b>"
                            if details:
                                hover += f"<br>Type: {details.get('type')}<br>Taille: {details.get('size')}ft<br>Poids: {details.get('weight')}t<br>Départ: {details.get('departure_time')}<br>Localisation: {details.get('location')}"
                            
                            is_match = st.session_state.search_query and (st.session_state.search_query == s.get('container_id') or (details and st.session_state.search_query == details.get('location')))
                            
                            if is_match:
                                xs.append((stack['row']-1) * 2.5); ys.append((stack['bay']-1) * 1.5); zs.append(tier_idx); ts.append(hover)
                            else:
                                x_d.append((stack['row']-1) * 2.5); y_d.append((stack['bay']-1) * 1.5); z_d.append(tier_idx); t_d.append(hover)
                
                add_cube_trace(fig_detail, x_d, y_d, z_d, color='#2ca02c', name='Piles', hover_texts=t_d)
                if xs:
                    add_cube_trace(fig_detail, xs, ys, zs, color='#00fdff', name='Résultat', hover_texts=ts)

                max_b = yard_data['n_bays']
                max_r = yard_data['n_rows']
                fig_detail.update_layout(
                    scene=dict(
                        xaxis=dict(title='Rangée (X)', range=[-1, max_r * 2.5]),
                        yaxis=dict(title='Bay (Y)', range=[-1, max_b * 1.5]),
                        zaxis=dict(title='Niveau (Z)', range=[0, yard_data['max_height'] + 1]),
                        aspectmode='manual', aspectratio=dict(x=1.5, y=2, z=1)
                    ),
                    margin=dict(l=0, r=0, b=0, t=0), height=500
                )
                st.plotly_chart(fig_detail, use_container_width=True)

        # --- TAB 3 : ANALYTICS ---
        elif st.session_state.active_tab == "Heatmap & Analytique":
            st.markdown("### 📊 Distribution de la Charge")
            
            occ_df = pd.DataFrame([{"Secteur": f"Bloc {b['block_id']}", "Taux d'Occupation (%)": b['occupancy']*100} for b in yard_data['blocks']])
            fig_bar = px.bar(occ_df, x="Secteur", y="Taux d'Occupation (%)", color="Taux d'Occupation (%)", color_continuous_scale="RdYlGn_r", template="plotly_dark")
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.2)', margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_bar, use_container_width=True)


