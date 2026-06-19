# ERP-Guard: Automated Segregation of Duties (SoD) & Audit Engine

An enterprise-grade, compliance-driven auditing pipeline built in Python to programmatically inspect ERP authorization profiles and transactional journals. 

This engine is designed to automate internal controls, satisfy SOX (Sarbanes-Oxley Act) section 404 requirements, support SOC 2 audits, and assist IT audit consultants in discovering operational anomalies, authorization crossovers, and fraud risks.

---

## 1. The Business Problem & Value Proposition

In large enterprise systems (like SAP, Oracle, or NetSuite), **Segregation of Duties (SoD)** is a critical internal control. It dictates that no single individual should have authorization to execute all stages of a high-risk business process. For example, if a employee can both **create a vendor** and **approve payments**, they can execute fictitious vendor fraud.

Historically, auditing these controls required manual reviews of hundreds of database sheets or paying hundreds of thousands of dollars for closed-source GRC software. 

**ERP-Guard** bridges this gap by acting as an automated, platform-agnostic audit engine. It ingests CSV database exports and automatically produces:
*   **Static Entitlements Audit:** Identifies users holding conflicting role memberships.
*   **Transactional Cycle Audit:** Scans logs to find instances where a single user executed both sides of a conflicting process on the same transaction loop.
*   **Account Integrity Audit:** Tracks activity logged by deactivated, unregistered (ghost), or terminated employee accounts.
*   **Split Transaction Audit:** Detects instances where users split purchase orders to bypass individual approval threshold limits (e.g., splitting a $25,000 transaction into three POs under a $10,000 limit).
*   **Department Restriction Audit:** Detects users holding permissions not permitted in their business unit (e.g. Marketing users with General Ledger posting rights).
*   **Risk Network Visualization:** Renders a bipartite graph mapping violating users to conflicting system permissions.
*   **Executive PDF Deliverable:** A formal, styled report detailing risk scores, transaction-level audit trails, and security recommendations.

---

## 2. Project Architecture & Codebase

```
erp-guard-auditor/
│
├── config/
│   └── sod_rules.json           # Declarative JSON rule book defining SoD policies
│
├── data/                        # Ingested ERP database dumps & output artifacts
│   ├── users.csv                # System accounts and assigned roles
│   ├── permissions.csv          # Role-to-technical-transaction mappings
│   ├── transaction_logs.csv     # Chronological log of transaction executions
│   ├── hr_database.csv          # Master HR active directory registry
│   ├── audit_findings.csv       # Raw audit results output (CSV)
│   ├── risk_network.png         # Bipartite network graph visualization of access risk
│   └── audit_report.pdf         # Final client-ready executive PDF report
│
├── src/
│   ├── generator.py             # High-fidelity mock ERP database generator
│   ├── engine.py                # Core Python/Pandas audit logic classes
│   ├── visualizer.py            # Bipartite graph generator using NetworkX
│   └── reporter.py              # ReportLab layout engine for PDF generation
│   └── main.py                  # CLI Coordinator
│
└── tests/
    └── test_engine.py           # Comprehensive pytest suite
```

---

## 3. Declarative Policy Configuration (`sod_rules.json`)
The audit rules are defined declaratively in JSON, allowing auditors to edit rules, change transaction limits, or add restricted departments without altering the Python source code.

```json
{
  "conflicting_permission_pairs": [
    {
      "id": "SOD_01_VENDOR_FRAUD",
      "name": "Vendor Creation & Payment Approval Conflict",
      "permission_a": "AP_CREATE_VENDOR",
      "permission_b": "AP_APPROVE_PAYMENT",
      "risk_level": "CRITICAL"
    }
  ],
  "threshold_rules": {
    "single_approval_limit": 10000.0,
    "split_transaction_detection": {
      "time_window_hours": 24
    }
  }
}
```

---

## 4. Built-in Audit Scenario (Case Study)

To demonstrate the engine's capabilities, `generator.py` creates a mock database with deliberate compliance violations representing real-world audit targets:
1.  **Static SoD Conflict (Alice Smith):** Assigned the role `AP_MANAGER` which inherits both vendor creation and payment approval privileges.
2.  **Transactional Cycle Violation (Bob Johnson):** Created a fictitious vendor (`VEND_999`) and approved a payment of `$12,000` to them within a 2-hour window.
3.  **Terminated User Activity (Charlie Brown):** Logged system configuration changes and log deletions weeks *after* their official termination date.
4.  **Split Transaction Bypassing (David Miller):** Bypassed the `$10,000` single PO approval limit by splitting a `$25,000` procurement into three separate POs ($9,500, $8,500, $7,000) to the same vendor within 24 hours.
5.  **Department Restriction (Eve Davis):** A Marketing department user holding a permission that allows posting General Ledger journal entries (`GL_POST_JOURNAL`).

---

## 5. Installation & Execution

### Prerequisites
*   Python 3.8+

### Setup Environment
1.  Navigate to the project directory:
    ```bash
    cd C:/Users/DELL/.gemini/antigravity/scratch/erp-guard-auditor
    ```
2.  Initialize the virtual environment:
    ```bash
    python -m venv .venv
    ```
3.  Activate the environment:
    *   **Windows (PowerShell):**
        ```powershell
        .venv\Scripts\Activate.ps1
        ```
    *   **Mac/Linux:**
        ```bash
        source .venv/bin/activate
        ```
4.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Run the Auditing Pipeline
To generate the mock data, run the analysis engine, export findings, build the network graph, and compile the final PDF report, execute:
```bash
python src/main.py --regenerate
```

The terminal will print a summary of findings:
```text
AUDIT EXECUTION COMPLETE - SUMMARY OF FINDINGS:
Total Violations Identified: 9

Breakdown by Violation Type:
violation_type
STATIC_SOD                           3
TERMINATED_USER_ACTIVITY             2
TRANSACTION_CYCLE_VIOLATION          1
TRANSACTION_SOD_CROSSOVER            1
SPLIT_TRANSACTION_LIMIT_AVOIDANCE    1
DEPARTMENT_RESTRICTION_VIOLATION     1

Breakdown by Risk Level:
risk_level
HIGH        5
CRITICAL    4
```

### Run Unit Tests
To verify the engine's mathematical and rule parsing logic using pytest:
```bash
pytest tests/
```
