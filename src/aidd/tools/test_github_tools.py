import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any
import mcp.types as types
from .github_tools import handle_get_issue


@pytest.mark.asyncio
async def test_handle_get_issue_missing_params():
    """Test that missing parameters return an error message"""
    result = await handle_get_issue({})
    assert result.type == "text"
    assert "Missing required parameters" in result.text


@pytest.mark.asyncio
async def test_handle_get_issue_success():
    """Test successful issue retrieval"""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'''{
        "number": 1,
        "title": "Test Issue",
        "state": "open",
        "user": {"login": "testuser"},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "html_url": "https://github.com/test/repo/issues/1",
        "body": "Test issue body",
        "labels": [{"name": "bug"}],
        "assignees": [{"login": "assignee1"}]
    }'''

    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.return_value.getresponse.return_value = mock_response
        result = await handle_get_issue({
            "owner": "test",
            "repo": "repo",
            "issue_number": 1
        })

        assert result.type == "text"
        assert "Test Issue" in result.text
        assert "testuser" in result.text
        assert "bug" in result.text
        assert "assignee1" in result.text
        assert "Test issue body" in result.text


@pytest.mark.asyncio
async def test_handle_get_issue_not_found():
    """Test handling of non-existent issue"""
    mock_response = MagicMock()
    mock_response.status = 404

    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.return_value.getresponse.return_value = mock_response
        result = await handle_get_issue({
            "owner": "test",
            "repo": "repo",
            "issue_number": 999
        })

        assert result.type == "text"
        assert "not found" in result.text.lower()


@pytest.mark.asyncio
async def test_handle_get_issue_error():
    """Test handling of API error"""
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.reason = "Internal Server Error"

    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.return_value.getresponse.return_value = mock_response
        result = await handle_get_issue({
            "owner": "test",
            "repo": "repo",
            "issue_number": 1
        })

        assert result.type == "text"
        assert "Error fetching issue" in result.text
        assert "500" in result.text


@pytest.mark.asyncio
async def test_handle_get_issue_exception():
    """Test handling of unexpected exceptions"""
    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.side_effect = Exception("Connection failed")
        result = await handle_get_issue({
            "owner": "test",
            "repo": "repo",
            "issue_number": 1
        })

        assert result.type == "text"
        assert "Error fetching issue" in result.text
        assert "Connection failed" in result.text
