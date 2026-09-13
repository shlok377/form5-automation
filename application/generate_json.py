#!/usr/bin/env python3
"""
FORM-5 JSON Exporter
Reads data/data.csv and uses application/mapping_config.json to generate
structured, individual employee JSON files into temp_json/
with the naming scheme: 0001_employee_name_empcode.json
"""

import csv
import json
import os
import re
import sys

def sanitize_filename(name):
    # Keep alphanumeric characters, spaces, hyphens, and convert spaces/hyphens to underscores
    name = re.sub(r'[^\w\s-]', '', str(name)).strip()
    return re.sub(r'[-\s]+', '_', name)

def get_value_from_row(row, mapping_target):
    if mapping_target is None or mapping_target == "":
        return ""
    if isinstance(mapping_target, str) and mapping_target.startswith("fixed:"):
        return mapping_target[6:]
    if isinstance(mapping_target, list):
        parts = []
        for item in mapping_target:
            if isinstance(item, int) and 0 <= item < len(row):
                parts.append(row[item].strip())
            elif isinstance(item, str) and item.isdigit():
                idx = int(item)
                if 0 <= idx < len(row):
                    parts.append(row[idx].strip())
            else:
                parts.append(str(item).strip())
        return "/".join(parts)
    if isinstance(mapping_target, int):
        if 0 <= mapping_target < len(row):
            return row[mapping_target].strip()
        return ""
    if isinstance(mapping_target, str) and mapping_target.isdigit():
        idx = int(mapping_target)
        if 0 <= idx < len(row):
            return row[idx].strip()
        return ""
    if isinstance(mapping_target, str) and ("/" in mapping_target or "," in mapping_target):
        sep = "/" if "/" in mapping_target else ","
        parts = []
        for x in mapping_target.split(sep):
            x = x.strip()
            if x.isdigit():
                idx = int(x)
                if 0 <= idx < len(row):
                    parts.append(row[idx].strip())
            else:
                parts.append(x)
        return "/".join(parts)
    return str(mapping_target).strip()

def parse_float(val):
    if val is None:
        return None
    val_str = str(val).strip()
    m = re.search(r'[-+]?\d*\.?\d+', val_str)
    if m:
        try:
            return float(m.group(0))
        except ValueError:
            return None
    return None

def eval_range(val, min_val, max_val):
    num = parse_float(val)
    if num is None:
        return ""
    if num < min_val:
        return "Decrease"
    elif num > max_val:
        return "Increase"
    else:
        return "Normal"

def eval_diff_component(val, min_val, max_val):
    num = parse_float(val)
    if num is None:
        return "="
    if num < min_val:
        return "↓"
    elif num > max_val:
        return "↑"
    else:
        return "="

def eval_urine_component(val):
    if not val:
        return "="
    val_clean = str(val).strip().lower()
    if val_clean in ["absent", "nil", "negative", "neg", "normal", "0", "-", "none", ""]:
        return "="
    return "↑"

def evaluate_section_f(row, data):
    inv = data.get("investigation_report", {})
    gender = str(data.get("demographics", {}).get("gender", "")).strip().lower()
    is_female = ("female" in gender or gender == "f")

    # 1. Hb % (M: 13.8 - 17.2, F: 12.0 - 15.6)
    hb_min, hb_max = (12.0, 15.6) if is_female else (13.8, 17.2)
    inv["hb_status"] = eval_range(inv.get("hb_value"), hb_min, hb_max)

    # 2. WBC Differential (N/L/M/E/B) %
    # Total WBC (4000 - 10000), Neutrophil (40-70), Lymphocyte (20-45), Monocyte (2-8), Eosinophil (0-6), Basophil (0-1)
    wbc_val = parse_float(inv.get("wbc_value"))
    if wbc_val is not None:
        if wbc_val < 4000:
            wbc_sym = "↓"
        elif wbc_val > 10000:
            wbc_sym = "↑"
        else:
            wbc_sym = "="
        wbc_part = f"WBC{wbc_sym} "
    else:
        wbc_part = "WBC= "

    n_val = row[90] if len(row) > 90 else ""
    l_val = row[91] if len(row) > 91 else ""
    m_val = row[92] if len(row) > 92 else ""
    e_val = row[93] if len(row) > 93 else ""
    b_val = row[94] if len(row) > 94 else ""
    
    n_sym = eval_diff_component(n_val, 40, 70)
    l_sym = eval_diff_component(l_val, 20, 45)
    m_sym = eval_diff_component(m_val, 2, 8)
    e_sym = eval_diff_component(e_val, 0, 6)
    b_sym = eval_diff_component(b_val, 0, 1)
    inv["wbc_status"] = f"{wbc_part}(N{n_sym} / L{l_sym} / M{m_sym} / E{e_sym} / B{b_sym})"

    # 3. Platelet Count (1.50 - 4.50)
    inv["platelet_status"] = eval_range(inv.get("platelet_value"), 1.50, 4.50)

    # 4. ESR (M: 0 - 15, F: 0 - 20)
    esr_min, esr_max = (0, 20) if is_female else (0, 15)
    inv["esr_status"] = eval_range(inv.get("esr_value"), esr_min, esr_max)

    # 5. FBS / RBS (70.00 - 140.00)
    inv["fbs_status"] = eval_range(inv.get("fbs_value"), 70.00, 140.00)

    # 6. PPBS (70.00 - 140.00)
    inv["ppbs_status"] = eval_range(inv.get("ppbs_value"), 70.00, 140.00)

    # 7. HBA1C level (4.0 - 6.0)
    inv["hba1c_status"] = eval_range(inv.get("hba1c_value"), 4.0, 6.0)

    # 8. BUN (7.0 - 20.0)
    inv["bun_status"] = eval_range(inv.get("bun_value"), 7.0, 20.0)

    # 9. Creatinine (0.50 - 1.50)
    inv["creatinine_status"] = eval_range(inv.get("creatinine_value"), 0.50, 1.50)

    # 10. Total Protein (6.30 - 8.20)
    inv["total_protein_status"] = eval_range(inv.get("total_protein_value"), 6.30, 8.20)

    # 11. Albumin (3.90 - 5.00)
    inv["albumin_status"] = eval_range(inv.get("albumin_value"), 3.90, 5.00)

    # 12. Globulin (2.30 - 3.50)
    inv["globulin_status"] = eval_range(inv.get("globulin_value"), 2.30, 3.50)

    # 13. SGOT (0.00 - 45.00)
    inv["sgot_status"] = eval_range(inv.get("sgot_value"), 0.00, 45.00)

    # 14. SGPT (0.00 - 45.00)
    inv["sgpt_status"] = eval_range(inv.get("sgpt_value"), 0.00, 45.00)

    # 15. Bilirubin (0.00 - 2.00)
    inv["bilirubin_status"] = eval_range(inv.get("bilirubin_value"), 0.00, 2.00)

    # 16. Urine RE (Protein/Sugar/Bilirubin/Pus Cells/RBC/Epithelial Cells/Crystals/Bacteria)
    p_sym = eval_urine_component(row[95] if len(row) > 95 else "")
    s_sym = eval_urine_component(row[96] if len(row) > 96 else "")
    b_sym = eval_urine_component(row[97] if len(row) > 97 else "")
    pc_sym = eval_urine_component(row[98] if len(row) > 98 else "")
    rbc_sym = eval_urine_component(row[99] if len(row) > 99 else "")
    ec_sym = eval_urine_component(row[100] if len(row) > 100 else "")
    c_sym = eval_urine_component(row[101] if len(row) > 101 else "")
    bac_sym = eval_urine_component(row[102] if len(row) > 102 else "")
    inv["urine_re_status"] = f"P{p_sym} S{s_sym} B{b_sym} PC{pc_sym} RBC{rbc_sym} EC{ec_sym} C{c_sym} B{bac_sym}"

    # 17. Urine ME
    ume_val = str(inv.get("urine_me_value", "")).strip().lower()
    if not ume_val:
        inv["urine_me_status"] = ""
    elif any(k in ume_val for k in ["nil", "absent", "normal", "neg"]):
        inv["urine_me_status"] = "Normal"
    else:
        inv["urine_me_status"] = "Normal"

    # 18. PSA (0.00 - 4.00)
    inv["psa_status"] = eval_range(inv.get("psa_value"), 0.00, 4.00)

def build_employee_json(row, index_num, mapping):
    idx_str = f"{index_num:04d}"
    code = row[0].strip() if len(row) > 0 else "UNKNOWN"
    name = row[2].strip() if len(row) > 2 else f"Employee_{idx_str}"
    
    # Initialize JSON object with 10 categories
    data = {
        "employee_index": idx_str,
        "employee_code": code,
        "employee_name": name,
        "demographics": {},
        "occupational_history": {},
        "brief_review": {},
        "current_symptoms": {},
        "physical": {},
        "investigation_report": {},
        "xray": {},
        "eye_exam": {},
        "ecg": {},
        "medical_fitness_test": {},
        "recommendations": "",
        "signature_date": ""
    }

    # Populate mapped fields
    for field_path, target in mapping.items():
        val = get_value_from_row(row, target)
        if "." in field_path:
            cat, key = field_path.split(".", 1)
            if cat in data and isinstance(data[cat], dict):
                data[cat][key] = val
        else:
            data[field_path] = val

    # Automatically evaluate Section F values against normal ranges
    evaluate_section_f(row, data)

    # Generate standardized filename
    filename = f"{idx_str}_{sanitize_filename(name)}_{sanitize_filename(code)}.json"
    return filename, data

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "data.csv")
    config_path = os.path.join(base_dir, "application", "mapping_config.json")
    output_dir = os.path.join(base_dir, "temp_json")

    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        print(f"Loaded mapping config from {config_path} ({len(mapping)} fields)")
    else:
        print(f"Warning: Config file {config_path} not found. Using empty mapping.", file=sys.stderr)
        mapping = {}

    os.makedirs(output_dir, exist_ok=True)

    with open(csv_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        # Skip Category header and Column name header
        cat_header = next(reader)
        col_header = next(reader)
        rows = list(reader)

    print(f"Found {len(rows)} employee records in CSV.")
    generated_files = []

    for i, row in enumerate(rows, start=1):
        filename, emp_json = build_employee_json(row, i, mapping)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as out:
            json.dump(emp_json, out, indent=2, ensure_ascii=False)
        generated_files.append(filename)

    print(f"Successfully generated {len(generated_files)} JSON files into: {output_dir}")
    print(f"Sample first file: {generated_files[0]}")
    print(f"Sample last file:  {generated_files[-1]}")

if __name__ == "__main__":
    main()
