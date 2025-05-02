import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any
import mcp.types as types
from .github_tools import handle_get_issue, handle_create_pull_request_review, handle_get_pull_request_files


@pytest.mark.asyncio
async def test_handle_create_pull_request_review_missing_params():
    """Return error if required args missing"""
    result = await handle_create_pull_request_review({"repo": "repo", "pull_number": 1, "event": "COMMENT"})
    assert isinstance(result, list)
    assert "Missing required parameters" in result[0].text

@pytest.mark.asyncio
async def test_handle_create_pull_request_review_success():
    mock_response = MagicMock()
    mock_response.status = 201
    mock_response.read.return_value = b'{"id": 123, "body": "Review posted!", "event": "COMMENT"}'

    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.return_value.getresponse.return_value = mock_response
        result = await handle_create_pull_request_review({
            "owner": "test",
            "repo": "repo",
            "pull_number": 1,
            "event": "COMMENT",
            "body": "Nice work!"
        })
        assert isinstance(result, list)
        assert "Pull request review created" in result[0].text
        assert "Review posted" in result[0].text

@pytest.mark.asyncio
async def test_handle_create_pull_request_review_api_error():
    mock_response = MagicMock()
    mock_response.status = 422
    mock_response.reason = "Unprocessable Entity"
    mock_response.read.return_value = b'{"message": "Validation Failed"}'
    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.return_value.getresponse.return_value = mock_response
        result = await handle_create_pull_request_review({
            "owner": "test",
            "repo": "repo",
            "pull_number": 1,
            "event": "COMMENT",
            "body": "invalid"
        })
        assert isinstance(result, list)
        assert "Error creating pull request review" in result[0].text
        assert "422" in result[0].text or "Unprocessable" in result[0].text

@pytest.mark.asyncio
async def test_handle_create_pull_request_review_exception():
    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.side_effect = Exception("oops")
        result = await handle_create_pull_request_review({
            "owner": "test",
            "repo": "repo",
            "pull_number": 1,
            "event": "COMMENT",
        })
        assert isinstance(result, list)
        assert "Exception occurred" in result[0].text

@pytest.mark.asyncio
async def test_handle_get_issue_missing_params():
    """Test that missing parameters return an error message"""
    result = await handle_get_issue({})
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"
    assert "Missing required parameters" in result[0].text


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

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Test Issue" in result[0].text
        assert "testuser" in result[0].text
        assert "bug" in result[0].text
        assert "assignee1" in result[0].text
        assert "Test issue body" in result[0].text


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

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "not found" in result[0].text.lower()


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

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error fetching issue" in result[0].text
        assert "500" in result[0].text


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

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error fetching issue" in result[0].text


@pytest.mark.asyncio
async def test_handle_get_pull_request_files_missing_params():
    """Test that missing parameters return an error message"""
    result = await handle_get_pull_request_files({})
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"
    assert "Missing required parameters" in result[0].text


@pytest.mark.asyncio
async def test_handle_get_pull_request_files_success():
    """Test successful pull request files retrieval"""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'''[
        {
            "filename": "src/example.py",
            "status": "modified",
            "additions": 10,
            "deletions": 2,
            "changes": 12,
            "blob_url": "https://github.com/owner/repo/blob/sha/src/example.py",
            "patch": "@@ -10,2 +10,10 @@ class Example:\\n-    def old_method(self):\\n-        pass\\n+    def new_method(self):\\n+        return 'new implementation'"
        },
        {
            "filename": "README.md",
            "status": "added",
            "additions": 15,
            "deletions": 0,
            "changes": 15,
            "blob_url": "https://github.com/owner/repo/blob/sha/README.md"
        },
        {
            "filename": "tests/old_test.py",
            "status": "removed",
            "additions": 0,
            "deletions": 25,
            "changes": 25,
            "blob_url": "https://github.com/owner/repo/blob/sha/tests/old_test.py"
        }
    ]'''

    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.return_value.getresponse.return_value = mock_response
        result = await handle_get_pull_request_files({
            "owner": "test",
            "repo": "repo",
            "pull_number": 1
        })

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Files Changed in Pull Request #1" in result[0].text
        assert "src/example.py" in result[0].text
        assert "README.md" in result[0].text
        assert "tests/old_test.py" in result[0].text
        assert "modified" in result[0].text
        assert "added" in result[0].text
        assert "removed" in result[0].text
        assert "Total Files Changed: 3" in result[0].text
        assert "Total Additions: +25" in result[0].text
        assert "Total Deletions: -27" in result[0].text


@pytest.mark.asyncio
async def test_handle_get_pull_request_files_empty():
    """Test handling of pull request with no files"""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'[]'

    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.return_value.getresponse.return_value = mock_response
        result = await handle_get_pull_request_files({
            "owner": "test",
            "repo": "repo",
            "pull_number": 1
        })

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "No files found in pull request #1" in result[0].text


@pytest.mark.asyncio
async def test_handle_get_pull_request_files_not_found():
    """Test handling of non-existent pull request"""
    mock_response = MagicMock()
    mock_response.status = 404

    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.return_value.getresponse.return_value = mock_response
        result = await handle_get_pull_request_files({
            "owner": "test",
            "repo": "repo",
            "pull_number": 999
        })

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "not found" in result[0].text.lower()


@pytest.mark.asyncio
async def test_handle_get_pull_request_files_error():
    """Test handling of API error"""
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.reason = "Internal Server Error"

    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.return_value.getresponse.return_value = mock_response
        result = await handle_get_pull_request_files({
            "owner": "test",
            "repo": "repo",
            "pull_number": 1
        })

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error fetching pull request files" in result[0].text
        assert "500" in result[0].text


@pytest.mark.asyncio
async def test_handle_get_pull_request_files_exception():
    """Test handling of unexpected exceptions"""
    with patch('http.client.HTTPSConnection') as mock_conn:
        mock_conn.side_effect = Exception("Connection failed")
        result = await handle_get_pull_request_files({
            "owner": "test",
            "repo": "repo",
            "pull_number": 1
        })

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error fetching pull request files" in result[0].text
