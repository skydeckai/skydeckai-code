from .code_analysis import handle_codebase_mapper, codebase_mapper_tool
from .code_execution import (
    execute_code_tool,
    execute_shell_script_tool,
    handle_execute_code,
    handle_execute_shell_script,
)
from .code_tools import search_code_tool, handle_search_code
from .directory_tools import (
    create_directory_tool,
    directory_tree_tool,
    handle_create_directory,
    handle_directory_tree,
    handle_list_directory,
    list_directory_tool,
)
from .file_tools import (
    copy_file_tool,
    delete_file_tool,
    edit_file_tool,
    get_file_info_tool,
    handle_copy_file,
    handle_delete_file,
    handle_edit_file,
    handle_get_file_info,
    handle_move_file,
    handle_read_file,
    handle_search_files,
    handle_write_file,
    move_file_tool,
    read_file_tool,
    search_files_tool,
    write_file_tool,
)
from .get_active_apps_tool import get_active_apps_tool, handle_get_active_apps
from .get_available_windows_tool import get_available_windows_tool, handle_get_available_windows
from .image_tools import read_image_file_tool, handle_read_image_file
from .other_tools import batch_tools_tool, handle_batch_tools, think_tool, handle_think
from .path_tools import (
    get_allowed_directory_tool,
    handle_get_allowed_directory,
    handle_update_allowed_directory,
    update_allowed_directory_tool,
)
from .screenshot_tool import (
    capture_screenshot_tool,
    handle_capture_screenshot,
)
from .system_tools import get_system_info_tool, handle_get_system_info
from .todo_tools import (
    todo_read_tool,
    todo_write_tool,
    todo_update_tool,
    handle_todo_read,
    handle_todo_write,
    handle_todo_update,
)
from .web_tools import web_fetch_tool, handle_web_fetch, web_search_tool, handle_web_search

# Export all tools definitions
TOOL_DEFINITIONS = [
    get_allowed_directory_tool(),
    write_file_tool(),
    update_allowed_directory_tool(),
    create_directory_tool(),
    edit_file_tool(),
    list_directory_tool(),
    read_file_tool(),
    move_file_tool(),
    copy_file_tool(),
    search_files_tool(),
    delete_file_tool(),
    get_file_info_tool(),
    directory_tree_tool(),
    execute_code_tool(),
    execute_shell_script_tool(),
    codebase_mapper_tool(),
    search_code_tool(),
    batch_tools_tool(),
    think_tool(),
    # Screenshot tools
    capture_screenshot_tool(),
    # System context tools
    get_active_apps_tool(),
    get_available_windows_tool(),
    # Image tools
    read_image_file_tool(),
    # Web tools
    web_fetch_tool(),
    web_search_tool(),
    # System tools
    get_system_info_tool(),
    # Todo tools
    todo_read_tool(),
    todo_write_tool(),
    todo_update_tool(),
]

# Export all handlers
TOOL_HANDLERS = {
    "get_allowed_directory": handle_get_allowed_directory,
    "update_allowed_directory": handle_update_allowed_directory,
    "list_directory": handle_list_directory,
    "create_directory": handle_create_directory,
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "edit_file": handle_edit_file,
    "move_file": handle_move_file,
    "copy_file": handle_copy_file,
    "search_files": handle_search_files,
    "search_code": handle_search_code,
    "delete_file": handle_delete_file,
    "get_file_info": handle_get_file_info,
    "directory_tree": handle_directory_tree,
    "execute_code": handle_execute_code,
    "execute_shell_script": handle_execute_shell_script,
    "codebase_mapper": handle_codebase_mapper,
    "batch_tools": handle_batch_tools,
    "think": handle_think,
    "get_system_info": handle_get_system_info,
    # Screenshot handlers
    "capture_screenshot": handle_capture_screenshot,
    # System context handlers
    "get_active_apps": handle_get_active_apps,
    "get_available_windows": handle_get_available_windows,
    # Image handlers
    "read_image_file": handle_read_image_file,
    # Web handlers
    "web_fetch": handle_web_fetch,
    "web_search": handle_web_search,
    # Todo handlers
    "todo_read": handle_todo_read,
    "todo_write": handle_todo_write,
    "todo_update": handle_todo_update,
}
