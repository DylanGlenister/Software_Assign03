def filter_dict(data: dict, valid_keys: set, /, *, log_invalid: bool = True) -> dict:
    filtered = {k: v for k, v in data.items() if k in valid_keys}
    if log_invalid:
        invalid = set(data.keys()) - valid_keys
        for key in invalid:
            print(f"Ignored invalid field: {key}")
    return filtered
