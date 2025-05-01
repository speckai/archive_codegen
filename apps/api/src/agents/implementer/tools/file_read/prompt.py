DESCRIPTION = "Read a file from the local filesystem."
PROMPT = """
Reads a file from the local filesystem. The file_path parameter must be an absolute path, not a relative path.
By default, it reads up to a certain number of lines starting from the beginning of the file.
You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters.
Any lines longer than a certain number of characters will be truncated. For image files, the tool will display the image for you.
""".strip()
