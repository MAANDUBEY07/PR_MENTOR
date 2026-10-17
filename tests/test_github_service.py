import pytest
from app.github_service.parser import InvalidPullRequestURL, parse_pull_request_url

def test_parse_valid_pull_request_url():
    assert parse_pull_request_url("https://github.com/acme/widgets/pull/12") == ("acme", "widgets", 12)

@pytest.mark.parametrize("url", ["http://github.com/a/b/pull/1", "https://example.com/a/b/pull/1", "https://github.com/a/b/issues/1", "https://github.com/a/b/pull/0", "https://user:pass@github.com/a/b/pull/1", "https://github.com:443/a/b/pull/1"])
def test_rejects_unsafe_or_invalid_url(url):
    with pytest.raises(InvalidPullRequestURL):
        parse_pull_request_url(url)
