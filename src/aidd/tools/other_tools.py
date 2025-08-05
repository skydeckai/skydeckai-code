import asyncio
from typing import List, Dict, Any, Callable

from mcp.types import TextContent

from .state import state


def batch_tools_tool():
    return {
        "name": "batch_tools",
        "description": "Execute multiple tools in parallel/sequential. "
                    "USE: Bulk operations, coordinated tasks, multiple queries. "
                    "NOT: Sequential dependencies between steps, fine-grained error handling. "
                    "All tools execute in same working directory context",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Short batch operation description (3-5 words). Examples: 'Setup new project', 'Analyze codebase'."
                },
                "sequential": {
                    "type": "boolean",
                    "description": "Sequential (true) or parallel (false) execution. Default: false.",
                    "default": False
                },
                "invocations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "description": "Tool name to invoke."
                            },
                            "arguments": {
                                "type": "object",
                                "description": "Tool arguments."
                            }
                        },
                        "required": ["tool", "arguments"]
                    },
                    "description": "Tool invocations to execute (parallel or sequential)."
                }
            },
            "required": ["description", "invocations"]
        }
    }


async def handle_batch_tools(arguments: dict) -> List[TextContent]:
    """Handle executing multiple tools in batch."""
    # Import TOOL_HANDLERS here to avoid circular imports
    from . import TOOL_HANDLERS

    description = arguments.get("description")
    invocations = arguments.get("invocations", [])
    sequential = arguments.get("sequential", False)

    if not description:
        raise ValueError("Description must be provided")
    if not invocations:
        raise ValueError("Invocations list must not be empty")

    # Validate that all tools exist before running any
    for idx, invocation in enumerate(invocations):
        tool_name = invocation.get("tool")
        if not tool_name:
            raise ValueError(f"Tool name missing in invocation #{idx+1}")

        if tool_name not in TOOL_HANDLERS:
            raise ValueError(f"Unknown tool '{tool_name}' in invocation #{idx+1}")

    # Format the results header
    header = f"Batch Operation: {description}\n"
    execution_mode = "Sequential" if sequential else "Parallel"
    header += f"Execution Mode: {execution_mode}\n"

    # Combine all results
    all_contents = [TextContent(type="text", text=header)]

    if sequential:
        # Sequential execution
        for idx, invocation in enumerate(invocations):
            tool_name = invocation.get("tool")
            tool_args = invocation.get("arguments", {})

            # Get the handler for this tool
            handler = TOOL_HANDLERS[tool_name]

            # Execute the tool and process results
            result = await _execute_tool_with_error_handling(handler, tool_args, tool_name, idx)

            # Add the result to our output
            status = "SUCCESS" if result["success"] else "ERROR"
            section_header = f"[{idx+1}] {tool_name} - {status}\n"
            all_contents.append(TextContent(type="text", text=f"\n{section_header}{'=' * len(section_header)}\n"))

            if result["success"]:
                all_contents.extend(result["content"])
            else:
                all_contents.append(TextContent(
                    type="text",
                    text=f"Error: {result['error']}"
                ))

                # If a tool fails in sequential mode, we stop execution
                if idx < len(invocations) - 1:
                    all_contents.append(TextContent(
                        type="text",
                        text=f"\nExecution stopped after failure. Remaining {len(invocations) - idx - 1} tools were not executed."
                    ))
                break
    else:
        # Parallel execution
        tasks = []

        for idx, invocation in enumerate(invocations):
            tool_name = invocation.get("tool")
            tool_args = invocation.get("arguments", {})

            # Create a task for each invocation
            handler = TOOL_HANDLERS[tool_name]
            task = asyncio.create_task(
                _execute_tool_with_error_handling(handler, tool_args, tool_name, idx)
            )
            tasks.append(task)

        # Wait for all tasks to complete
        completed_results = await asyncio.gather(*tasks)

        # Process results
        for tool_result in completed_results:
            tool_name = tool_result["tool_name"]
            idx = tool_result["index"]
            status = "SUCCESS" if tool_result["success"] else "ERROR"

            # Add separator and header for this tool's results
            section_header = f"[{idx+1}] {tool_name} - {status}\n"
            all_contents.append(TextContent(type="text", text=f"\n{section_header}{'=' * len(section_header)}\n"))

            # Add the actual content from the tool
            if tool_result["success"]:
                all_contents.extend(tool_result["content"])
            else:
                all_contents.append(TextContent(
                    type="text",
                    text=f"Error: {tool_result['error']}"
                ))

    return all_contents


async def _execute_tool_with_error_handling(handler, arguments, tool_name, index):
    """Execute a single tool with error handling."""
    try:
        content = await handler(arguments)
        return {
            "tool_name": tool_name,
            "index": index,
            "success": True,
            "content": content
        }
    except Exception as e:
        return {
            "tool_name": tool_name,
            "index": index,
            "success": False,
            "error": str(e)
        }


def think_tool():
    return {
        "name": "think",
        "description": "Structured reasoning for complex problems. Documents thought process without file changes. "
                    "USE: Planning architecture, debugging complex issues, weighing tradeoffs. "
                    "NOT: Simple explanations, direct coding, information retrieval. "
                    "RETURNS: Markdown-formatted thinking process",
        "inputSchema": {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "Step-by-step thinking process using markdown (bullet points, lists, headings, code blocks)."
                }
            },
            "required": ["thought"]
        }
    }


async def handle_think(arguments: dict) -> List[TextContent]:
    """Handle recording a thought without making any changes."""
    thought = arguments.get("thought")

    if not thought:
        raise ValueError("Thought must be provided")

    # Format the thought in markdown
    formatted_thought = f"""# Thought Process

{thought}

---
*Note: This is a thinking tool used for reasoning and brainstorming. No changes were made to the repository.*
"""

    return [TextContent(
        type="text",
        text=formatted_thought
    )]
