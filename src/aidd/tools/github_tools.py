import http.client
import json
import os
from typing import Any, Dict, List
from mcp.types import TextContent


def list_pull_requests_tool() -> Dict[str, Any]:
    return {
        "name": "list_pull_requests",
        "description": "List and filter repository pull requests",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "state": {
                    "type": "string",
                    "description": "Filter by pull request state: open, closed, or all",
                    "enum": ["open", "closed", "all"],
                    "default": "open"
                },
                "head": {
                    "type": "string",
                    "description": "Filter by head user/org and branch name (user:ref-name or org:ref-name)",
                    "nullable": True
                },
                "base": {
                    "type": "string",
                    "description": "Filter by base branch name",
                    "nullable": True
                },
                "sort": {
                    "type": "string",
                    "description": "How to sort the results",
                    "enum": ["created", "updated", "popularity", "long-running"],
                    "default": "created"
                },
                "direction": {
                    "type": "string",
                    "description": "Sort direction: asc or desc",
                    "enum": ["asc", "desc"],
                    "default": "desc"
                },
                "per_page": {
                    "type": "number",
                    "description": "Results per page (max 100)",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 100
                }
            },
            "required": ["owner", "repo"]
        },
    }

def create_pull_request_review_tool() -> Dict[str, Any]:
    return {
        "name": "create_pull_request_review",
        "description": "Create a review for a pull request.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pull_number": {"type": "number", "description": "Pull request number"},
                "event": {"type": "string", "description": "Review action: APPROVE, REQUEST_CHANGES, or COMMENT"},
                "body": {"type": "string", "description": "Text of the review (optional)", "nullable": True},
                "comments": {"type": "array", "items": {"type": "object"}, "description": "Array of review comments (optional) use this for inline comments", "nullable": True},
                "commit_id": {"type": "string", "description": "SHA of commit to review (optional)", "nullable": True},
            },
            "required": ["owner", "repo", "pull_number", "event"]
        },
    }

# Handler for creating a pull request review
async def handle_create_pull_request_review(args: Dict[str, Any]) -> List[TextContent]:
    owner = args.get("owner")
    repo = args.get("repo")
    pull_number = args.get("pull_number")
    event = args.get("event")
    body_value = args.get("body")
    comments_value = args.get("comments")
    commit_id = args.get("commit_id")

    if not all([owner, repo, pull_number, event]):
        return [TextContent(type="text", text="Error: Missing required parameters: owner, repo, pull_number, event.")]

    path = f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
    conn = None
    try:
        conn = http.client.HTTPSConnection("api.github.com")
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Python-MCP-Server",
        }
        if token := os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"token {token}"

        payload = {"event": event}
        if body_value:
            payload["body"] = body_value
        if commit_id:
            payload["commit_id"] = commit_id
        if comments_value:
            payload["comments"] = comments_value

        conn.request("POST", path, body=json.dumps(payload), headers=headers)
        response = conn.getresponse()
        response_body = response.read()
        if response.status not in (200, 201):
            return [TextContent(type="text", text=f"Error creating pull request review: {response.status} {response.reason}\n{response_body.decode()}")]
        review_data = json.loads(response_body)
        return [TextContent(type="text", text=f"Pull request review created: {json.dumps(review_data, indent=2)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Exception occurred: {str(e)}")]
    finally:
        if conn:
            conn.close()

def get_pull_request_files_tool() -> Dict[str, Any]:
    return {
        "name": "get_pull_request_files",
        "description": "Retrieves the list of files changed in a GitHub pull request.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner"
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name"
                },
                "pull_number": {
                    "type": "number",
                    "description": "Pull request number"
                }
            },
            "required": ["owner", "repo", "pull_number"]
        },
    }

async def handle_get_pull_request_files(args: Dict[str, Any]) -> List[TextContent]:
    owner = args.get("owner")
    repo = args.get("repo")
    pull_number = args.get("pull_number")

    if not all([owner, repo, pull_number]):
        return [TextContent(type="text", text="Error: Missing required parameters. Required parameters are owner, repo, and pull_number.")]

    # GitHub API URL for PR files
    path = f"/repos/{owner}/{repo}/pulls/{pull_number}/files"
    conn = None

    try:
        # Create connection
        conn = http.client.HTTPSConnection("api.github.com")

        # Set headers
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Python-MCP-Server"
        }

        # Add GitHub token if available
        if token := os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"token {token}"

        # Make request
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        if response.status == 404:
            return [TextContent(type="text", text=f"Pull request #{pull_number} not found in repository {owner}/{repo}. "
                                "Please set GITHUB_TOKEN environment variable if you are searching for private repositories.")]

        if response.status != 200:
            return [TextContent(type="text", text=f"Error fetching pull request files: {response.status} {response.reason}")]

        # Read and parse response
        files_data = json.loads(response.read())

        # Format the files data for display
        if not files_data:
            return [TextContent(type="text", text=f"No files found in pull request #{pull_number}.")]

        files_info = f"# Files Changed in Pull Request #{pull_number}\n\n"

        for file in files_data:
            filename = file.get("filename", "Unknown file")
            status = file.get("status", "unknown")
            additions = file.get("additions", 0)
            deletions = file.get("deletions", 0)
            changes = file.get("changes", 0)

            status_emoji = "🆕" if status == "added" else "✏️" if status == "modified" else "🗑️" if status == "removed" else "📄"
            files_info += f"{status_emoji} **{filename}** ({status})\n"
            files_info += f"   - Additions: +{additions}, Deletions: -{deletions}, Total Changes: {changes}\n"

            # Add file URL if available
            if blob_url := file.get("blob_url"):
                files_info += f"   - [View File]({blob_url})\n"

            # Add patch information if available and not too large
            if patch := file.get("patch"):
                files_info += f"```diff\n{patch}\n```\n"

            files_info += "\n"

        # Add summary statistics
        total_files = len(files_data)
        total_additions = sum(file.get("additions", 0) for file in files_data)
        total_deletions = sum(file.get("deletions", 0) for file in files_data)

        files_info += f"\n## Summary\n"
        files_info += f"- Total Files Changed: {total_files}\n"
        files_info += f"- Total Additions: +{total_additions}\n"
        files_info += f"- Total Deletions: -{total_deletions}\n"
        files_info += f"- Total Changes: {total_additions + total_deletions}\n"

        return [TextContent(type="text", text=files_info)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error fetching pull request files: {str(e)}")]
    finally:
        if conn is not None:
            conn.close()

async def handle_list_pull_requests(args: Dict[str, Any]) -> List[TextContent]:
    owner = args.get("owner")
    repo = args.get("repo")
    state = args.get("state", "open")
    head = args.get("head")
    base = args.get("base")
    sort = args.get("sort", "created")
    direction = args.get("direction", "desc")
    per_page = args.get("per_page", 30)

    # Validate required parameters
    if not all([owner, repo]):
        return [TextContent(type="text", text="Error: Missing required parameters. Required parameters are owner and repo.")]

    # Build query parameters
    query_params = f"state={state}&sort={sort}&direction={direction}&per_page={per_page}"
    if head:
        query_params += f"&head={head}"
    if base:
        query_params += f"&base={base}"

    # GitHub API URL
    path = f"/repos/{owner}/{repo}/pulls?{query_params}"
    conn = None

    try:
        # Create connection
        conn = http.client.HTTPSConnection("api.github.com")

        # Set headers
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Python-MCP-Server"
        }

        # Add GitHub token if available
        if token := os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"token {token}"

        # Make request
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        if response.status == 404:
            return [TextContent(type="text", text=f"Repository {owner}/{repo} not found. "
                                "Please set GITHUB_TOKEN environment variable if you are searching for private repositories.")]

        if response.status != 200:
            return [TextContent(type="text", text=f"Error fetching pull requests: {response.status} {response.reason}")]

        # Read and parse response
        pr_data = json.loads(response.read())

        # Handle empty results
        if not pr_data:
            status_label = "open" if state == "open" else (
                "closed" if state == "closed" else "matching your criteria")
            return [TextContent(type="text", text=f"No {status_label} pull requests found in repository {owner}/{repo}.")]

        # Format the pull requests data for display
        pr_info = f"# Pull Requests in {owner}/{repo} ({state})\n\n"

        # Create a table header
        pr_info += "| Number | Title | State | Creator | Head → Base | Created At |\n"
        pr_info += "|--------|-------|-------|---------|-------------|------------|\n"

        for pr in pr_data:
            number = pr.get("number", "N/A")
            title = pr.get("title", "No title")
            pr_state = pr.get("state", "unknown")
            creator = pr.get("user", {}).get("login", "unknown")
            created_at = pr.get("created_at", "unknown")

            # Get branch information
            head_branch = f"{pr.get('head', {}).get('label', 'unknown')}"
            base_branch = f"{pr.get('base', {}).get('label', 'unknown')}"
            branch_info = f"{head_branch} → {base_branch}"

            # Add row to table
            pr_info += f"| [{number}]({pr.get('html_url', '')}) | {title} | {pr_state} | {creator} | {branch_info} | {created_at} |\n"

        # Add summary
        pr_info += f"\n\n**Total pull requests found: {len(pr_data)}**\n"
        pr_info += f"View all pull requests: https://github.com/{owner}/{repo}/pulls\n"

        return [TextContent(type="text", text=pr_info)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error fetching pull requests: {str(e)}")]
    finally:
        if conn is not None:
            conn.close()
