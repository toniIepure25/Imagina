def compute_slope(rows: list[dict], key: str) -> float:
    values: list[float] = []
    for row in rows:
        v = row.get(key)
        if isinstance(v, (int, float)):
            values.append(float(v))
    if len(values) < 2:
        return 0.0
    return round((values[-1] - values[0]) / (len(values) - 1), 5)
