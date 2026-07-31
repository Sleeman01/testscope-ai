from pathlib import Path
from tools.extract_test_metadata import extract_test_metadata

FIXTURE = Path(__file__).parent / "fixtures" / "sample_test_file.py"

def test_extracts_pytest_function_with_fixture_and_markers():
    content = FIXTURE.read_text()
    result = extract_test_metadata(content)
    names = [t["name"] for t in result["tests"]]
    assert "test_login_rejects_invalid_password" in names
    entry = next(t for t in result["tests"] if t["name"] == "test_login_rejects_invalid_password")
    assert entry["framework"] == "pytest"
    assert "client" in entry["fixtures_used"]
    assert "pytest.mark.parametrize" in entry["decorators"]
    assert entry["assert_count"] >= 1
    assert "/api/login" in entry["string_literals"]

def test_ignores_non_test_functions():
    content = "def helper():\n    return 1\n"
    result = extract_test_metadata(content)
    assert result["tests"] == []
