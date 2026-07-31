import subprocess
from pathlib import Path

def make_bare_repo(tmp_path: Path) -> str:
    """Creates a local bare git repo with one test file, returns its file:// clone URL."""
    work = tmp_path / "work"
    work.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=work, check=True)
    (work / "tests").mkdir()
    (work / "tests" / "test_login.py").write_text(
        "def test_login_rejects_invalid_password():\n    assert True\n"
    )
    subprocess.run(["git", "add", "."], cwd=work, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=work, check=True)
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(work), str(bare)], check=True)
    return f"file://{bare}"
