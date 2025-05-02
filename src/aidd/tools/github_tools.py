import http.client
import json
import os
from typing import Any, Dict, List
from mcp.types import TextContent, ErrorData

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


def create_pull_request_review_tool() -> Dict[str, Any]:
    return {
        "name": "create_pull_request_review",
        "description": "Create a review for a pull request. Use this to approve, request changes, or comment on a PR. You can also submit code review comments.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pull_number": {"type": "number", "description": "Pull request number"},
                "event": {"type": "string", "description": "Review action: APPROVE, REQUEST_CHANGES, or COMMENT"},
                "body": {"type": "string", "description": "Text of the review (optional)", "nullable": True},
                "comments": {"type": "array", "items": {"type": "object"}, "description": "Array of review comments (optional)", "nullable": True},
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


def get_pull_request_files_tool() -> Dict[str, Any]:
    return {
        "name": "get_pull_request_files",
        "description": "Retrieves the list of files changed in a GitHub pull request. "
        "WHEN TO USE: When you need to examine which files were modified, added, or deleted in a specific pull request. "
        "This is useful for code review, understanding the scope of changes, or analyzing the impact of a pull request. "
        "WHEN NOT TO USE: When you need to view the actual content changes within files, create or modify pull requests, "
        "or when you're interested in other pull request metadata such as comments or reviews. "
        "RETURNS: A formatted markdown response containing a list of all files changed in the pull request, including "
        "the filename, status (added, modified, removed), and change statistics (additions and deletions).",
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
                if len(patch) < 500:  # Only include patch if it's reasonably sized
                    files_info += f"```diff\n{patch}\n```\n"
                else:
                    files_info += f"   - [Patch too large to display - view on GitHub]\n"
            
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
