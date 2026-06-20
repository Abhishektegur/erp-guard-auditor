import os
import json
import pandas as pd
from datetime import datetime

class ERPAuditEngine:
    def __init__(self, rules_path, data_dir=None, dataframes=None):
        self.rules_path = rules_path
        self.rules = self._load_rules()
        
        if dataframes is not None:
            self.users_df = self.standardize_columns(dataframes.get("users"), "users")
            self.permissions_df = self.standardize_columns(dataframes.get("permissions"), "permissions")
            self.logs_df = self.standardize_columns(dataframes.get("transaction_logs"), "transaction_logs")
            self.hr_df = self.standardize_columns(dataframes.get("hr_database"), "hr_database")
        else:
            self.data_dir = data_dir
            self.users_df = self.standardize_columns(self._load_csv("users.csv"), "users")
            self.permissions_df = self.standardize_columns(self._load_csv("permissions.csv"), "permissions")
            self.logs_df = self.standardize_columns(self._load_csv("transaction_logs.csv"), "transaction_logs")
            self.hr_df = self.standardize_columns(self._load_csv("hr_database.csv"), "hr_database")
            
        self._prepare_data()

    @staticmethod
    def standardize_columns(df, sheet_type):
        """Standardizes input dataframe column headers based on aliases."""
        if df is None or len(df.columns) == 0:
            return df
            
        # Map aliases to standard names
        aliases = {
            "users": {
                "user_id": ["user_id", "user", "userid", "user id", "username", "employee_id", "employee id"],
                "name": ["name", "full name", "employee name", "employee_name"],
                "department": ["department", "dept", "business unit", "bu", "department_name"],
                "role": ["role", "roles", "job role", "profile", "role_name"],
                "status": ["status", "active", "state", "user_status"]
            },
            "permissions": {
                "role": ["role", "roles", "job role", "profile", "role_name"],
                "permission": ["permission", "privilege", "tcode", "transaction", "action", "permission_name"]
            },
            "transaction_logs": {
                "transaction_id": ["transaction_id", "tx_id", "id", "doc_id", "document", "trans_id", "transaction id"],
                "user_id": ["user_id", "user", "userid", "user id", "username"],
                "action": ["action", "operation", "activity", "tcode", "permission"],
                "amount": ["amount", "value", "cost", "total", "amount_value"],
                "related_id": ["related_id", "related", "vendor_id", "vendor", "po_id", "document_id", "related id"],
                "timestamp": ["timestamp", "time", "date", "datetime", "transaction_date"]
            },
            "hr_database": {
                "employee_id": ["employee_id", "employee id", "id", "user_id", "user id", "username", "emp_id"],
                "name": ["name", "full name", "employee name", "employee_name"],
                "department": ["department", "dept", "business unit", "bu"],
                "status": ["status", "active", "state", "employee_status"],
                "termination_date": ["termination_date", "term_date", "resign_date", "exit_date", "termination date"]
            }
        }
        
        if sheet_type not in aliases:
            return df
            
        mapping = {}
        # Convert df columns to lowercase strings for matching
        df_cols_lower = {str(c).lower().strip(): c for c in df.columns}
        
        for std_col, list_aliases in aliases[sheet_type].items():
            for alias in list_aliases:
                if alias.lower() in df_cols_lower:
                    orig_col = df_cols_lower[alias.lower()]
                    mapping[orig_col] = std_col
                    break
                    
        return df.rename(columns=mapping)

    def _load_rules(self):
        with open(self.rules_path, "r") as f:
            return json.load(f)

    def _load_csv(self, filename):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required audit dataset not found: {path}")
        return pd.read_csv(path)

    def _prepare_data(self):
        # Convert timestamps in logs to datetime objects
        if "timestamp" in self.logs_df.columns:
            self.logs_df["timestamp"] = pd.to_datetime(self.logs_df["timestamp"])
        
        # Convert termination dates in HR to datetime
        if "termination_date" in self.hr_df.columns:
            self.hr_df["termination_date"] = pd.to_datetime(self.hr_df["termination_date"], errors="coerce")

        # Fill NaNs where appropriate
        self.users_df = self.users_df.fillna("")
        self.permissions_df = self.permissions_df.fillna("")
        self.logs_df = self.logs_df.fillna("")
        self.hr_df = self.hr_df.fillna("")

    def get_user_permissions(self):
        """Maps each user to their full set of permissions based on assigned roles."""
        user_roles = self.users_df.merge(self.permissions_df, on="role", how="inner")
        user_perms = user_roles.groupby("user_id").agg({
            "name": "first",
            "department": "first",
            "role": lambda x: list(set(x)),
            "permission": lambda x: list(set(x))
        }).reset_index()
        return user_perms

    def audit_static_entitlements(self):
        """Audits SoD violations residing in authorization profiles (what users CAN do)."""
        violations = []
        user_perms = self.get_user_permissions()
        
        conflicts = self.rules.get("conflicting_permission_pairs", [])
        
        for _, row in user_perms.iterrows():
            user_id = row["user_id"]
            name = row["name"]
            dept = row["department"]
            perms = set(row["permission"])
            roles = row["role"]
            
            for conflict in conflicts:
                perm_a = conflict["permission_a"]
                perm_b = conflict["permission_b"]
                
                if perm_a in perms and perm_b in perms:
                    violations.append({
                        "violation_type": "STATIC_SOD",
                        "user_id": user_id,
                        "user_name": name,
                        "department": dept,
                        "conflict_id": conflict["id"],
                        "conflict_name": conflict["name"],
                        "risk_level": conflict["risk_level"],
                        "details": f"User holds roles {roles} which grant both conflicting permissions: '{perm_a}' and '{perm_b}'."
                    })
        return pd.DataFrame(violations)

    def audit_transactional_violations(self):
        """Audits SoD violations inside transaction logs (what users ACTUALLY did)."""
        violations = []
        conflicts = self.rules.get("conflicting_permission_pairs", [])
        
        for conflict in conflicts:
            perm_a = conflict["permission_a"]
            perm_b = conflict["permission_b"]
            
            # Filter logs for permission A and B
            logs_a = self.logs_df[self.logs_df["action"] == perm_a]
            logs_b = self.logs_df[self.logs_df["action"] == perm_b]
            
            # Find users who performed both actions
            intersecting_users = set(logs_a["user_id"]).intersection(set(logs_b["user_id"]))
            
            for user_id in intersecting_users:
                # Find occurrences where the user performed both actions
                user_logs_a = logs_a[logs_a["user_id"] == user_id]
                user_logs_b = logs_b[logs_b["user_id"] == user_id]
                
                # Check for transaction-cycle violation (actions on the same Document/Vendor ID)
                cycle_violations = []
                for _, row_a in user_logs_a.iterrows():
                    # For AP payments, the related_id is the vendor or PO
                    related_a = row_a["related_id"]
                    matching_b = user_logs_b[user_logs_b["related_id"] == related_a]
                    
                    if not matching_b.empty:
                        for _, row_b in matching_b.iterrows():
                            cycle_violations.append((row_a, row_b))
                
                user_info = self.users_df[self.users_df["user_id"] == user_id]
                name = user_info["name"].values[0] if not user_info.empty else "Unknown"
                dept = user_info["department"].values[0] if not user_info.empty else "Unknown"
                
                if cycle_violations:
                    for row_a, row_b in cycle_violations:
                        violations.append({
                            "violation_type": "TRANSACTION_CYCLE_VIOLATION",
                            "user_id": user_id,
                            "user_name": name,
                            "department": dept,
                            "conflict_id": conflict["id"],
                            "conflict_name": conflict["name"],
                            "risk_level": "CRITICAL",
                            "details": f"User executed full cycle on related ID '{row_a['related_id']}': Created ({row_a['action']} in Tx {row_a['transaction_id']}) and Approved ({row_b['action']} in Tx {row_b['transaction_id']})."
                        })
                else:
                    # General transactional SoD (same user did both actions, but not on the same ID)
                    violations.append({
                        "violation_type": "TRANSACTION_SOD_CROSSOVER",
                        "user_id": user_id,
                        "user_name": name,
                        "department": dept,
                        "conflict_id": conflict["id"],
                        "conflict_name": conflict["name"],
                        "risk_level": conflict["risk_level"],
                        "details": f"User executed both conflicting transaction codes: '{perm_a}' and '{perm_b}' during the audit period, though not on the same document ID."
                    })
                    
        return pd.DataFrame(violations)

    def audit_user_integrity(self):
        """Audits transactions made by terminated employees or unregistered ghost accounts."""
        violations = []
        
        # Merge logs with HR to check status
        logs_hr = self.logs_df.merge(self.hr_df, left_on="user_id", right_on="employee_id", how="left")
        
        for _, row in logs_hr.iterrows():
            user_id = row["user_id"]
            tx_id = row["transaction_id"]
            action = row["action"]
            tx_date = row["timestamp"]
            emp_status = row["status"]  # Status from HR
            term_date = row["termination_date"]
            name = row["name"] if pd.notna(row["name"]) and row["name"] != "" else "Unknown"
            dept = row["department"] if pd.notna(row["department"]) and row["department"] != "" else "Unknown"
            
            # 1. Unregistered Ghost Account
            if pd.isna(row["employee_id"]):
                violations.append({
                    "violation_type": "GHOST_ACCOUNT_ACTIVITY",
                    "user_id": user_id,
                    "user_name": "Ghost Account",
                    "department": "Unknown",
                    "conflict_id": "SYS_GHOST_USER",
                    "conflict_name": "Ghost/Unregistered User Activity",
                    "risk_level": "CRITICAL",
                    "details": f"Transaction {tx_id} ({action}) processed by user '{user_id}' who is not registered in the HR database."
                })
            # 2. Terminated Employee
            elif emp_status == "TERMINATED":
                if pd.notna(term_date) and tx_date > term_date:
                    violations.append({
                        "violation_type": "TERMINATED_USER_ACTIVITY",
                        "user_id": user_id,
                        "user_name": name,
                        "department": dept,
                        "conflict_id": "SYS_TERM_USER",
                        "conflict_name": "Post-Termination Account Activity",
                        "risk_level": "CRITICAL",
                        "details": f"Transaction {tx_id} ({action}) processed on {tx_date} by employee '{user_id}' who was terminated on {term_date}."
                    })
                    
        return pd.DataFrame(violations)

    def audit_split_transactions(self):
        """Detects split POs created by the same user to the same vendor to bypass approval limit."""
        violations = []
        limit = self.rules["threshold_rules"]["single_approval_limit"]
        split_cfg = self.rules["threshold_rules"]["split_transaction_detection"]
        window_hours = split_cfg["time_window_hours"]
        
        # We only audit PO_CREATE transactions
        po_logs = self.logs_df[self.logs_df["action"] == "PO_CREATE"].copy()
        if po_logs.empty:
            return pd.DataFrame(violations)
            
        po_logs = po_logs.sort_values(by=["user_id", "related_id", "timestamp"])
        
        # Group by user and vendor
        grouped = po_logs.groupby(["user_id", "related_id"])
        
        for (user_id, vendor_id), group in grouped:
            if len(group) < 2:
                continue
                
            # Iterate through the group transactions to check windows
            transactions = group.to_dict('records')
            i = 0
            n = len(transactions)
            while i < n:
                curr_tx = transactions[i]
                curr_time = curr_tx["timestamp"]
                curr_amount = curr_tx["amount"]
                
                # Check if current tx is already above limit (that's an approval issue, not a split issue)
                if curr_amount >= limit:
                    i += 1
                    continue
                    
                cumulative_sum = curr_amount
                split_group = [curr_tx]
                
                for j in range(i + 1, n):
                    next_tx = transactions[j]
                    time_diff = (next_tx["timestamp"] - curr_time).total_seconds() / 3600.0
                    
                    if time_diff <= window_hours:
                        if next_tx["amount"] < limit:
                            cumulative_sum += next_tx["amount"]
                            split_group.append(next_tx)
                    else:
                        break
                
                # If the sum exceeds the limit, and we have multiple transactions
                if len(split_group) > 1 and cumulative_sum >= limit:
                    tx_ids = [tx["transaction_id"] for tx in split_group]
                    user_info = self.users_df[self.users_df["user_id"] == user_id]
                    name = user_info["name"].values[0] if not user_info.empty else "Unknown"
                    dept = user_info["department"].values[0] if not user_info.empty else "Unknown"
                    
                    violations.append({
                        "violation_type": "SPLIT_TRANSACTION_LIMIT_AVOIDANCE",
                        "user_id": user_id,
                        "user_name": name,
                        "department": dept,
                        "conflict_id": "SYS_SPLIT_TX",
                        "conflict_name": "Split Transaction Threshold Avoidance",
                        "risk_level": "HIGH",
                        "details": f"User created {len(split_group)} POs to vendor '{vendor_id}' within {window_hours} hours totaling ${cumulative_sum:,.2f}, circumventing the ${limit:,.2f} approval limit. Transaction IDs: {tx_ids}."
                    })
                    # Skip all elements in the split group
                    i += len(split_group)
                else:
                    i += 1
        return pd.DataFrame(violations)

    def audit_department_restrictions(self):
        """Audits authorization violations where users hold roles outside their business unit context."""
        violations = []
        restrictions = self.rules.get("department_permission_restrictions", {})
        user_perms = self.get_user_permissions()
        
        for _, row in user_perms.iterrows():
            user_id = row["user_id"]
            name = row["name"]
            dept = row["department"]
            perms = row["permission"]
            
            for perm in perms:
                if perm in restrictions:
                    allowed_depts = restrictions[perm]
                    if dept not in allowed_depts:
                        violations.append({
                            "violation_type": "DEPARTMENT_RESTRICTION_VIOLATION",
                            "user_id": user_id,
                            "user_name": name,
                            "department": dept,
                            "conflict_id": f"DEP_RESTRICT_{perm}",
                            "conflict_name": f"Unauthorized Access to {perm}",
                            "risk_level": "HIGH",
                            "details": f"User is in department '{dept}', but holds permission '{perm}' which is restricted to: {allowed_depts}."
                        })
        return pd.DataFrame(violations)

    def run_all_audits(self):
        """Runs all auditing modules and compiles them into a single consolidated report."""
        dfs = [
            self.audit_static_entitlements(),
            self.audit_transactional_violations(),
            self.audit_user_integrity(),
            self.audit_split_transactions(),
            self.audit_department_restrictions()
        ]
        
        # Filter out empty dataframes and concatenate
        active_dfs = [df for df in dfs if not df.empty]
        if active_dfs:
            consolidated = pd.concat(active_dfs, ignore_index=True)
            return consolidated
        else:
            return pd.DataFrame(columns=[
                "violation_type", "user_id", "user_name", "department", 
                "conflict_id", "conflict_name", "risk_level", "details"
            ])
