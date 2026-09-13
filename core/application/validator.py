#!/usr/bin/env python3
"""
CSV Validator for FORM-5
Validates an uploaded or existing CSV against application/mapping_config.json
Checks header row structure, required columns, and returns a comprehensive validation report.
"""

import csv
import io
import json
import os

def load_mapping(config_path):
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_csv_content(csv_text_or_lines, config_path):
    """
    Validates CSV lines or string against mapping_config.json.
    Returns:
    {
        "valid": bool,
        "total_columns": int,
        "total_rows": int,
        "category_header": list,
        "column_header": list,
        "missing_columns": list,
        "sample_records": list,
        "errors": list,
        "warnings": list
    }
    """
    mapping = load_mapping(config_path)
    
    if isinstance(csv_text_or_lines, str):
        reader = csv.reader(io.StringIO(csv_text_or_lines.strip()))
    else:
        reader = csv.reader(csv_text_or_lines)
        
    rows = list(reader)
    errors = []
    warnings = []
    
    if len(rows) < 2:
        return {
            "valid": False,
            "total_columns": 0,
            "total_rows": 0,
            "category_header": [],
            "column_header": [],
            "missing_columns": ["CSV must have at least 2 header rows and at least 1 data row"],
            "sample_records": [],
            "errors": ["File has less than 2 rows. Expected Category Header (Row 1) and Column Name Header (Row 2)."],
            "warnings": []
        }
        
    category_header = rows[0]
    column_header = rows[1]
    data_rows = rows[2:]
    
    total_cols = max(len(category_header), len(column_header))
    total_data_rows = len(data_rows)
    
    # Check max index referenced in mapping
    required_indices = set()
    for key, target in mapping.items():
        if isinstance(target, int):
            required_indices.add(target)
        elif isinstance(target, str) and target.isdigit():
            required_indices.add(int(target))
        elif isinstance(target, list):
            for item in target:
                if isinstance(item, int):
                    required_indices.add(item)
                elif isinstance(item, str) and item.isdigit():
                    required_indices.add(int(item))
                    
    missing_columns = []
    for idx in sorted(required_indices):
        if idx >= len(column_header):
            missing_columns.append(f"Column index {idx} (exceeds file columns: {len(column_header)})")
            
    # Check critical columns
    # Index 0: Employee Code, Index 2: Employee Name
    if len(column_header) > 0 and not column_header[0].strip():
        warnings.append("Column 0 (Employee Code) header appears empty.")
    if len(column_header) > 2 and not column_header[2].strip():
        warnings.append("Column 2 (Worker Name) header appears empty.")
        
    if total_data_rows == 0:
        errors.append("No employee records found in CSV (data rows start at row 3).")
        
    # Check sample rows for critical fields
    sample_records = []
    for i, row in enumerate(data_rows[:5], start=1):
        emp_code = row[0].strip() if len(row) > 0 else f"ROW_{i}"
        emp_name = row[2].strip() if len(row) > 2 else f"Employee_{i}"
        age = row[3].strip() if len(row) > 3 else ""
        dept = row[10].strip() if len(row) > 10 else ""
        sample_records.append({
            "row": i,
            "code": emp_code,
            "name": emp_name,
            "age": age,
            "designation": dept,
            "col_count": len(row)
        })
        
    is_valid = len(missing_columns) == 0 and len(errors) == 0

    return {
        "valid": is_valid,
        "total_columns": total_cols,
        "total_rows": total_data_rows,
        "category_header": category_header[:15],
        "column_header": column_header[:15],
        "missing_columns": missing_columns,
        "sample_records": sample_records,
        "errors": errors,
        "warnings": warnings
    }

def validate_csv_file(file_path, config_path):
    if not os.path.exists(file_path):
        return {
            "valid": False,
            "errors": [f"File not found: {file_path}"]
        }
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return validate_csv_content(f, config_path)

if __name__ == "__main__":
    app_dir = os.path.dirname(os.path.abspath(__file__))
    core_dir = os.path.dirname(app_dir)
    root_dir = os.path.dirname(core_dir)

    csv_file = os.path.join(core_dir, "data", "data.csv")
    cfg_file = os.path.join(core_dir, "config", "mapping_config.json")
    if not os.path.exists(cfg_file):
        for candidate in [
            os.path.join(core_dir, "mapping_config.json"),
            os.path.join(app_dir, "mapping_config.json"),
            os.path.join(root_dir, "mapping_config.json"),
        ]:
            if os.path.exists(candidate):
                cfg_file = candidate
                break

    report = validate_csv_file(csv_file, cfg_file)
    print("Validation result:", json.dumps(report, indent=2))
