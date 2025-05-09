import base64
import io
import os

from mcp.types import TextContent
from PIL import Image

from .state import state

# Maximum file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

# Image size constraints
MIN_WIDTH = 20
MAX_WIDTH = 800

def read_image_file_tool():
    return {
        "name": "read_image_file",
        "description": "Read an image file from the file system and return its contents as a base64-encoded string. "
                    "WHEN TO USE: When you need to view or process image files, include images in responses, analyze "
                    "image content, or convert images to a format that can be transmitted as text. Useful for examining "
                    "screenshots, diagrams, photos, or any visual content stored in the file system. "
                    "WHEN NOT TO USE: When you only need information about the image file without its contents "
                    "(use get_file_info instead), when working with extremely large images (over 100MB), or when you "
                    "need to read text files (use read_file instead). "
                    "RETURNS: A base64-encoded data URI string prefixed with the appropriate MIME type "
                    "(e.g., 'data:image/png;base64,...'). Images that are very small or very large will be automatically "
                    "resized to between 20-800 pixels wide while maintaining aspect ratio. This tool supports common image "
                    "formats like PNG, JPEG, GIF, and WebP. Only works within the allowed directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the image file to read. This must be a valid image file in a supported format "
                                   "(PNG, JPEG, GIF, WebP). Examples: 'screenshots/screen.png', 'images/logo.jpg', "
                                   "'diagrams/flowchart.gif'. Both absolute and relative paths are supported, but must be "
                                   "within the allowed workspace."
                },
                "max_size": {
                    "type": "integer",
                    "description": "Maximum file size in bytes to allow. Files larger than this size will be rejected to "
                                   "prevent memory issues. Default is 100MB (104,857,600 bytes). For most use cases, the "
                                   "default value is sufficient, but you can lower this when working with limited memory.",
                    "optional": True
                }
            },
            "required": ["path"]
        },
    }

async def handle_read_image_file(arguments: dict):
    """Handle reading an image file and converting it to base64."""
    path = arguments.get("path")
    max_size = arguments.get("max_size", MAX_FILE_SIZE)

    if not path:
        raise ValueError("path must be provided")

    # Determine full path based on whether input is absolute or relative
    if os.path.isabs(path):
        full_path = os.path.abspath(path)  # Just normalize the absolute path
    else:
        # For relative paths, join with allowed_directory
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory ({state.allowed_directory})")

    if not os.path.exists(full_path):
        raise ValueError(f"File does not exist: {full_path}")
    if not os.path.isfile(full_path):
        raise ValueError(f"Path is not a file: {full_path}")

    # Check file size before attempting to read
    file_size = os.path.getsize(full_path)
    if file_size > max_size:
        raise ValueError(f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)")

    try:
        # Try to open the image with PIL to validate it's a valid image
        with Image.open(full_path) as img:
            # Get the image format
            image_format = img.format.lower()
            if not image_format:
                # Try to determine format from file extension
                ext = os.path.splitext(full_path)[1].lower().lstrip('.')
                if ext in ['jpg', 'jpeg']:
                    image_format = 'jpeg'
                elif ext in ['png', 'gif', 'webp']:
                    image_format = ext
                else:
                    raise ValueError(f"Unsupported image format: {ext}")

            # Resize image if width is greater than MAX_WIDTH or less than MIN_WIDTH
            if img.width > MAX_WIDTH or img.width < MIN_WIDTH:
                # Calculate new dimensions maintaining aspect ratio
                if img.width > MAX_WIDTH:
                    target_width = MAX_WIDTH
                else:
                    target_width = MIN_WIDTH

                ratio = target_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)

            # Convert image to bytes
            img_byte_arr = io.BytesIO()
            if image_format.lower() == 'jpeg':
                img.save(img_byte_arr, format=image_format, quality=85)  # Specify quality for JPEG
            else:
                img.save(img_byte_arr, format=image_format)
            img_byte_arr = img_byte_arr.getvalue()

            # Convert to base64
            base64_data = base64.b64encode(img_byte_arr).decode('utf-8')

            # Return the image data with its type
            return [TextContent(
                type="text",
                text=f"data:image/{image_format};base64,{base64_data}"
            )]
    except Image.UnidentifiedImageError:
        raise ValueError(f"File is not a valid image: {path}")
    except Exception as e:
        raise ValueError(f"Error reading image file: {str(e)}")
