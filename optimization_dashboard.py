import streamlit as st
import pandas as pd
import plotly.express as px
from time import perf_counter

from simulation.simulator import simulate

st.set_page_config(
    page_title="Simulation & Optimisation - Marsa Maroc",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Tableau de Bord : Résultats de Simulation & Optimisation")
st.markdown("Ce tableau de bord permet de lancer une simulation de placement de conteneurs en masse et d'analyser les KPI d'optimisation générés par le système.")

# --- BARRE LATÉRALE ---
st.sidebar.header("⚙️ Paramètres de la Simulation")

with st.sidebar.form("sim_form"):
    n_containers = st.number_input("Nombre de conteneurs à simuler", min_value=10, max_value=5000, value=100, step=10)
    blocks = st.number_input("Nombre de blocs virtuels", min_value=1, max_value=10, value=4, step=1)
    rows = st.number_input("Rangées par bloc", min_value=1, max_value=50, value=10, step=1)
    height = st.number_input("Hauteur maximale (niveaux)", min_value=1, max_value=8, value=4, step=1)
    
    submit = st.form_submit_button("🚀 Lancer la Simulation")

if submit:
    with st.spinner(f"Simulation en cours pour {n_containers} conteneurs..."):
        t0 = perf_counter()
        # Appel à la fonction de simulation backend
        result = simulate(
            n_containers=n_containers,
            blocks=blocks,
            rows=rows,
            max_height=height
        )
        t1 = perf_counter()
        
    st.success(f"✅ Simulation terminée en {t1 - t0:.3f} secondes.")
    
    st.divider()
    
    # --- KPIs ---
    st.header("📈 Indicateurs de Performance (KPIs)")
    
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    # Rehandles en vert si 0, orange/rouge sinon
    rehandles = result.total_rehandles_estimated
    kpi1.metric("🔁 Total Rehandles (estimé)", rehandles, delta="Optimal" if rehandles == 0 else "-À améliorer", delta_color="normal" if rehandles == 0 else "inverse")
    
    kpi2.metric("⏱️ Temps Décision Moyen", f"{result.average_decision_time_ms:.3f} ms")
    kpi3.metric("📦 Taux d'Occupation", f"{result.occupancy_rate * 100:.1f} %")
    kpi4.metric("📈 Hauteur Moyenne", f"{result.average_stack_height:.2f}")
    
    placements_ratio = f"{result.containers_placed} / {result.containers_processed}"
    kpi5.metric("🎯 Placements Réussis", placements_ratio)
    
    if result.failed_placements > 0:
        st.warning(f"⚠️ {result.failed_placements} placements ont échoué (yard probablement plein, augmentez la capacité).")
        
    st.divider()
    
    # --- VISUALISATION DU YARD ---
    st.header("🗺️ État Final du Yard Simulé")
    
    # Construire la vue Plotly pour chaque bloc
    plot_data = []
    
    # Remplissage des données depuis le yard généré
    # result.yard est l'instance TerminalYard
    for block_name, block in result.yard.blocks.items():
        for row in range(1, block.n_rows + 1):
            if row in block.stacks:
                stack = block.stacks[row]
                current_height = stack.current_height
                # Get the container IDs from the stack's slots
                containers_in_stack = [s.container_id for s in stack.slots if not s.is_free]
                container_ids_str = "<br>".join([f"Niv {i+1}: {cid}" for i, cid in enumerate(containers_in_stack)])
            else:
                current_height = 0
                container_ids_str = "Vide"
                
            plot_data.append({
                "Bloc": block_name,
                "Rangée": row,
                "Hauteur": current_height,
                "Conteneurs": container_ids_str
            })
            
    df = pd.DataFrame(plot_data)
    
    if not df.empty:
        tabs = st.tabs([f"Bloc {b}" for b in df['Bloc'].unique()])
        
        for i, block_name in enumerate(df['Bloc'].unique()):
            with tabs[i]:
                df_block = df[df['Bloc'] == block_name]
                
                fig = px.bar(
                    df_block, 
                    x='Rangée', 
                    y='Hauteur', 
                    title=f"Remplissage des Piles - {block_name}",
                    labels={'Rangée': 'Numéro de rangée', 'Hauteur': 'Conteneurs empilés'},
                    color='Hauteur',
                    color_continuous_scale="Tealgrn", # Variation couleur (Teal/Green) pour l'optimisation
                    range_y=[0, height + 1],
                    hover_data={"Conteneurs": True, "Bloc": False}
                )
                fig.add_hline(y=height, line_dash="dash", line_color="red", annotation_text="Capacité Maximum")
                
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée à visualiser (Yard vide).")
        
else:
    st.info("👈 Modifiez les paramètres et cliquez sur 'Lancer la Simulation' pour voir les résultats.")
