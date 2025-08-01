import json
from .todo_store import todo_store
from mcp.types import TextContent


def todo_read_tool():
    """Define the todo_read tool."""
    return {
        "name": "todo_read",
        "description": "Read the current task list from the workspace-specific todo storage. "
        "MANDATORY: This tool MUST be called FIRST before ANY workspace operations including file reads, code analysis, development tasks, project creation, or directory manipulation. "
        "WORKSPACE-FIRST RULE: Every LLM interaction with workspaces, directories, projects, or repositories requires todo management. "
        "WHEN TO USE: Always when starting workspace operations - check task status, review pending/completed work, understand project context, pick up previous progress. "
        "Essential for: Project initialization, code development, file operations, debugging, testing, deployment, refactoring. "
        "WHEN NOT TO USE: Pure informational queries unrelated to workspace development. "
        "RETURNS: Sequential task list with status and metadata. Tasks execute in order - no priority system. "
        "Each workspace maintains isolated todo lists for project organization. "
        "CRITICAL: Bypassing this tool for workspace operations violates mandatory protocol. "
        "EXAMPLES: \n- Creating new projects: Read todos to check existing project structure tasks\n- Code development: Check current development phase and next sequential steps\n- File modifications: Understand task context before making changes\n- Project analysis: Review completed analysis and next investigation steps",
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
        "description": "Update the entire task list (complete replacement) for the current workspace. "
        "MANDATORY: This tool MUST be called when planning, adding, or reorganizing tasks during ANY workspace operations. "
        "WORKSPACE-FIRST RULE: All workspace development requires structured task management through sequential execution. "
        "WHEN TO USE: Task planning for new projects, adding development phases, reorganizing workflow, batch status updates. "
        "Sequential execution model: Tasks are completed in order, building upon previous work. No priority system - order determines execution. "
        "Essential for: Project planning, development workflows, feature implementation, debugging sequences, deployment phases. "
        "WHEN NOT TO USE: Single task updates (use todo_update), pure reading (use todo_read). "
        "RETURNS: Success status and task count. Enforces sequential execution (only one in-progress task). "
        "CRITICAL: Sequential task management is mandatory for all workspace development activities. "
        "EXAMPLES: \n- New project setup: Create sequential tasks for initialization, structure, dependencies\n- Feature development: Plan design, implementation, testing, documentation phases\n- Bug fixing: Create investigation, fix, test, validation sequence\n- Code refactoring: Plan analysis, changes, testing, cleanup steps",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "Complete list of todo items to replace the current list for sequential execution. Each todo must contain id, content, and status fields. Tasks execute in array order.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique identifier for the task. Must be unique across all todos."},
                            "content": {"type": "string", "description": "Task description or content. Cannot be empty."},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "Current status of the task. Only one task can be 'in_progress' at a time."},
                            "metadata": {"type": "object", "description": "Optional additional data for the task.", "additionalProperties": True},
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
        "description": "Update a specific todo item by ID for sequential workflow management. "
        "MANDATORY: This tool MUST be called when progressing through tasks during workspace operations. "
        "WORKSPACE-FIRST RULE: Task progress updates are required for all workspace development activities. "
        "WHEN TO USE: Mark tasks in-progress when starting, completed when finished, update content for clarification. "
        "Sequential workflow: Progress through tasks in order, maintaining single active task constraint. "
        "Essential for: Task status transitions, progress tracking, workflow advancement, content updates. "
        "WHEN NOT TO USE: Multiple task updates (use todo_write), adding new tasks (use todo_write). "
        "RETURNS: Updated todo with status counts showing workflow progress. "
        "Enforces sequential execution - only one task can be in-progress at any time. "
        "CRITICAL: Sequential progress tracking is mandatory for workspace development workflows. "
        "EXAMPLES: \n- Starting work: Update task from 'pending' to 'in_progress'\n- Completing work: Update task from 'in_progress' to 'completed'\n- Task refinement: Update content for better clarity\n- Workflow progression: Move to next sequential task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "string", "description": "The unique ID of the todo to update."},
                "updates": {
                    "type": "object",
                    "description": "Fields to update in the todo for sequential workflow. Can include content, status, or metadata.",
                    "properties": {
                        "content": {"type": "string", "description": "New task description or content."},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "New status of the task."},
                        "metadata": {"type": "object", "description": "Additional data for the task.", "additionalProperties": True},
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
