"""
Script de test de la pipeline ETL Bronze → Silver → Gold.
Usage : python test_pipeline.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pipeline.etl_pipeline import ETLPipeline

csv_path = os.path.join(os.path.dirname(__file__), "containers_400.csv")

print("=" * 60)
print("  TEST PIPELINE ETL MARSA MAROC")
print("=" * 60)

pipeline = ETLPipeline()
result = pipeline.run(csv_path)

print("\n--- RÉSULTATS ---")
print("Status:", result["pipeline_status"])

if result.get("bronze_report"):
    br = result["bronze_report"]
    print(f"[BRONZE] {br['total_rows_ingested']} lignes ingérées")

if result.get("silver_report"):
    sr = result["silver_report"]
    print(f"[SILVER] {sr['total_cleaned']}/{sr['total_raw']} valides (qualité: {sr['quality_score']}%)")
    print(f"         Doublons: {sr['duplicates_removed']}, Nulles: {sr['invalid_nulls_removed']}, Domaine: {sr['invalid_domain_removed']}")

if result.get("gold_kpis") and result["gold_kpis"].get("type_distribution"):
    gk = result["gold_kpis"]
    print(f"[GOLD]   {gk['total_containers']} conteneurs analysés")
    print("         Distribution par type:")
    for t, info in gk["type_distribution"].items():
        print(f"           - {t}: {info['count']} ({info['percentage']}%)")
    ws = gk.get("weight_stats", {})
    print(f"         Poids — moy: {ws.get('avg_t')}t, min: {ws.get('min_t')}t, max: {ws.get('max_t')}t")

print(f"\nRecords prêts pour placement: {len(result.get('cleaned_records', []))}")
pipeline.stop()
print("\n✅ Test terminé avec succès !")
