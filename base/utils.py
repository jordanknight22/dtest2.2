import pandas as pd
import numpy as np
from .models import PetRates
from collections import defaultdict
from django.db import transaction

cover_limits = {
    "Bronze": 2250,
    "Silver": 3000,
    "Gold": 4000,
    "Prime": 2500,
    "Premier": 4000,
    "Premier Plus": 8000
}

def merge_nested_structures(base_dict, new_dict):
    """
    Recursively merges new_dict into base_dict:
    pet_type -> scheme -> factor_name
    """
    for pet_type, schemes in new_dict.items():
        for scheme, factors in schemes.items():
            if pet_type not in base_dict:
                base_dict[pet_type] = {}
            if scheme not in base_dict[pet_type]:
                base_dict[pet_type][scheme] = {}
            base_dict[pet_type][scheme].update(factors)
    return base_dict

def parse_rates_excel(file_path, sheet_name, header_keyword, header_keyword2, value_field, pet_type_filter=None):
    """
    Universal Excel parser for rating data.
    Handles:
      • Single-row and multi-row labeled rates
      • Dual headers (e.g. Animal Age + Animal Gender)
    Returns a list of dicts:
      pet_type, scheme, <value_field>, limit
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    print(f"✅ Loaded sheet '{sheet_name}' with shape {df.shape}")

    # --- Helper to find header row ---
    def find_row(keyword):
        matches = df[df.apply(lambda r: r.astype(str).str.contains(keyword, case=False, na=False).any(), axis=1)]
        if matches.empty:
            raise ValueError(f"❌ Could not find '{keyword}' in sheet '{sheet_name}'.")
        print(f"🔍 Found '{keyword}' at row {matches.index[0]}")
        return matches.index[0]

    # --- Identify header rows safely ---
    animal_row_idx = find_row("animal")
    cover_row_idx = find_row("cover name")
    header_idx = find_row(header_keyword)

    # Try to find the optional second header
    if header_keyword2 is not None:
        try:
            header_idx2 = find_row(header_keyword2)
            print(f"🔍 Found second header '{header_keyword2}' at row {header_idx2}")
        except ValueError:
            header_idx2 = None
            print(f"⚠️ '{header_keyword2}' not found — continuing with single header")
    else:
        header_idx2 = None

    # --- Column setup ---
    start_col = df.iloc[animal_row_idx].first_valid_index() + 1
    end_col = df.iloc[animal_row_idx].last_valid_index() + 1
    col_positions = list(range(start_col, end_col))
    animals = df.iloc[animal_row_idx, col_positions].astype(str).replace("", np.nan).ffill()
    covers = df.iloc[cover_row_idx, col_positions].astype(str).replace("", np.nan).ffill()
    # --- Identify label area ---
    start_idx = header_idx + 1
    end_idx = start_idx
    while end_idx < len(df) and not df.iloc[end_idx].isna().all():
        end_idx += 1

    data_slice = df.iloc[start_idx:end_idx, :]

    # --- Detect first populated column ---
    first_populated_col = data_slice.apply(lambda col: col.first_valid_index(), axis=0).dropna()
    if first_populated_col.empty:
        raise ValueError("No populated column found for labels")
    label_col_idx = int(first_populated_col.index[0])

    # --- Extract labels ---
    label_col = df.iloc[start_idx:end_idx, label_col_idx].astype(str).str.strip()
    print(f"🔹 Label column (from col {label_col_idx}): {list(label_col)}")

    # --- Combine with second header if present ---
    if header_idx2:
        # Find second label column
        start_idx2 = header_idx2 + 1
        end_idx2 = start_idx2 + len(label_col)
        second_label_col = df.iloc[start_idx2:end_idx2, label_col_idx+1].astype(str).str.strip()
        label_col = [f"{b}: {a}" for a, b in zip(label_col, second_label_col)]
        print(f"🧩 Combined label column: {label_col}")

    # --- Map labels to normalized options (copay support) ---
    label_map = {}
    for i, label in enumerate(label_col):
        if value_field == "copay" and label in ["0", "0%"]:
            label_map[i] = "no"
        elif value_field == "copay" and label in ["0.2", "20%"]:
            label_map[i] = "yes"
        else:
            label_map[i] = label.lower()
    print(f"🔹 Label map: {label_map}")

    # --- Detect multi-row ---
    is_multi_row = len(label_map) > 1
    print(f"🔹 Detected multi-row: {is_multi_row}")

    table_rows = []

    if is_multi_row:
        values_rows = df.iloc[header_idx + 1 : header_idx + 1 + len(label_map), col_positions]

        for rel_idx, pet_type in enumerate(animals):
            scheme = str(covers.iloc[rel_idx]).strip()
            if pet_type_filter and pet_type.lower() != pet_type_filter.lower():
                continue

            rates_dict = {}
            for row_idx in range(values_rows.shape[0]):
                cell_val = values_rows.iloc[row_idx, rel_idx]
                if isinstance(cell_val, str) and cell_val.strip().lower() == "decline":
                    val = 999
                else:
                    try:
                        val = float(cell_val)
                    except (ValueError, TypeError):
                        val = 0
                rates_dict[label_map[row_idx]] = val

            table_rows.append({
                'pet_type': pet_type.lower(),
                'scheme': scheme,
                value_field: rates_dict,
                'limit': cover_limits.get(scheme, 0) if 'cover_limits' in globals() else 0
            })

    else:
        values_row = df.iloc[header_idx + 1, col_positions]
        for rel_idx, pet_type in enumerate(animals):
            scheme = str(covers.iloc[rel_idx]).strip()
            try:
                val = float(values_row.iloc[rel_idx])
            except (ValueError, TypeError):
                val = None
            table_rows.append({
                'pet_type': pet_type.lower(),
                'scheme': scheme,
                value_field: val,
                'limit': cover_limits.get(scheme, 0) if 'cover_limits' in globals() else 0
            })

    print("✅ Finished parsing table rows.")
    return table_rows


def build_nested_structure(table_rows, factor_name):
    """
    Converts a flat list of rows into a nested dict:
        pet_type -> scheme -> factor_name -> rate(s)
    Handles both single-value (base_rate) and dict (copay, multipet) cases.
    """
    result = defaultdict(lambda: defaultdict(dict))

    for row in table_rows:
        pet_type = row['pet_type'].lower()
        scheme = row['scheme'].lower().replace(" ", "_")
        factor_value = row.get(factor_name)

        if isinstance(factor_value, dict):
            # Example: copay = {'yes': 0.8, 'no': 1.0}
            result[pet_type][scheme][factor_name] = factor_value
        else:
            # Example: base_rate = 1.25
            result[pet_type][scheme][factor_name] = factor_value

        # Always include limit if available
        if 'limit' in row:
            result[pet_type][scheme]['limit'] = row['limit']

    return result


def save_nested_rates_to_db(nested_rates):
    """
    Save parsed nested rates into PetRates table.
    Handles both single-value and multi-option factors (e.g., yes/no).
    Uses bulk_create for efficiency.
    """
    records = []

    for pet_type, schemes in nested_rates.items():
        for scheme, factors in schemes.items():
            scheme_name = scheme.replace("_", " ").title()
            limit_val = cover_limits.get(scheme_name, 0)

            for factor_name, value in factors.items():
                if factor_name == "limit":
                    continue

                # Case 1: single numeric rate
                if isinstance(value, (int, float)) or value is None:
                    rate_val = float(value) if value is not None else 0.0
                    records.append(
                        PetRates(
                            pet_type=pet_type,
                            scheme=scheme,
                            factor=factor_name,
                            option=None,
                            rate=rate_val,
                            limit=limit_val,
                        )
                    )

                # Case 2: dictionary of options (yes/no etc.)
                elif isinstance(value, dict):
                    for option, rate in value.items():
                        if rate in [None, ""]:
                            continue
                        try:
                            rate_val = float(rate)
                        except (ValueError, TypeError):
                            rate_val = 0.0

                        records.append(
                            PetRates(
                                pet_type=pet_type,
                                scheme=scheme,
                                factor=factor_name,
                                option=option,
                                rate=rate_val,
                                limit=limit_val,
                            )
                        )

    # ✅ Bulk save all at once (faster than many update_or_create calls)
    with transaction.atomic():
        PetRates.objects.all().delete()
        PetRates.objects.bulk_create(records)