import pytest
import os
from typing import Dict, Any
from mcp.types import TextContent
from .github_tools import handle_get_issue


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
