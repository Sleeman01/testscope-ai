import pytest
from repository import InvalidRepositoryError, normalize_repository


@pytest.mark.parametrize("raw", [
    "https://github.com/Sleeman01/testscope-ai",
    "https://github.com/Sleeman01/testscope-ai.git",
    "http://github.com/Sleeman01/testscope-ai",
    "github.com/Sleeman01/testscope-ai",
    "git@github.com:Sleeman01/testscope-ai.git",
    "Sleeman01/testscope-ai",
])
def test_normalize_repository_accepts_all_known_forms(raw):
    assert normalize_repository(raw) == "Sleeman01/testscope-ai"

@pytest.mark.parametrize("raw", [
    "not-a-repo",
    "https://gitlab.com/owner/repo",
    "owner/repo/extra",
    "",
    "   ",
    "owner/",
    "/repo",
])
def test_normalize_repository_rejects_invalid_input(raw):
    with pytest.raises(InvalidRepositoryError, match="Invalid repository"):
        normalize_repository(raw)
