import pytest
import os
from typing import Dict, Any
from mcp.types import TextContent
from .github_tools import handle_get_issue, handle_create_pull_request_review


@pytest.mark.asyncio
@pytest.mark.skipif("GITHUB_TOKEN" not in os.environ or not os.environ.get('GITHUB_TEST_REPO_OWNER') or not os.environ.get('GITHUB_TEST_REPO'), reason="Needs GITHUB_TOKEN, GITHUB_TEST_REPO_OWNER, and GITHUB_TEST_REPO env variables.")
async def test_handle_create_pull_request_review_real_api():
    """Integration test for creating a review (safe COMMENT event)."""
    owner = os.environ["GITHUB_TEST_REPO_OWNER"]
    repo = os.environ["GITHUB_TEST_REPO"]
    pr_num = int(os.environ.get("GITHUB_TEST_PR_NUMBER", "1"))  # Default to PR 1 if not set
    result = await handle_create_pull_request_review({
        "owner": owner,
        "repo": repo,
        "pull_number": pr_num,
        "event": "COMMENT",
        "body": "*Integration test comment*"
    })
    assert isinstance(result, list)
    assert any("review" in r.text.lower() for r in result)

@pytest.mark.asyncio
async def test_handle_get_issue_real_api():
    """Test the get_issue tool against the real GitHub API"""
    # Test with a well-known public repository and issue
    result = await handle_get_issue({
        "owner": "python",
        "repo": "cpython",
        "issue_number": 1
    })

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert "python" in result[0].text.lower()
    assert "cpython" in result[0].text.lower()


@pytest.mark.asyncio
async def test_handle_get_issue_not_found_real_api():
    """Test handling of non-existent issue against the real GitHub API"""
    result = await handle_get_issue({
        "owner": "python",
        "repo": "cpython",
        "issue_number": 999999999  # Very high number that shouldn't exist
    })

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_handle_get_issue_private_repo():
    """Test handling of private repository access"""
    result = await handle_get_issue({
        "owner": "github",
        "repo": "github",  # This is a private repository
        "issue_number": 1
    })

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert "error" in result[0].text.lower(
    ) or "not found" in result[0].text.lower()
