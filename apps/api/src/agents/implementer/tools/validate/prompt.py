DESCRIPTION = """
This is a tool to perform a visual validation using the browser against the current state of the codebase.
You should use this tool when you're ready to submit your changes and want to ensure that the changes fix the user's request.

This tool will return the following:

- Overall success state if the changes have fulfilled the user's request and feedback
- For each point of interest that the user has requested to be validated:
    - Success state if the changes for this region/component have fulfilled the user's request and feedback
    - User defined annotation of the point of interest
    - Rationale for the success state
    - Before/after screenshots of the points of interest from the browser that are validated against
""".strip()
