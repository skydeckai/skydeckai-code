import os

from mcp.types import TextContent
from .state import state


def get_allowed_directory_tool():
    """Define the get_allowed_directory tool."""
    return {
        "name": "get_allowed_directory",
        "description": "Get current allowed working directory. "
                      "USE: Understand workspace boundaries, verify file operation scope. "
                      "NOT: List directory contents (use list_directory). "
                      "RETURNS: Absolute path to workspace root",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }

def update_allowed_directory_tool():
    """Define the update_allowed_directory tool."""
    return {
            "name": "update_allowed_directory",
            "description": "Change allowed working directory. "
                        "USE: Switch projects, modify workspace boundaries. "
                        "NOT: Create subdirectories (use create_directory). "
                        "RETURNS: Confirmation of directory change",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory path (absolute, must exist). Examples: '/Users/username/projects', '~/Documents/code'."
                    }
                },
                "required": ["directory"]
            },
        }

async def handle_get_allowed_directory(arguments: dict):
    """Handle getting the allowed directory."""
    return [TextContent(
        type="text",
        text=f"Allowed directory: {state.allowed_directory}"
    )]

async def handle_update_allowed_directory(arguments: dict):
    """Handle updating the allowed directory."""
    directory = arguments.get("directory")
    if not directory:
        raise ValueError("directory must be provided")

    # Handle home directory expansion
    if directory.startswith("~"):
        directory = os.path.expanduser(directory)

    # Must be an absolute path
    if not os.path.isabs(directory):
        raise ValueError("Directory must be an absolute path")

    # Normalize the path
    directory = os.path.abspath(directory)

    # Verify directory exists
    if not os.path.isdir(directory):
        raise ValueError(f"Path is not a directory: {directory}")

    state.allowed_directory = directory
    return [TextContent(
        type="text",
        text=f"Successfully updated allowed directory to: {state.allowed_directory}"
    )]
