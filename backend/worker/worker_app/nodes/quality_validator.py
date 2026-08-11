def quality_validator(state: dict) -> dict:
    known_paths = {f["path"] for f in state.get("candidate_files", [])}
    for entry in state.get("coverage_matrix", []):
        kept, dropped = [], []
        for item in entry.get("evidence", []):
            path = item.split("::")[0]
            (kept if path in known_paths else dropped).append(item)
        entry["evidence"] = kept
        for item in dropped:
            state.setdefault("warnings", []).append(f"Dropped fabricated evidence reference: {item}")
    return state
