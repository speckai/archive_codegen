DESCRIPTION = """
- Fast file pattern matching tool that works with any codebase size
- Supports glob patterns like "**/*.js" or "src/**/*.ts"
- Returns matching file paths sorted by modification time
- Use this tool when you need to find files by name patterns
- When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead
""".strip()

# TODO: maybe communicate the specificity of things?
# it failed to get what it wanted w an overly specific pattern like **/*login*/**/*.(tsx|ts|js|jsx) when it should have just used **/*login*/**.(tsx|ts|js|jsx)

# **/auth/**/*.(tsx|ts|js|jsx) as well
