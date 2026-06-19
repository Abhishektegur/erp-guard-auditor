import os
import csv
import random
from datetime import datetime, timedelta

def generate_mock_data(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Generate Permissions Mapping
    # Standard roles and their associated transaction codes
    permissions = [
        # Role, Permission
        ("AP_CLERK", "AP_CREATE_VENDOR"),
        ("AP_CLERK", "AP_ENTER_INVOICE"),
        ("AP_APPROVER", "AP_APPROVE_PAYMENT"),
        ("AP_MANAGER", "AP_CREATE_VENDOR"),    # Conflict: AP_MANAGER has both vendor create and pay approve
        ("AP_MANAGER", "AP_APPROVE_PAYMENT"),
        ("PURCHASING_AGENT", "PO_CREATE"),
        ("RECEIVING_CLERK", "PO_RECEIVE_GOODS"),
        ("GL_CLERK", "GL_CREATE_JOURNAL"),
        ("GL_APPROVER", "GL_POST_JOURNAL"),
        ("SYS_ADMIN", "SYS_ADMIN_CONFIG"),
        ("SYS_ADMIN", "SYS_DELETE_LOGS"),       # Conflict: Admin can edit config and delete logs
        ("MARKETING_USER", "MKT_CAMPAIGN"),
        ("MARKETING_USER", "GL_POST_JOURNAL"),   # Conflict: Marketing department user has GL posting permission
    ]
    
    with open(os.path.join(output_dir, "permissions.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["role", "permission"])
        writer.writerows(permissions)
        
    # 2. Generate HR Active Directory Database
    hr_data = [
        # employee_id, name, department, status, termination_date
        ("asmith", "Alice Smith", "Finance", "ACTIVE", ""),
        ("bjohnson", "Bob Johnson", "Finance", "ACTIVE", ""),
        ("cbrown", "Charlie Brown", "IT", "TERMINATED", "2026-05-01"), # Terminated before transaction log starts
        ("dmiller", "David Miller", "Procurement", "ACTIVE", ""),
        ("edavis", "Eve Davis", "Marketing", "ACTIVE", ""),
        ("fwilson", "Frank Wilson", "Operations", "ACTIVE", ""),
        ("glee", "Grace Lee", "Treasury", "ACTIVE", ""),
        ("hclark", "Henry Clark", "Finance", "ACTIVE", ""),
        ("imartinez", "Ivy Martinez", "IT", "ACTIVE", ""),
    ]
    
    with open(os.path.join(output_dir, "hr_database.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["employee_id", "name", "department", "status", "termination_date"])
        writer.writerows(hr_data)
        
    # 3. Generate Users and their Role Assignments
    users = [
        # user_id, name, department, role, status
        ("asmith", "Alice Smith", "Finance", "AP_MANAGER", "ACTIVE"),         # STATIC SOD VIOLATION: AP_MANAGER has both Create Vendor & Approve Payment
        ("bjohnson", "Bob Johnson", "Finance", "AP_CLERK", "ACTIVE"),
        ("cbrown", "Charlie Brown", "IT", "SYS_ADMIN", "INACTIVE"),           # INACTIVE USER / TERMINATED EMPLOYEE
        ("dmiller", "David Miller", "Procurement", "PURCHASING_AGENT", "ACTIVE"),
        ("edavis", "Eve Davis", "Marketing", "MARKETING_USER", "ACTIVE"),     # DEPARTMENT RESTRICTION VIOLATION: Marketing has GL_POST_JOURNAL
        ("fwilson", "Frank Wilson", "Operations", "RECEIVING_CLERK", "ACTIVE"),
        ("glee", "Grace Lee", "Treasury", "AP_APPROVER", "ACTIVE"),
        ("hclark", "Henry Clark", "Finance", "GL_CLERK", "ACTIVE"),
        ("imartinez", "Ivy Martinez", "IT", "SYS_ADMIN", "ACTIVE"),          # STATIC SOD VIOLATION: SYS_ADMIN has admin and delete log capabilities
    ]
    
    with open(os.path.join(output_dir, "users.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "name", "department", "role", "status"])
        writer.writerows(users)

    # 4. Generate Transaction Logs
    # We will embed transaction data starting from 2026-06-01
    start_date = datetime(2026, 6, 1, 9, 0, 0)
    logs = []
    tx_id = 10001
    
    # Helper to format timestamp
    def fmt(dt):
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    # Day 1: Normal operations
    logs.append([tx_id, "bjohnson", "AP_CREATE_VENDOR", 0.0, "VEND_101", fmt(start_date)])
    tx_id += 1
    logs.append([tx_id, "bjohnson", "AP_ENTER_INVOICE", 1500.0, "INV_5001", fmt(start_date + timedelta(hours=1))])
    tx_id += 1
    logs.append([tx_id, "glee", "AP_APPROVE_PAYMENT", 1500.0, "INV_5001", fmt(start_date + timedelta(hours=2))])
    tx_id += 1
    
    # Day 2: Normal PO cycle
    logs.append([tx_id, "dmiller", "PO_CREATE", 4500.0, "PO_9001", fmt(start_date + timedelta(days=1))])
    tx_id += 1
    logs.append([tx_id, "fwilson", "PO_RECEIVE_GOODS", 0.0, "PO_9001", fmt(start_date + timedelta(days=1, hours=3))])
    tx_id += 1

    # Day 3: TRANSACTIONAL SOD VIOLATION - Bob Johnson (AP_CLERK) creates a vendor and approves a payment to them.
    # Note: Bob's role is AP_CLERK, which doesn't technically have AP_APPROVE_PAYMENT permission.
    # But in reality, due to system bugs or admin errors, users sometimes execute transactions they shouldn't.
    logs.append([tx_id, "bjohnson", "AP_CREATE_VENDOR", 0.0, "VEND_999", fmt(start_date + timedelta(days=2))])
    tx_id += 1
    logs.append([tx_id, "bjohnson", "AP_APPROVE_PAYMENT", 12000.0, "VEND_999", fmt(start_date + timedelta(days=2, hours=1))])
    tx_id += 1

    # Day 4: GHOST / INACTIVE USER VIOLATION - Charlie Brown was terminated on 2026-05-01, but logs show actions on 2026-06-04
    logs.append([tx_id, "cbrown", "SYS_ADMIN_CONFIG", 0.0, "SYS_CONF_01", fmt(start_date + timedelta(days=3))])
    tx_id += 1
    logs.append([tx_id, "cbrown", "SYS_DELETE_LOGS", 0.0, "LOGS_JUNE_03", fmt(start_date + timedelta(days=3, hours=1))])
    tx_id += 1

    # Day 5: SPLIT TRANSACTION VIOLATION - David Miller splits a $25,000 PO into three smaller POs
    # to avoid the single PO approval threshold ($10,000). All are to VEND_202 within 24 hours.
    logs.append([tx_id, "dmiller", "PO_CREATE", 9500.0, "VEND_202", fmt(start_date + timedelta(days=4))])
    tx_id += 1
    logs.append([tx_id, "dmiller", "PO_CREATE", 8500.0, "VEND_202", fmt(start_date + timedelta(days=4, hours=2))])
    tx_id += 1
    logs.append([tx_id, "dmiller", "PO_CREATE", 7000.0, "VEND_202", fmt(start_date + timedelta(days=4, hours=4))])
    tx_id += 1

    # Day 6: Normal GL journal processing
    logs.append([tx_id, "hclark", "GL_CREATE_JOURNAL", 50000.0, "JE_7001", fmt(start_date + timedelta(days=5))])
    tx_id += 1
    logs.append([tx_id, "glee", "GL_POST_JOURNAL", 50000.0, "JE_7001", fmt(start_date + timedelta(days=5, hours=2))])
    tx_id += 1
    
    # Day 7: DEPARTMENT VIOLATION - Marketing user Eve Davis posts a journal entry
    logs.append([tx_id, "edavis", "GL_POST_JOURNAL", 250.0, "JE_7002", fmt(start_date + timedelta(days=6))])
    tx_id += 1

    # Write logs to CSV
    with open(os.path.join(output_dir, "transaction_logs.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["transaction_id", "user_id", "action", "amount", "related_id", "timestamp"])
        writer.writerows(logs)
        
    print(f"Mock audit data generated successfully in {output_dir}")

if __name__ == "__main__":
    generate_mock_data("./data")
