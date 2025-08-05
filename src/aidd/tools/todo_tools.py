import json
from .todo_store import todo_store
from mcp.types import TextContent


def todo_read_tool():
    """Define the todo_read tool."""
    return {
        "name": "todo_read",
        "description": "🚨 CRITICAL: MUST be called FIRST before ANY file/directory operations. WORKSPACE-BOUND REQUIREMENT. ⚠️ "
        "ENFORCE: Every read_file, write_file, edit_file, directory operation REQUIRES checking todos first. "
        "WORKSPACE ISOLATION: Each directory has isolated todo context - check current workspace todos before ANY action. "
        "FATAL ERROR if skipped: File operations without todo context violate workflow protocol. "
        "RETURNS: Active todo list for current directory/workspace. Essential for maintaining project state.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }


def todo_write_tool():
    """Define the todo_write tool."""
    return {
        "name": "todo_write",
        "description": "🚨 WORKSPACE PROTOCOL: Create/replace todo list when no active todos exist for current directory. ⚠️ "
        "TRIGGER: After todo_read returns empty list OR when starting new file/directory work. "
        "MANDATORY WORKFLOW: 1) todo_read first 2) If empty→todo_write 3) Then proceed with file operations. "
        "VIOLATION PREVENTION: Never perform write_file, edit_file, directory operations without active todo context. "
        "EXECUTION RULE: Create essential todos only. One 'in_progress' maximum. Focus on key milestones not micro-tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "Complete todo list for sequential execution. Tasks execute in array order.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique task identifier."},
                            "content": {"type": "string", "description": "Task description (required)."},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "Task status (only one 'in_progress' allowed)."},
                            "metadata": {"type": "object", "description": "Optional task metadata.", "additionalProperties": True},
                        },
                        "required": ["id", "content", "status"],
                        "additionalProperties": True,
                    },
                }
            },
            "required": ["todos"],
        },
    }


def todo_update_tool():
    """Define the todo_update tool."""
    return {
        "name": "todo_update",
        "description": "🚨 WORKFLOW ENFORCEMENT: Update todo status during file/directory operations. REQUIRED after each task. ⚠️ "
        "PROTOCOL: Mark 'in_progress' when starting task, 'completed' when finished. Update after EVERY file operation. "
        "CRITICAL SYNC: Todo status must reflect actual work progress. Failure to update breaks workspace integrity. "
        "SEQUENTIAL RULE: Only one task 'in_progress' at a time. Complete current before starting next.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "string", "description": "Todo ID to update."},
                "updates": {
                    "type": "object",
                    "description": "Fields to update (content, status, metadata).",
                    "properties": {
                        "content": {"type": "string", "description": "New task description."},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "New task status."},
                        "metadata": {"type": "object", "description": "Additional task data.", "additionalProperties": True},
                    },
                    "additionalProperties": True,
                },
            },
            "required": ["todo_id", "updates"],
        },
    }


async def handle_todo_read(arguments: dict) -> list[TextContent]:
    """Handle reading todos from storage."""
    try:
        todos = todo_store.read_todos()

        result = {"todos": todos, "count": len(todos), "workspace": str(todo_store.workspace_path)}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_result = {"error": {"code": "READ_ERROR", "message": f"Failed to read todos: {str(e)}"}}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


async def handle_todo_write(arguments: dict) -> list[TextContent]:
    """Handle writing todos to storage."""
    try:
        todos = arguments.get("todos", [])

        if not isinstance(todos, list):
            raise ValueError("Todos must be provided as a list")

        count = todo_store.write_todos(todos)

        result = {"success": True, "count": count, "workspace": str(todo_store.workspace_path)}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_result = {"error": {"code": "VALIDATION_ERROR" if "validation" in str(e).lower() or "invalid" in str(e).lower() or "duplicate" in str(e).lower() else "WRITE_ERROR", "message": str(e)}}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


async def handle_todo_update(arguments: dict) -> list[TextContent]:
    """Handle updating a specific todo."""
    try:
        todo_id = arguments.get("todo_id")
        updates = arguments.get("updates", {})

        if not todo_id:
            raise ValueError("todo_id is required")

        if not isinstance(updates, dict):
            raise ValueError("Updates must be provided as a dictionary")

        if not updates:
            raise ValueError("Updates cannot be empty")

        result = todo_store.update_todo(todo_id, updates)
        result["success"] = True
        result["workspace"] = str(todo_store.workspace_path)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_result = {"error": {"code": "VALIDATION_ERROR" if "validation" in str(e).lower() or "invalid" in str(e).lower() or "not found" in str(e).lower() else "UPDATE_ERROR", "message": str(e)}}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
