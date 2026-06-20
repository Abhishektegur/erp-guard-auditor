import os
import json
import pytest
import pandas as pd
from src.generator import generate_mock_data
from src.engine import ERPAuditEngine

@pytest.fixture
def test_env(tmp_path):
    # Create config directory and write rules
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    rules_path = config_dir / "sod_rules.json"
    
    rules = {
      "conflicting_permission_pairs": [
        {
          "id": "SOD_01_VENDOR_FRAUD",
          "name": "Vendor Creation & Payment Approval Conflict",
          "permission_a": "AP_CREATE_VENDOR",
          "permission_b": "AP_APPROVE_PAYMENT",
          "risk_level": "CRITICAL"
        },
        {
          "id": "SOD_02_PO_COLLUSION",
          "name": "PO Creation & Goods Receipt Conflict",
          "permission_a": "PO_CREATE",
          "permission_b": "PO_RECEIVE_GOODS",
          "risk_level": "HIGH"
        }
      ],
      "threshold_rules": {
        "single_approval_limit": 10000.0,
        "split_transaction_detection": {
          "time_window_hours": 24,
          "max_cumulative_ratio": 0.95
        }
      },
      "department_permission_restrictions": {
        "GL_POST_JOURNAL": ["Finance", "Accounting"]
      }
    }
    
    with open(rules_path, "w") as f:
        json.dump(rules, f)
        
    # Generate mock data
    data_dir = tmp_path / "data"
    generate_mock_data(str(data_dir))
    
    # Initialize engine
    engine = ERPAuditEngine(str(rules_path), str(data_dir))
    return engine

def test_static_entitlements(test_env):
    engine = test_env
    violations = engine.audit_static_entitlements()
    
    # We expect static violations for:
    # 1. 'asmith' who holds AP_MANAGER which has AP_CREATE_VENDOR and AP_APPROVE_PAYMENT
    assert not violations.empty
    violating_users = violations["user_id"].tolist()
    assert "asmith" in violating_users
    
    # Verify the details field
    asmith_violation = violations[violations["user_id"] == "asmith"].iloc[0]
    assert asmith_violation["conflict_id"] == "SOD_01_VENDOR_FRAUD"
    assert asmith_violation["risk_level"] == "CRITICAL"

def test_transactional_violations(test_env):
    engine = test_env
    violations = engine.audit_transactional_violations()
    
    # In mock data, 'bjohnson' created VEND_999 and approved payment to VEND_999
    assert not violations.empty
    cycle_violations = violations[violations["violation_type"] == "TRANSACTION_CYCLE_VIOLATION"]
    assert not cycle_violations.empty
    assert "bjohnson" in cycle_violations["user_id"].tolist()
    
    bjohnson_violation = cycle_violations[cycle_violations["user_id"] == "bjohnson"].iloc[0]
    assert bjohnson_violation["conflict_id"] == "SOD_01_VENDOR_FRAUD"

def test_user_integrity(test_env):
    engine = test_env
    violations = engine.audit_user_integrity()
    
    # In mock data:
    # 'cbrown' is terminated but performed actions in June 2026
    assert not violations.empty
    terminated_violations = violations[violations["violation_type"] == "TERMINATED_USER_ACTIVITY"]
    assert not terminated_violations.empty
    assert "cbrown" in terminated_violations["user_id"].tolist()
    
    # Check details contain terminated date
    cbrown_violation = terminated_violations[terminated_violations["user_id"] == "cbrown"].iloc[0]
    assert "2026-05-01" in cbrown_violation["details"]

def test_split_transactions(test_env):
    engine = test_env
    violations = engine.audit_split_transactions()
    
    # In mock data, 'dmiller' created POs of 9.5k, 8.5k, and 7k to same vendor
    # within 24h, totaling 25k (which exceeds the 10k limit).
    assert not violations.empty
    split_violations = violations[violations["violation_type"] == "SPLIT_TRANSACTION_LIMIT_AVOIDANCE"]
    assert not split_violations.empty
    assert "dmiller" in split_violations["user_id"].tolist()
    
    dmiller_violation = split_violations[split_violations["user_id"] == "dmiller"].iloc[0]
    assert "$25,000" in dmiller_violation["details"]

def test_department_restrictions(test_env):
    engine = test_env
    violations = engine.audit_department_restrictions()
    
    # In mock data, 'edavis' is in Marketing but holds GL_POST_JOURNAL
    assert not violations.empty
    dept_violations = violations[violations["violation_type"] == "DEPARTMENT_RESTRICTION_VIOLATION"]
    assert not dept_violations.empty
    assert "edavis" in dept_violations["user_id"].tolist()
    
    edavis_violation = dept_violations[dept_violations["user_id"] == "edavis"].iloc[0]
    assert "Marketing" in edavis_violation["details"]

def test_standardize_columns():
    # Test case-insensitive alias matching, whitespace stripping, and unmapped columns remaining intact
    df_users = pd.DataFrame(columns=["  User ID  ", "Employee Name", "BU", "Job Role", "Active", "unrelated_col"])
    standardized_users = ERPAuditEngine.standardize_columns(df_users, "users")
    
    assert "user_id" in standardized_users.columns
    assert "name" in standardized_users.columns
    assert "department" in standardized_users.columns
    assert "role" in standardized_users.columns
    assert "status" in standardized_users.columns
    assert "unrelated_col" in standardized_users.columns
    
    # Test permissions sheet mapping
    df_perms = pd.DataFrame(columns=["Role_name", "TCode"])
    standardized_perms = ERPAuditEngine.standardize_columns(df_perms, "permissions")
    
    assert "role" in standardized_perms.columns
    assert "permission" in standardized_perms.columns
    
    # Test transaction logs mapping
    df_logs = pd.DataFrame(columns=["Tx_id", "Username", "Operation", "Total", "Vendor_id", "Datetime"])
    standardized_logs = ERPAuditEngine.standardize_columns(df_logs, "transaction_logs")
    
    assert "transaction_id" in standardized_logs.columns
    assert "user_id" in standardized_logs.columns
    assert "action" in standardized_logs.columns
    assert "amount" in standardized_logs.columns
    assert "related_id" in standardized_logs.columns
    assert "timestamp" in standardized_logs.columns
    
    # Test empty or None inputs
    assert ERPAuditEngine.standardize_columns(None, "users") is None
    df_empty = pd.DataFrame()
    assert ERPAuditEngine.standardize_columns(df_empty, "users").empty

