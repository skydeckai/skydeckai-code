from .state import state
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import json


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
        """Get the path to the global todos file."""
        return state.config_dir / "todos.json"

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

        workspace_key = str(self.workspace_path)

        if not self.todos_file_path.exists():
            self._cached_store = {"lastModified": datetime.now().isoformat(), "todos": []}
            return self._cached_store

        try:
            with open(self.todos_file_path, "r", encoding="utf-8") as f:
                global_data = json.load(f)
                workspace_data = global_data.get(workspace_key, {})
                self._cached_store = {"lastModified": workspace_data.get("lastModified", datetime.now().isoformat()), "todos": workspace_data.get("todos", [])}
                return self._cached_store
        except (json.JSONDecodeError, IOError, OSError):
            # Return empty store if file is corrupted
            self._cached_store = {"lastModified": datetime.now().isoformat(), "todos": []}
            return self._cached_store

    def _save_store(self, store: Dict[str, Any]) -> None:
        """Save todos to file atomically."""
        # Ensure the ~/.skydeckai-code directory exists
        self.todos_file_path.parent.mkdir(exist_ok=True)

        workspace_key = str(self.workspace_path)

        # Load existing global data
        global_data = {}
        if self.todos_file_path.exists():
            try:
                with open(self.todos_file_path, "r", encoding="utf-8") as f:
                    global_data = json.load(f)
            except (json.JSONDecodeError, IOError, OSError):
                global_data = {}

        # Update the workspace data
        global_data[workspace_key] = store

        # Write to temporary file first (atomic write)
        temp_path = self.todos_file_path.with_suffix(".json.tmp")

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(global_data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(self.todos_file_path)

            # Update cache
            self._cached_store = store

        except Exception:
            # Clean up temp file if something went wrong
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _add_to_gitignore(self) -> None:
        """No longer needed since todos are stored in ~/.skydeckai-code/todo.json"""
        pass

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
        original_todo = None
        for i, todo in enumerate(todos):
            if todo["id"] == todo_id:
                todo_index = i
                original_todo = todo
                break

        if todo_index is None or original_todo is None:
            raise ValueError(f"Todo with ID '{todo_id}' not found")

        # Check if status is changing to completed
        original_status = original_todo["status"]
        new_status = updates.get("status", original_status)
        is_completing = original_status != "completed" and new_status == "completed"

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

        result = {"updated_todo": updated_todo, "counts": {"pending": pending_count, "in_progress": in_progress_count, "completed": completed_count, "total": len(updated_todos)}}

        # If a todo was just completed, find and include the next pending todo
        if is_completing:
            next_todo = self._find_next_pending_todo(updated_todos, todo_index)
            if next_todo:
                result["next_todo"] = next_todo
            else:
                result["next_todo"] = None
                result["message"] = "All todos completed! No more pending tasks."

        return result

    def _find_next_pending_todo(self, todos: List[Dict[str, Any]], completed_index: int) -> Dict[str, Any] | None:
        """Find the next pending todo after the completed one in sequential order."""
        # Look for the next pending todo starting from the position after the completed one
        for i in range(completed_index + 1, len(todos)):
            if todos[i]["status"] == "pending":
                return todos[i]
        
        # If no pending todo found after the completed one, look from the beginning
        # This handles cases where todos might be reordered or the completed one wasn't the first in-progress
        for i in range(completed_index):
            if todos[i]["status"] == "pending":
                return todos[i]
        
        # No pending todos found
        return None

    def _validate_todos(self, todos: List[Dict[str, Any]]) -> None:
        """Validate todos according to business rules."""
        if not isinstance(todos, list):
            raise ValueError("Todos must be a list")

        # Check for required fields and collect IDs
        required_fields = {"id", "content", "status"}
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
