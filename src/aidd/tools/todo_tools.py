import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from mcp.types import TextContent
from .state import state


class TodoStore:
    """Manages todo persistence and operations."""

    def __init__(self):
        self._cached_store = None
        self._last_workspace = None

    @property
    def workspace_path(self) -> Path:
        """Get the current workspace directory."""
        return Path(state.allowed_directory)

    @property
    def todos_file_path(self) -> Path:
        """Get the path to the todos file."""
        return self.workspace_path / ".skydeckai-todos.json"

    def _detect_workspace_change(self) -> bool:
        """Check if workspace has changed since last access."""
        current_workspace = str(self.workspace_path)
        if self._last_workspace != current_workspace:
            self._last_workspace = current_workspace
            self._cached_store = None
            return True
        return False

    def _load_store(self) -> Dict[str, Any]:
        """Load todos from file with caching."""
        self._detect_workspace_change()

        if self._cached_store is not None:
            return self._cached_store

        if not self.todos_file_path.exists():
            self._cached_store = {"lastModified": datetime.now().isoformat(), "todos": []}
            return self._cached_store

        try:
            with open(self.todos_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cached_store = {"lastModified": data.get("lastModified", datetime.now().isoformat()), "todos": data.get("todos", [])}
                return self._cached_store
        except (json.JSONDecodeError, IOError, OSError):
            # Return empty store if file is corrupted
            self._cached_store = {"lastModified": datetime.now().isoformat(), "todos": []}
            return self._cached_store

    def _save_store(self, store: Dict[str, Any]) -> None:
        """Save todos to file atomically."""
        self.workspace_path.mkdir(exist_ok=True)

        # Write to temporary file first (atomic write)
        temp_path = self.todos_file_path.with_suffix(".json.tmp")

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(store, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(self.todos_file_path)

            # Update cache
            self._cached_store = store

            # Add to .gitignore if first time
            self._add_to_gitignore()

        except Exception:
            # Clean up temp file if something went wrong
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _add_to_gitignore(self) -> None:
        """Add todos file to .gitignore if not already present."""
        gitignore_path = self.workspace_path / ".gitignore"
        target_line = ".skydeckai-todos.json"

        # Check if already in .gitignore
        if gitignore_path.exists():
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    if target_line in f.read():
                        return
            except (IOError, OSError):
                pass

        # Add to .gitignore
        try:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                if gitignore_path.stat().st_size > 0:
                    f.write("\n")
                f.write(f"# SkyDeckAI todos\n{target_line}\n")
        except (IOError, OSError):
            pass  # Silently fail if can't write

    def read_todos(self) -> List[Dict[str, Any]]:
        """Read all todos from storage."""
        store = self._load_store()
        return store["todos"]

    def write_todos(self, todos: List[Dict[str, Any]]) -> int:
        """Write todos to storage with validation."""
        # Validate todos
        self._validate_todos(todos)

        # Process todos (add timestamps, etc.)
        processed_todos = []
        current_time = datetime.now().isoformat()

        for todo in todos:
            processed_todo = dict(todo)

            # Ensure required fields have defaults
            processed_todo.setdefault("id", self._generate_id())
            processed_todo.setdefault("status", "pending")
            processed_todo.setdefault("priority", "medium")
            processed_todo.setdefault("created_at", current_time)
            processed_todo["updated_at"] = current_time

            processed_todos.append(processed_todo)

        # Create new store
        new_store = {"lastModified": current_time, "todos": processed_todos}

        # Save to file
        self._save_store(new_store)

        return len(processed_todos)

    def update_todo(self, todo_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a specific todo by ID."""
        store = self._load_store()
        todos = store["todos"]
        
        # Find the todo to update
        todo_index = None
        for i, todo in enumerate(todos):
            if todo["id"] == todo_id:
                todo_index = i
                break
        
        if todo_index is None:
            raise ValueError(f"Todo with ID '{todo_id}' not found")
        
        # Create updated todo
        updated_todo = dict(todos[todo_index])
        updated_todo.update(updates)
        updated_todo["updated_at"] = datetime.now().isoformat()
        
        # Replace the todo in the list
        updated_todos = todos.copy()
        updated_todos[todo_index] = updated_todo
        
        # Validate the entire list with the update
        self._validate_todos(updated_todos)
        
        # Save updated list
        new_store = {"lastModified": datetime.now().isoformat(), "todos": updated_todos}
        self._save_store(new_store)
        
        # Return status counts
        pending_count = sum(1 for t in updated_todos if t["status"] == "pending")
        in_progress_count = sum(1 for t in updated_todos if t["status"] == "in_progress")
        completed_count = sum(1 for t in updated_todos if t["status"] == "completed")
        
        return {
            "updated_todo": updated_todo,
            "counts": {
                "pending": pending_count,
                "in_progress": in_progress_count,
                "completed": completed_count,
                "total": len(updated_todos)
            }
        }

    def _validate_todos(self, todos: List[Dict[str, Any]]) -> None:
        """Validate todos according to business rules."""
        if not isinstance(todos, list):
            raise ValueError("Todos must be a list")

        # Check for required fields and collect IDs
        required_fields = {"id", "content", "status", "priority"}
        seen_ids = set()
        in_progress_count = 0

        for i, todo in enumerate(todos):
            if not isinstance(todo, dict):
                raise ValueError(f"Todo at index {i} must be a dictionary")

            # Check required fields
            missing_fields = required_fields - set(todo.keys())
            if missing_fields:
                raise ValueError(f"Todo at index {i} missing required fields: {missing_fields}")

            # Validate ID uniqueness
            todo_id = todo["id"]
            if not isinstance(todo_id, str) or not todo_id.strip():
                raise ValueError(f"Todo at index {i} must have a non-empty string ID")

            if todo_id in seen_ids:
                raise ValueError(f"Duplicate todo ID found: {todo_id}")
            seen_ids.add(todo_id)

            # Validate status
            if todo["status"] not in ["pending", "in_progress", "completed"]:
                raise ValueError(f"Todo at index {i} has invalid status: {todo['status']}")

            if todo["status"] == "in_progress":
                in_progress_count += 1

            # Validate priority
            if todo["priority"] not in ["high", "medium", "low"]:
                raise ValueError(f"Todo at index {i} has invalid priority: {todo['priority']}")

            # Validate content
            if not isinstance(todo["content"], str) or not todo["content"].strip():
                raise ValueError(f"Todo at index {i} must have non-empty content")

        # Business rule: only one task can be in progress
        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress at a time")

    def _generate_id(self) -> str:
        """Generate a unique ID for a todo."""
        import uuid

        return str(uuid.uuid4())[:8]


# Global todo store instance
todo_store = TodoStore()


def todo_read_tool():
    """Define the todo_read tool."""
    return {
        "name": "todo_read",
        "description": "Read the current task list from the workspace-specific todo storage. "
        "WHEN TO USE: When you need to check the current status of tasks, review what's pending "
        "or completed, or get context about ongoing work in this workspace. "
        "You can also use this tool to pick up your previous progress. "
        "You must use this tool along with other todo tools everytime you interact with a workspace, "
        "including explaining the workspace or developing with the workspace. "
        "WHEN NOT TO USE: When you want to update tasks (use todo_write instead). "
        "or you do not want to interact with current workspace. "
        "RETURNS: A list of todo objects with their current status, priority, and metadata. "
        "Each workspace maintains its own isolated todo list.",
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
        "WHEN TO USE: When you need to add new tasks, update task status, modify priorities, "
        "or reorganize the task list. This replaces the entire list with validation. "
        "You must use this tool along with other todo tools everytime you interact with a workspace, "
        "including explaining the workspace or developing with the workspace. "
        "WHEN NOT TO USE: When you only want to read current tasks (use todo_read instead), "
        "or you do not want to interact with current workspace. "
        "RETURNS: Success status and count of tasks written. Enforces business rules like "
        "unique IDs and single in-progress task constraint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "Complete list of todo items to replace the current list. Each todo must contain id, content, status, and priority fields.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique identifier for the task. Must be unique across all todos."},
                            "content": {"type": "string", "description": "Task description or content. Cannot be empty."},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "Current status of the task. Only one task can be 'in_progress' at a time."},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"], "description": "Task priority level."},
                            "metadata": {"type": "object", "description": "Optional additional data for the task.", "additionalProperties": True},
                        },
                        "required": ["id", "content", "status", "priority"],
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
        "description": "Update a specific todo item by ID without replacing the entire list. "
        "WHEN TO USE: When you need to update specific fields of a single todo (status, priority, content, etc.). "
        "More efficient than todo_write when only updating one task. "
        "You must use this tool along with other todo tools everytime you interact with a workspace, "
        "including explaining the workspace or developing with the workspace. "
        "WHEN NOT TO USE: When you need to update multiple todos at once (use todo_write instead). "
        "or you do not want to interact with current workspace. "
        "RETURNS: The updated todo and status counts (pending, in_progress, completed). "
        "Enforces business rules like unique IDs and single in-progress task constraint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "description": "The unique ID of the todo to update."
                },
                "updates": {
                    "type": "object",
                    "description": "Fields to update in the todo. Can include content, status, priority, or metadata.",
                    "properties": {
                        "content": {"type": "string", "description": "New task description or content."},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "New status of the task."},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"], "description": "New priority level."},
                        "metadata": {"type": "object", "description": "Additional data for the task.", "additionalProperties": True},
                    },
                    "additionalProperties": True,
                }
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

