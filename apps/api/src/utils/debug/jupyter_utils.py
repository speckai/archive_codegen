def init_debug():
    """Initialize debug environment with clipboard helpers"""
    try:
        from AppKit import NSPasteboard, NSStringPboardType
        from Foundation import NSString, NSUTF8StringEncoding
    except ImportError:
        print("Missing dependencies. Please install:")
        print("pip install pyobjc")
        return

    def pbcopy(s: str) -> None:
        """Copy string argument to clipboard"""
        board = NSPasteboard.generalPasteboard()
        board.declareTypes_owner_([NSStringPboardType], None)
        newStr = NSString.stringWithString_(s)
        newData = newStr.dataUsingEncoding_(NSUTF8StringEncoding)
        board.setData_forType_(newData, NSStringPboardType)

    def pbpaste() -> str:
        """Returns contents of clipboard"""
        board = NSPasteboard.generalPasteboard()
        content = board.stringForType_(NSStringPboardType)
        return content

    # Add to global namespace
    import builtins

    builtins.c = pbcopy
    builtins.paste = pbpaste
    print("Clipboard helpers loaded!")

    # New temp file helper function
    def to_temp(obj, filename="debug_output.html"):
        """
        Writes an object to a temporary file with pretty formatting.
        Supports various data types including BaseModels.

        Args:
            obj: The object to write to the file
            filename: Name of the temporary file (default: debug_output.html)
        """
        import json
        import os
        import pprint
        import tempfile

        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)

        # Helper function to convert dict to pretty XML-like format using CDATA
        def dict_to_pretty_xml(d, indent=0):
            result = []
            spaces = "  " * indent

            if isinstance(d, dict):
                for key, value in d.items():
                    if isinstance(value, (dict, list)):
                        result.append(f"{spaces}<{key}>")
                        result.append(dict_to_pretty_xml(value, indent + 1))
                        result.append(f"{spaces}</{key}>")
                    else:
                        value_str = str(value).replace("\n", f"\n{spaces}  ")
                        result.append(f"{spaces}<{key}><![CDATA[{value_str}]]></{key}>")
            elif isinstance(d, list):
                for i, item in enumerate(d):
                    if isinstance(item, (dict, list)):
                        result.append(f"{spaces}<item_{i}>")
                        result.append(dict_to_pretty_xml(item, indent + 1))
                        result.append(f"{spaces}</item_{i}>")
                    else:
                        value_str = str(item).replace("\n", f"\n{spaces}  ")
                        result.append(f"{spaces}<item><![CDATA[{value_str}]]></item>")
            else:
                result.append(f"{spaces}<![CDATA[{str(d)}]]>")

            return "\n".join(result)

        # Special handling for strings - preserve formatting and don't escape
        if isinstance(obj, str):
            # Just write the string directly, preserving all formatting
            content = obj
        # Convert object to string with nice formatting
        elif hasattr(obj, "model_dump") and callable(obj.model_dump):  # Pydantic v2
            data = obj.model_dump()
            content = dict_to_pretty_xml(data)
        elif hasattr(obj, "json") and callable(obj.json):  # Pydantic v1
            data = json.loads(obj.json())
            content = dict_to_pretty_xml(data)
        elif hasattr(obj, "dict") and callable(obj.dict):  # Older Pydantic
            data = obj.dict()
            content = dict_to_pretty_xml(data)
        elif isinstance(obj, (dict, list, tuple)):
            content = dict_to_pretty_xml(obj)
        else:
            # For other types, use repr but clean it up
            raw_content = repr(obj)
            # If it's a multiline string representation (like your example)
            if "\\n" in raw_content and (
                raw_content.startswith("'") or raw_content.startswith('"')
            ):
                # Remove quotes and unescape newlines and other escape sequences
                content = raw_content[1:-1].encode().decode("unicode_escape")
            else:
                content = pprint.pformat(obj, indent=2, width=100)

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Output written to: {filepath}")
        return filepath

    # Add to global namespace
    builtins.t = to_temp
    print("Temp file helper loaded!")
