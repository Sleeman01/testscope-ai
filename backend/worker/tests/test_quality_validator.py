from app.nodes.quality_validator import quality_validator

def test_strips_fabricated_evidence_not_in_candidate_files():
    state = {
        "candidate_files": [{"path": "tests/test_login.py"}],
        "coverage_matrix": [
            {"criterion_id": "AC1", "status": "Covered",
             "evidence": ["tests/test_login.py::test_x", "tests/nonexistent.py::test_fake"],
             "explanation": "..."},
        ],
        "warnings": [],
    }
    result = quality_validator(state)
    evidence = result["coverage_matrix"][0]["evidence"]
    assert "tests/nonexistent.py::test_fake" not in evidence
    assert "tests/test_login.py::test_x" in evidence
    assert any("fabricated" in w.lower() or "nonexistent.py" in w for w in result["warnings"])

def test_leaves_valid_evidence_untouched():
    state = {
        "candidate_files": [{"path": "tests/test_login.py"}],
        "coverage_matrix": [{"criterion_id": "AC1", "status": "Covered",
                              "evidence": ["tests/test_login.py::test_x"], "explanation": "..."}],
        "warnings": [],
    }
    result = quality_validator(state)
    assert result["coverage_matrix"][0]["evidence"] == ["tests/test_login.py::test_x"]
    assert result["warnings"] == []
