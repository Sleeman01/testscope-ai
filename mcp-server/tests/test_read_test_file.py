from pathlib import Path
from tools.read_test_file import read_test_file

def test_reads_full_small_file(tmp_path):
    root = tmp_path / "workspace_root"
    (root / "a1").mkdir(parents=True)
    (root / "a1" / "test_x.py").write_text("def test_x():\n    assert True\n")
    result = read_test_file("a1", "test_x.py", root=root)
    assert "def test_x" in result["content"]
    assert result["truncated"] is False

def test_truncates_large_file(tmp_path):
    root = tmp_path / "workspace_root"
    (root / "a1").mkdir(parents=True)
    big = "x = 1\n" * 20000  # well over 50KB
    (root / "a1" / "test_big.py").write_text(big)
    result = read_test_file("a1", "test_big.py", root=root)
    assert result["truncated"] is True
    assert len(result["content"].encode()) <= 50 * 1024
