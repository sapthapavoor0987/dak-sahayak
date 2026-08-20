"""
Server-side validation engine for India Post Account Opening Forms.
"""

import json
import os
import re

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")

def load_scheme_config(scheme="ppf", language="en"):
    config_filename = f"{scheme.lower()}_{language.lower()}.json"
    config_path = os.path.join(CONFIG_DIR, config_filename)
    if not os.path.exists(config_path):
        fallback_path = os.path.join(CONFIG_DIR, "ppf_en.json")
        if os.path.exists(fallback_path):
            with open(fallback_path, "r", encoding="utf-8") as f:
                return json.load(f)
        raise FileNotFoundError(f"Configuration file {config_filename} not found.")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_form_data(scheme="ppf", language="en", data=None):
    if not data or not isinstance(data, dict):
        return {
            "is_valid": False,
            "error_type": "empty_payload",
            "message": "Form payload data is required.",
            "missing_fields": ["all"],
            "invalid_fields": []
        }

    try:
        config = load_scheme_config(scheme, language)
    except Exception as e:
        return {
            "is_valid": False,
            "error_type": "config_error",
            "message": str(e),
            "missing_fields": [],
            "invalid_fields": []
        }

    required = config.get("required_fields", [])
    rules = config.get("validation_rules", {})
    missing_fields = []
    invalid_fields = []

    # 1. Check Required Fields
    for field in required:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing_fields.append(field)

    # 2. Check Validation Rules
    for field, rule in rules.items():
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            continue

        rule_type = rule.get("type")
        if rule_type == "regex":
            pattern = rule.get("pattern")
            if pattern and not re.match(pattern, str(val).strip(), re.IGNORECASE):
                invalid_fields.append({
                    "field": field,
                    "value": str(val),
                    "error": rule.get("error_message", f"Invalid format for {field}")
                })
        elif rule_type == "numeric":
            try:
                num_val = float(str(val).replace(",", "").strip())
                min_v = rule.get("min_val")
                max_v = rule.get("max_val")
                if min_v is not None and num_val < min_v:
                    invalid_fields.append({
                        "field": field,
                        "value": val,
                        "error": rule.get("error_message", f"Value must be at least {min_v}")
                    })
                elif max_v is not None and num_val > max_v:
                    invalid_fields.append({
                        "field": field,
                        "value": val,
                        "error": rule.get("error_message", f"Value cannot exceed {max_v}")
                    })
            except (ValueError, TypeError):
                invalid_fields.append({
                    "field": field,
                    "value": val,
                    "error": rule.get("error_message", f"{field} must be a valid number")
                })
        elif rule_type == "string":
            min_l = rule.get("min_length", 1)
            max_l = rule.get("max_length", 255)
            s_val = str(val).strip()
            if len(s_val) < min_l or len(s_val) > max_l:
                invalid_fields.append({
                    "field": field,
                    "value": val,
                    "error": rule.get("error_message", f"Length must be between {min_l} and {max_l} characters")
                })

    is_valid = len(missing_fields) == 0 and len(invalid_fields) == 0

    return {
        "is_valid": is_valid,
        "scheme": scheme,
        "language": language,
        "missing_fields": missing_fields,
        "invalid_fields": invalid_fields,
        "message": "Form data is valid." if is_valid else f"Validation failed with {len(missing_fields)} missing and {len(invalid_fields)} invalid fields."
    }
