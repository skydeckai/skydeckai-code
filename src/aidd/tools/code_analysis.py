import json
import os
import subprocess
from typing import Any, Dict, List

import tree_sitter_c_sharp
import tree_sitter_cpp
import tree_sitter_go
import tree_sitter_java
import tree_sitter_javascript
import tree_sitter_kotlin
import tree_sitter_python
import tree_sitter_ruby
import tree_sitter_rust
from tree_sitter import Language, Parser
from tree_sitter_php._binding import language_php
from tree_sitter_typescript._binding import language_tsx, language_typescript

from .state import state

# Map of file extensions to language names
LANGUAGE_MAP = {
    '.py': 'python',
    '.js': 'javascript', '.jsx': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'tsx',
    '.java': 'java',
    '.cpp': 'cpp', '.hpp': 'cpp', '.cc': 'cpp', '.hh': 'cpp', '.cxx': 'cpp', '.hxx': 'cpp',
    '.rb': 'ruby', '.rake': 'ruby',
    '.go': 'go',
    '.rs': 'rust',
    '.php': 'php',
    '.cs': 'c-sharp',
    '.kt': 'kotlin', '.kts': 'kotlin'
    # Add more languages as needed
}

# Initialize languages and create parsers
try:
    _parser_cache = {
        'python': Parser(Language(tree_sitter_python.language())),
        'javascript': Parser(Language(tree_sitter_javascript.language())),
        'typescript': Parser(Language(language_typescript())),
        'tsx': Parser(Language(language_tsx())),
        'java': Parser(Language(tree_sitter_java.language())),
        'cpp': Parser(Language(tree_sitter_cpp.language())),
        'ruby': Parser(Language(tree_sitter_ruby.language())),
        'go': Parser(Language(tree_sitter_go.language())),
        'rust': Parser(Language(tree_sitter_rust.language())),
        'php': Parser(Language(language_php())),
        'c-sharp': Parser(Language(tree_sitter_c_sharp.language())),
        'kotlin': Parser(Language(tree_sitter_kotlin.language())),
    }
except Exception as e:
    raise RuntimeError(f"Failed to initialize languages: {e}")

def codebase_mapper_tool():
    return {
        "name": "codebase_mapper",
        "description": "Generate structural map of code: classes, functions, methods using tree-sitter. "
                    "USE: Understand codebase architecture, discover code structure. "
                    "NOT: Text search (use search_code), single file analysis. "
                    "SUPPORTS: Python, JS/TS, Java, C++, Ruby, Go, Rust, PHP, C#, Kotlin. "
                    "RETURNS: Text tree of classes/functions with statistics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Root directory to analyze. Examples: '.', 'src', 'lib/components'."
                }
            },
            "required": ["path"]
        },
    }

def _detect_language(file_path: str) -> str:
    """Detect programming language based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    return LANGUAGE_MAP.get(ext, 'unknown')

def _get_language_parser(language: str):
    """Get the appropriate tree-sitter parser for a language."""
    try:
        if language not in _parser_cache:
            return {'error': f'Unsupported language: {language}'}
        return _parser_cache[language]
    except Exception as e:
        return {
            'error': f'Error loading language {language}: {str(e)}'
        }

def _extract_node_text(node, source_code: bytes) -> str:
    """Extract text from a node."""
    return source_code[node.start_byte:node.end_byte].decode('utf-8')

def _analyze_file(file_path: str) -> Dict[str, Any]:
    """Analyze a single file using tree-sitter."""
    try:
        with open(file_path, 'rb') as f:
            source_code = f.read()

        language = _detect_language(file_path)
        if language == 'unknown':
            return {'error': f'Unsupported file type: {os.path.splitext(file_path)[1]}'}

        parser = _get_language_parser(language)
        if isinstance(parser, dict) and 'error' in parser:
            return parser

        tree = parser.parse(source_code)
        root_node = tree.root_node

        # Check if we got a valid root node
        if not root_node:
            return {'error': 'Failed to parse file - no root node'}

        def process_node(node) -> Dict[str, Any]:
            if not node:
                return None

            result = {
                'type': node.type,
                'start_line': node.start_point[0] + 1,
                'end_line': node.end_point[0] + 1,
            }

            # Process child nodes based on language-specific patterns
            if language == 'python':
                if node.type in ['class_definition', 'function_definition']:
                    for child in node.children:
                        if child.type == 'identifier':
                            result['name'] = _extract_node_text(child, source_code)
                        elif child.type == 'parameters':
                            params = []
                            for param in child.children:
                                if param.type == 'identifier':
                                    params.append(_extract_node_text(param, source_code))
                            if params:
                                result['parameters'] = params
                elif node.type == 'assignment':
                    # Handle global variable assignments
                    for child in node.children:
                        if child.type == 'identifier':
                            result['type'] = 'variable_declaration'
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                        # Break after first identifier to avoid capturing right-hand side
                        break

            elif language == 'javascript':
                if node.type in ['class_declaration', 'method_definition', 'function_declaration']:
                    for child in node.children:
                        if child.type == 'identifier':
                            result['name'] = _extract_node_text(child, source_code)
                        elif child.type == 'formal_parameters':
                            params = []
                            for param in child.children:
                                if param.type == 'identifier':
                                    params.append(_extract_node_text(param, source_code))
                            if params:
                                result['parameters'] = params
                elif node.type in ['variable_declaration', 'lexical_declaration']:
                    # Handle var/let/const declarations
                    for child in node.children:
                        if child.type == 'variable_declarator':
                            for subchild in child.children:
                                if subchild.type == 'identifier':
                                    result['type'] = 'variable_declaration'
                                    result['name'] = _extract_node_text(subchild, source_code)
                                    return result

            elif language == 'typescript':
                if node.type in ['class_declaration', 'method_declaration', 'function_declaration', 'interface_declaration']:
                    for child in node.children:
                        if child.type == 'identifier':
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                    return result
                elif node.type in ['variable_statement', 'property_declaration']:
                    # Handle variable declarations and property declarations
                    for child in node.children:
                        if child.type == 'identifier':
                            result['type'] = 'variable_declaration'
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                    return result

            elif language == 'java':
                if node.type in ['class_declaration', 'method_declaration', 'constructor_declaration', 'interface_declaration']:
                    for child in node.children:
                        if child.type == 'identifier':
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                    return result
                elif node.type in ['field_declaration', 'variable_declaration']:
                    # Handle Java global fields and variables
                    for child in node.children:
                        if child.type == 'variable_declarator':
                            for subchild in child.children:
                                if subchild.type == 'identifier':
                                    result['type'] = 'variable_declaration'
                                    result['name'] = _extract_node_text(subchild, source_code)
                                    return result
                    return result

            elif language == 'cpp':
                if node.type in ['class_specifier', 'function_definition', 'struct_specifier']:
                    for child in node.children:
                        if child.type == 'identifier':
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                    return result
                elif node.type in ['declaration', 'variable_declaration']:
                    # Handle C++ global variables and declarations
                    for child in node.children:
                        if child.type == 'init_declarator' or child.type == 'declarator':
                            for subchild in child.children:
                                if subchild.type == 'identifier':
                                    result['type'] = 'variable_declaration'
                                    result['name'] = _extract_node_text(subchild, source_code)
                                    return result
                    return result

            elif language == 'ruby':
                if node.type in ['class', 'method', 'singleton_method', 'module']:
                    for child in node.children:
                        if child.type == 'identifier':
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                    return result
                elif node.type == 'assignment' or node.type == 'global_variable':
                    # Handle Ruby global variables and assignments
                    for child in node.children:
                        if child.type == 'identifier' or child.type == 'global_variable':
                            result['type'] = 'variable_declaration'
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                    return result

            elif language == 'go':
                if node.type in ['type_declaration', 'function_declaration', 'method_declaration', 'interface_declaration']:
                    for child in node.children:
                        if child.type == 'identifier' or child.type == 'field_identifier':
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                    return result
                elif node.type == 'var_declaration' or node.type == 'const_declaration':
                    # Handle Go variable and constant declarations
                    for child in node.children:
                        if child.type == 'var_spec' or child.type == 'const_spec':
                            for subchild in child.children:
                                if subchild.type == 'identifier':
                                    result['type'] = 'variable_declaration'
                                    result['name'] = _extract_node_text(subchild, source_code)
                                    return result
                    return result

            elif language == 'rust':
                if node.type in ['struct_item', 'impl_item', 'fn_item', 'trait_item']:
                    for child in node.children:
                        if child.type == 'identifier':
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                    return result
                elif node.type in ['static_item', 'const_item', 'let_declaration']:
                    # Handle Rust static items, constants, and let declarations
                    for child in node.children:
                        if child.type == 'identifier':
                            result['type'] = 'variable_declaration'
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                        elif child.type == 'pattern' and child.children:
                            result['name'] = _extract_node_text(child.children[0], source_code)
                    return result

            elif language == 'php':
                if node.type in ['class_declaration', 'method_declaration', 'function_definition', 'interface_declaration', 'trait_declaration']:
                    for child in node.children:
                        if child.type == 'name':
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                    return result
                elif node.type == 'property_declaration' or node.type == 'const_declaration':
                    # Handle PHP class properties and constants
                    for child in node.children:
                        if child.type == 'property_element' or child.type == 'const_element':
                            for subchild in child.children:
                                if subchild.type == 'variable_name' or subchild.type == 'name':
                                    result['type'] = 'variable_declaration'
                                    result['name'] = _extract_node_text(subchild, source_code)
                    return result

            elif language == 'csharp':
                if node.type in ['class_declaration', 'interface_declaration', 'method_declaration']:
                    for child in node.children:
                        if child.type == 'identifier':
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                    return result
                elif node.type in ['field_declaration', 'property_declaration']:
                    # Handle C# fields and properties
                    for child in node.children:
                        if child.type == 'variable_declaration':
                            for subchild in child.children:
                                if subchild.type == 'identifier':
                                    result['type'] = 'variable_declaration'
                                    result['name'] = _extract_node_text(subchild, source_code)
                                    return result
                    return result

            elif language == 'kotlin':
                if node.type in ['class_declaration', 'function_declaration']:
                    for child in node.children:
                        if child.type == 'simple_identifier':
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                    return result
                elif node.type in ['property_declaration', 'variable_declaration']:
                    # Handle Kotlin properties and variables
                    for child in node.children:
                        if child.type == 'simple_identifier':
                            result['type'] = 'variable_declaration'
                            result['name'] = _extract_node_text(child, source_code)
                            return result
                        break  # Only capture the first identifier
                    return result

            # Recursively process children
            children = []
            for child in node.children:
                child_result = process_node(child)
                if child_result and (
                    child_result.get('type') in [
                        'class_definition', 'function_definition',
                        'class_declaration', 'method_definition',
                        'function_declaration', 'interface_declaration',
                        'method_declaration', 'constructor_declaration',
                        'class_specifier', 'struct_specifier',
                        'class', 'method', 'singleton_method', 'module',
                        'type_declaration', 'method_declaration',
                        'interface_declaration', 'struct_item', 'impl_item',
                        'fn_item', 'trait_item', 'trait_declaration',
                        'property_declaration', 'object_definition',
                        'trait_definition', 'def_definition',
                        'function_definition', 'class_definition',
                        'variable_declaration'] or 'children' in child_result
                ):
                    children.append(child_result)

            if children:
                result['children'] = children
            return result

        return process_node(root_node)

    except Exception as e:
        return {
            'error': f'Error analyzing file: {str(e)}'
        }

async def handle_codebase_mapper(arguments: dict):
    """Handle building a structural map of source code."""
    from mcp.types import TextContent

    path = arguments.get("path", ".")

    # Validate and get full path
    full_path = os.path.abspath(os.path.join(state.allowed_directory, path))
    if not full_path.startswith(state.allowed_directory):
        return [TextContent(
            type="text",
            text=json.dumps({'error': 'Access denied: Path must be within allowed directory'})
        )]
    if not os.path.exists(full_path):
        return [TextContent(
            type="text",
            text=json.dumps({'error': f'Path does not exist: {path}'})
        )]
    if not os.path.isdir(full_path):
        return [TextContent(type="text", text=json.dumps({'error': f'Path is not a directory: {path}'}))]

    analyzed_files = []

    # First try using git ls-files
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            cwd=full_path,
            capture_output=True,
            text=True,
            check=True,
        )
        if result.returncode == 0:
            files = [
                os.path.join(full_path, f.strip())
                for f in result.stdout.splitlines()
                if f.strip()
            ]
            analyzed_files.extend(files)

    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # If git didn't work or found no files, use regular directory walk
    if not analyzed_files:
        skip_dirs = {'.git', '.svn', 'node_modules', '__pycache__', 'build', 'dist'}
        for root, _, filenames in os.walk(full_path):

            # Get the directory name
            dir_name = os.path.basename(root)

            # Skip hidden and build directories
            if dir_name.startswith('.') or dir_name in skip_dirs:
                continue

            for filename in filenames:
                # Skip hidden files
                if filename.startswith('.'):
                    continue

                file_path = os.path.join(root, filename)
                language = _detect_language(file_path)
                if language != 'unknown':
                    analyzed_files.append(file_path)

    if not analyzed_files:
        return [TextContent(
            type="text",
            text=json.dumps({
                'error': 'No source code files found to analyze',
                'path': full_path
            }, indent=2)
        )]

    # Analyze each file
    analysis_results = []
    errors = []
    for file_path in sorted(analyzed_files):
        rel_path = os.path.relpath(file_path, full_path)
        try:
            result = _analyze_file(file_path)

            if result and isinstance(result, dict) and 'error' not in result:
                # Successfully analyzed file
                analysis_results.append({
                    'path': rel_path,
                    'language': _detect_language(rel_path),
                    'structure': result
                })
            elif result and isinstance(result, dict) and 'error' in result:
                errors.append({
                    'path': rel_path,
                    'error': result['error']
                })
        except Exception as e:
            errors.append({
                'path': rel_path,
                'error': str(e)
            })

    if not analysis_results:
        return [TextContent(
            type="text",
            text=json.dumps({
                'error': 'Analysis completed but no valid results',
                'path': full_path,
                'attempted': len(analyzed_files),
                'files_found': len(analyzed_files),
                'errors': errors
            }, indent=2)
        )]

    def count_nodes(structure: Dict[str, Any], node_types: set[str]) -> int:
        """Recursively count nodes of specific types in the tree structure."""
        count = 0

        # Count current node if it matches
        if structure.get('type') in node_types:
            count += 1

        # Recursively count in children
        for child in structure.get('children', []):
            count += count_nodes(child, node_types)

        return count

    # Define node types for different categories
    class_types = {
        'class_definition', 'class_declaration', 'class_specifier',
        'struct_specifier', 'struct_item', 'interface_declaration',
        'object_declaration'  # Kotlin object declarations
    }

    function_types = {
        'function_definition', 'function_declaration', 'method_definition',
        'method_declaration', 'constructor_declaration', 'fn_item',
        'method', 'singleton_method',
        'primary_constructor'  # Kotlin primary constructors
    }

    def generate_text_map(analysis_results: List[Dict[str, Any]]) -> str:
        """Generate a compact text representation of the code structure analysis."""

        def format_node(node: Dict[str, Any], prefix: str = "", is_last: bool = True) -> List[str]:
            lines = []

            node_type = node.get('type', '')
            node_name = node.get('name', '')

            # Handle decorated functions - extract the actual function definition
            if node_type == 'decorated_definition' and 'children' in node:
                for child in node.get('children', []):
                    if child.get('type') in {
                        'function_definition', 'method_definition', 'member_function_definition'
                    }:
                        return format_node(child, prefix, is_last)

            # Handle class body, block nodes, and wrapper functions
            if not node_name and node_type in {'class_body', 'block', 'declaration_list', 'body'}:
                return process_children(node.get('children', []), prefix, is_last)
            elif not node_name:
                return lines

            branch = "└── " if is_last else "├── "

            # Format node information based on type
            if node_type in {
                'class_definition', 'class_declaration', 'class_specifier',
                'class', 'interface_declaration', 'struct_specifier',
                'struct_item', 'trait_item', 'trait_declaration',
                'module', 'type_declaration'
            }:
                node_info = f"class {node_name}"
            elif node_type in {
                'function_definition', 'function_declaration', 'method_definition',
                'method_declaration', 'fn_item', 'method', 'singleton_method',
                'constructor_declaration', 'member_function_definition',
                'constructor', 'destructor', 'public_method_definition',
                'private_method_definition', 'protected_method_definition'
            }:
                # Handle parameters
                params = []
                if 'parameters' in node and node['parameters']:
                    params = node['parameters']
                elif 'children' in node:
                    # Try to extract parameters from children for languages that structure them differently
                    for child in node['children']:
                        if child.get('type') in {'parameter_list', 'parameters', 'formal_parameters', 'argument_list'}:
                            for param in child.get('children', []):
                                if param.get('type') in {'identifier', 'parameter'}:
                                    param_name = param.get('name', '')
                                    if param_name:
                                        params.append(param_name)

                params_str = ', '.join(params) if params else ''
                node_info = f"{node_name}({params_str})"
            else:
                node_info = node_name

            lines.append(f"{prefix}{branch}{node_info}")

            # Process children
            if 'children' in node:
                new_prefix = prefix + ("    " if is_last else "│   ")
                child_lines = process_children(node['children'], new_prefix, is_last)
                if child_lines:  # Only add child lines if there are any
                    lines.extend(child_lines)

            return lines

        def process_children(children: List[Dict], prefix: str, is_last: bool) -> List[str]:
            if not children:
                return []

            lines = []
            significant_children = [
                child for child in children
                if child.get('type') in {
                    'decorated_definition',
                    # Class-related nodes
                    'class_definition', 'class_declaration', 'class_specifier',
                    'class', 'interface_declaration', 'struct_specifier',
                    'struct_item', 'trait_item', 'trait_declaration',
                    'module', 'type_declaration',
                    'impl_item',  # Rust implementations
                    # Method-related nodes
                    'function_definition', 'function_declaration', 'method_definition',
                    'method_declaration', 'fn_item', 'method', 'singleton_method',
                    'constructor_declaration', 'member_function_definition',
                    'constructor', 'destructor', 'public_method_definition',
                    'private_method_definition', 'protected_method_definition',
                    # Container nodes that might have methods
                    'class_body', 'block', 'declaration_list', 'body',
                    'impl_block',  # Rust implementation blocks
                    # Property and field nodes
                    'property_declaration', 'field_declaration',
                    'variable_declaration', 'const_declaration'
                }
            ]

            for i, child in enumerate(significant_children):
                is_last_child = (i == len(significant_children) - 1)
                child_lines = format_node(child, prefix, is_last_child)
                if child_lines:  # Only add child lines if there are any
                    lines.extend(child_lines)

            return lines

        # Process each file
        output_lines = []

        # Sort analysis results by path
        sorted_results = sorted(analysis_results, key=lambda x: x['path'])

        for result in sorted_results:
            # Skip files with no significant structure
            if not result.get('structure') or not result.get('structure', {}).get('children'):
                continue

            # Add file header
            output_lines.append(f"\n{result['path']}")

            # Format the structure
            structure = result['structure']
            if 'children' in structure:
                significant_nodes = [
                    child for child in structure['children']
                    if child.get('type') in {
                        'decorated_definition',
                        # Class-related nodes
                        'class_definition', 'class_declaration', 'class_specifier',
                        'class', 'interface_declaration', 'struct_specifier',
                        'struct_item', 'trait_item', 'trait_declaration',
                        'module', 'type_declaration',
                        'impl_item',  # Rust implementations
                        # Method-related nodes
                        'function_definition', 'function_declaration', 'method_definition',
                        'method_declaration', 'fn_item', 'method', 'singleton_method',
                        'constructor_declaration', 'member_function_definition',
                        'constructor', 'destructor', 'public_method_definition',
                        'private_method_definition', 'protected_method_definition',
                        # Property and field nodes
                        'property_declaration', 'field_declaration',
                        'variable_declaration', 'const_declaration'
                    }
                ]

                for i, node in enumerate(significant_nodes):
                    is_last = (i == len(significant_nodes) - 1)
                    node_lines = format_node(node, "", is_last)
                    if node_lines:  # Only add node lines if there are any
                        output_lines.extend(node_lines)

        # Return the formatted text
        return '\n'.join(output_lines) if output_lines else "No significant code structure found."

    def format_analysis_results(analysis_results: List[Dict[str, Any]], analyzed_files: List[str], errors: List[Dict[str, str]]) -> str:
            """Format the analysis results into a clear text format."""

            # Count statistics
            total_files = len(analyzed_files)
            classes = sum(count_nodes(f['structure'], class_types) for f in analysis_results)
            functions = sum(count_nodes(f['structure'], function_types) for f in analysis_results)
            decorated_functions = sum(count_nodes(f['structure'], {'decorated_definition'}) for f in analysis_results)
            error_count = len(errors)

            # Build output sections
            sections = []

            # Add statistics section
            sections.append("\n===ANALYSIS STATISTICS===\n")
            sections.append(f"Total files analyzed: {total_files}")
            sections.append(f"Total errors: {error_count}")
            sections.append(f"Total classes found: {classes}")
            sections.append(f"Total functions found: {functions}")
            sections.append(f"Total decorated functions: {decorated_functions}")

            # Add errors section if any
            if errors:
                sections.append("\n===ERRORS===")
                for error in errors:
                    error_first_line = error['error'].split('\n')[0]
                    sections.append(f"{error['path']}: {error_first_line}")

            # Add repository map
            sections.append("\n===REPOSITORY STRUCTURE===")
            sections.append(generate_text_map(analysis_results))

            # Join all sections with newlines
            return "\n".join(sections)

    return [TextContent(
        type="text",
        text=format_analysis_results(analysis_results, analyzed_files, errors)
    )]
