import os
import argparse
from generator import generate_mock_data
from engine import ERPAuditEngine
from visualizer import generate_risk_graph
from reporter import generate_pdf_report

def main():
    parser = argparse.ArgumentParser(description="ERP-Guard: Segregation of Duties Audit Engine CLI")
    parser.add_argument("--config", default="./config/sod_rules.json", help="Path to rules config file")
    parser.add_argument("--data-dir", default="./data", help="Directory containing ERP data files")
    parser.add_argument("--output-pdf", default="./data/audit_report.pdf", help="Output path for the PDF report")
    parser.add_argument("--output-csv", default="./data/audit_findings.csv", help="Output path for the CSV findings")
    parser.add_argument("--regenerate", action="store_true", help="Force regeneration of mock ERP data")
    
    args = parser.parse_args()
    
    # 1. Generate data if not exists or requested
    required_files = ["users.csv", "permissions.csv", "transaction_logs.csv", "hr_database.csv"]
    missing_data = any(not os.path.exists(os.path.join(args.data_dir, f)) for f in required_files)
    
    if missing_data or args.regenerate:
        print("Data files missing or --regenerate flag set. Generating mock ERP datasets...")
        generate_mock_data(args.data_dir)
        print("-" * 50)
        
    # 2. Run Audit Engine
    print(f"Initializing ERP-Guard Audit Engine...")
    engine = ERPAuditEngine(args.config, args.data_dir)
    
    print("Running compliance audits across entitlements, transaction logs, and HR active directory...")
    findings_df = engine.run_all_audits()
    
    # Save raw findings to CSV
    findings_df.to_csv(args.output_csv, index=False)
    print(f"Raw findings saved to: {args.output_csv}")
    
    # 3. Generate Graph
    graph_path = os.path.join(args.data_dir, "risk_network.png")
    print("Generating risk network graph...")
    generate_risk_graph(engine, graph_path)
    
    # 4. Generate PDF Report
    print("Compiling compliance report...")
    generate_pdf_report(engine, findings_df, graph_path, args.output_pdf)
    print("-" * 50)
    
    # Print Console Summary
    print("AUDIT EXECUTION COMPLETE - SUMMARY OF FINDINGS:")
    if findings_df.empty:
        print("SUCCESS: No compliance violations detected in this audit cycle.")
    else:
        violations_count = len(findings_df)
        print(f"Total Violations Identified: {violations_count}")
        print("\nBreakdown by Violation Type:")
        print(findings_df["violation_type"].value_counts().to_string())
        
        print("\nBreakdown by Risk Level:")
        print(findings_df["risk_level"].value_counts().to_string())
        
        print("\nUnique Violators:")
        unique_users = findings_df["user_id"].unique()
        print(f"User IDs: {list(unique_users)}")
        
    print("-" * 50)
    print(f"Full PDF Report: {os.path.abspath(args.output_pdf)}")

if __name__ == "__main__":
    main()
