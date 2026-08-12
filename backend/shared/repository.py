import re

# Matches an explicit GitHub URL/SSH form: https://, http://, bare "github.com/", or
# git@github.com:. owner/repo segments must themselves be slash-free; an optional
# trailing ".git" and/or "/" is stripped.
_GITHUB_URL_RE = re.compile(
    r"^(?:https?://github\.com/|github\.com/|git@github\.com:)"
    r"(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$",
)
# Matches a bare "owner/repo" with no host/scheme.
_PLAIN_RE = re.compile(r"^(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)$")


class InvalidRepositoryError(ValueError):
    pass


def normalize_repository(raw: str) -> str:
    candidate = (raw or "").strip()
    match = _GITHUB_URL_RE.match(candidate) or _PLAIN_RE.match(candidate)
    if not match:
        raise InvalidRepositoryError(
            "Invalid repository: expected owner/repo or a GitHub URL",
        )
    return f"{match.group('owner')}/{match.group('repo')}"
