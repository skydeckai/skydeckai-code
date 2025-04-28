import http.client
import json
import os
from typing import Any, Dict, List
from mcp.types import TextContent

# Tool definition


def get_issue_tool() -> Dict[str, Any]:
    return {
        "name": "get_issue",
        "description": "Retrieves detailed information about a GitHub issue from a repository. "
        "WHEN TO USE: When you need to examine issue details, track progress, understand requirements, "
        "or gather context about a specific problem or feature request. Ideal for reviewing issue descriptions, "
        "checking status, identifying assignees, or understanding the full context of a development task. "
        "WHEN NOT TO USE: When you need to create new issues, update existing ones, or interact with pull requests. "
        "For those operations, use the appropriate GitHub API endpoints or tools. "
        "RETURNS: A formatted markdown response containing the issue's title, number, state, creator, creation date, "
        "last update date, URL, labels, assignees, and full description. The response is structured for easy reading "
        "and includes all relevant metadata to understand the issue's context and current status.",
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
                "issue_number": {
                    "type": "number",
                    "description": "Issue number"
                }
            },
            "required": ["owner", "repo", "issue_number"]
        },
    }

# Tool handler


async def handle_get_issue(args: Dict[str, Any]) -> List[TextContent]:
    owner = args.get("owner")
    repo = args.get("repo")
    issue_number = args.get("issue_number")

    if not all([owner, repo, issue_number]):
        return [TextContent(type="text", text="Error: Missing required parameters. Required parameters are owner, repo, and issue_number.")]

    # GitHub API URL
    path = f"/repos/{owner}/{repo}/issues/{issue_number}"
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
            return [TextContent(type="text", text=f"Issue #{issue_number} not found in repository {owner}/{repo}. "
                                "Please set GITHUB_TOKEN environment variable if you are searching for private repositories.")]

        if response.status != 200:
            return [TextContent(type="text", text=f"Error fetching issue: {response.status} {response.reason}")]

        # Read and parse response
        issue_data = json.loads(response.read())

        # Format the issue data for display
        issue_info = (
            f"# Issue #{issue_data.get('number')}: {issue_data.get('title')}\n\n"
            f"**State:** {issue_data.get('state')}\n"
            f"**Created by:** {issue_data.get('user', {}).get('login')}\n"
            f"**Created at:** {issue_data.get('created_at')}\n"
            f"**Updated at:** {issue_data.get('updated_at')}\n"
            f"**URL:** {issue_data.get('html_url')}\n\n"
        )

        # Add labels if they exist
        if labels := issue_data.get('labels', []):
            label_names = [label.get('name') for label in labels]
            issue_info += f"**Labels:** {', '.join(label_names)}\n\n"

        # Add assignees if they exist
        if assignees := issue_data.get('assignees', []):
            assignee_names = [assignee.get('login') for assignee in assignees]
            issue_info += f"**Assignees:** {', '.join(assignee_names)}\n\n"

        # Add body if it exists
        if body := issue_data.get('body'):
            issue_info += f"## Description\n\n{body}\n\n"

        return [TextContent(type="text", text=issue_info)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error fetching issue: {str(e)}")]
    finally:
        if conn is not None:
            conn.close()
