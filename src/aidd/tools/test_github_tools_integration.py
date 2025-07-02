import pytest
import os
from typing import Dict, Any
from mcp.types import TextContent
from .github_tools import handle_create_pull_request_review, handle_get_pull_request_files, handle_list_pull_requests


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
async def test_handle_get_pull_request_files_real_api():
    """Test the get_pull_request_files tool against the real GitHub API"""
    # Test with a well-known public repository and pull request
    result = await handle_get_pull_request_files({
        "owner": "python",
        "repo": "cpython",
        "pull_number": 1
    })

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert "Files Changed in Pull Request #1" in result[0].text
    
    # Check for summary section containing expected stats
    assert "Total Files Changed:" in result[0].text
    assert "Total Additions:" in result[0].text
    assert "Total Deletions:" in result[0].text


@pytest.mark.asyncio
async def test_handle_get_pull_request_files_not_found_real_api():
    """Test handling of non-existent pull request against the real GitHub API"""
    result = await handle_get_pull_request_files({
        "owner": "python",
        "repo": "cpython",
        "pull_number": 999999999  # Very high number that shouldn't exist
    })

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_handle_get_pull_request_files_private_repo():
    """Test handling of private repository access"""
    result = await handle_get_pull_request_files({
        "owner": "github",
        "repo": "github",  # This is a private repository
        "pull_number": 1
    })

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert "error" in result[0].text.lower() or "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_handle_list_pull_requests_real_api():
    """Test the list_pull_requests tool against the real GitHub API"""
    # Test with a well-known public repository
    result = await handle_list_pull_requests({
        "owner": "python",
        "repo": "cpython",
        "state": "open"
    })

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert "Pull Requests in python/cpython (open)" in result[0].text
    # Check for table headers
    assert "| Number | Title | State | Creator | Head → Base | Created At |" in result[0].text
    # Check for summary
    assert "Total pull requests found:" in result[0].text


@pytest.mark.asyncio
async def test_handle_list_pull_requests_closed_real_api():
    """Test the list_pull_requests tool with closed pull requests against the real GitHub API"""
    result = await handle_list_pull_requests({
        "owner": "python",
        "repo": "cpython",
        "state": "closed",
        "per_page": 10
    })

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert "Pull Requests in python/cpython (closed)" in result[0].text
    # Check for table headers
    assert "| Number | Title | State | Creator | Head → Base | Created At |" in result[0].text
    # Check for summary
    assert "Total pull requests found:" in result[0].text


@pytest.mark.asyncio
async def test_handle_list_pull_requests_filtered_real_api():
    """Test the list_pull_requests tool with filters against the real GitHub API"""
    result = await handle_list_pull_requests({
        "owner": "python",
        "repo": "cpython",
        "state": "open",
        "base": "main",
        "sort": "updated",
        "direction": "desc",
        "per_page": 5
    })

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert "Pull Requests in python/cpython (open)" in result[0].text


@pytest.mark.asyncio
async def test_handle_list_pull_requests_not_found_real_api():
    """Test handling of non-existent repository against the real GitHub API"""
    result = await handle_list_pull_requests({
        "owner": "python",
        "repo": "nonexistent_repo_name_abc123",  # This shouldn't exist
        "state": "open"
    })

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_handle_list_pull_requests_private_repo():
    """Test handling of private repository access"""
    result = await handle_list_pull_requests({
        "owner": "github",
        "repo": "github",  # This is a private repository
        "state": "open"
    })

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert "error" in result[0].text.lower() or "not found" in result[0].text.lower()
