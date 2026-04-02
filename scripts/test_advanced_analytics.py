import os
import csv
from datetime import datetime, timedelta
from pipeline.etl_pipeline import get_pipeline

def create_test_csv(filename):
    now = datetime.now()
    # Dwell Time will be around 4 days and 2 days
    dep1 = (now + timedelta(days=5)).isoformat() # Bottom A
    dep2 = (now + timedelta(days=3)).isoformat() # Top A (OK)
    dep3 = (now + timedelta(days=2)).isoformat() # Bottom B (Blocked by dep4)
    dep4 = (now + timedelta(days=6)).isoformat() # Top B
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'size', 'weight', 'departure_time', 'type', 'slot'])
        # Pile A (OK)
        # Note : Tier 1 (A-01) departs Apr 05, Tier 2 (A-02) departs Apr 03 -> OK (Top departs first)
        writer.writerow(['TEST001', 20, 15.0, dep1, 'import', 'A-001-A-01'])
        writer.writerow(['TEST002', 20, 12.0, dep2, 'import', 'A-001-A-02'])
        # Pile B (Rehandle Risk)
        # Note : Tier 1 (B-01) departs Apr 02, Tier 2 (B-02) departs Apr 06 -> BLOCKED (Bottom wants to leave first)
        writer.writerow(['TEST003', 40, 20.0, dep3, 'export', 'B-001-A-01'])
        writer.writerow(['TEST004', 40, 18.0, dep4, 'export', 'B-001-A-02'])

def test_analytics():
    csv_file = "test_analytics.csv"
    create_test_csv(csv_file)
    
    print("🚀 Lancement de l'ETL avec analyses avancées...")
    pipeline = get_pipeline()
    result = pipeline.run(os.path.abspath(csv_file))
    
    if result["pipeline_status"] == "SUCCESS":
        gold_report = result["gold_kpis"]
        
        print("\n📊 RÉSULTATS ANALYTIQUES :")
        
        # Check Dwell Time
        print(f"⏱️ Dwell Time Moyen (import) : {gold_report['dwell_analytics'].get('import')} jours")
        print(f"⏱️ Dwell Time Moyen (export) : {gold_report['dwell_analytics'].get('export')} jours")
        
        # Check Stacking Efficiency
        adv = gold_report["advanced_analytics"]
        print(f"🏗️ Risques de Rehandle : {adv['rehandle_risk_count']}")
        print(f"🏗️ Score d'Efficacité : {adv['efficiency_score']}%")
        
        if adv['rehandle_risk_count'] > 0:
            print("✅ Succès : Risque de rehandle détecté !")
        else:
            print("❌ Échec : Aucun risque détecté alors que la pile B est mal gerbée.")
            
    else:
        print(f"❌ Erreur Pipeline : {result.get('error')}")

if __name__ == "__main__":
    test_analytics()
