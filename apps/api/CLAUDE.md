# Paige API Development Guide

## Commands

- **Run dev server**: `npm run dev` or `uv run uvicorn src.api:app --reload --host 0.0.0.0 --port 8080`
- **Run tests**: `uv run pytest tests/path/to/test_file.py -v`
- **Run single test**: `uv run pytest tests/path/to/test_file.py::TestClass::test_function -v`
- **Format code**: `uv run black src/`
- **Type checking**: `uv run mypy src/`

## Code Style

- **Imports**: Standard library first, third-party second, local imports last (all in groups)
  - No `__init__.py` files in modules
- **Types**: Always use type hints for variables, parameters, and return values
  - Use built-ins (`list`, `dict`, `tuple`, `set`) instead of `List`, `Dict`, `Tuple`, `Set`
  - Use `X | None` instead of `Optional[X]`
  - Use specific types like Task, SelectedComponents, etc.
  - All API responses must use Pydantic BaseModel classes for type safety
  - Always add type annotations when declaring new variables:
    ```python
    count: int = 0
    names: list[str] = []
    data: dict[str, Any] = {}
    ```
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE_CASE for constants
  - Prefix booleans with `is_` or `has_`
- **Functions**: Keep under 200 lines, descriptive parameter names
  - Must have :param and :return docstrings
  - All new variables must have inline type annotations
- **Error handling**: Use specific exception types, log errors with context
- **Documentation**: Triple double-quotes for docstrings describing purpose, parameters, and return values
- **String Building**: Use f-strings and single string literals instead of building lists of strings
  - Prefer:
    ```python
    return f"""
    <recording>
      <n>{self.name}</n>
      <annotation>{self.annotation}</annotation>
      ...
    </recording>
    """
    ```
  - Instead of:
    ```python
    parts = ["<recording>"]
    parts.append(f"<n>{self.name}</n>")
    parts.append(f"<annotation>{self.annotation}</annotation>")
    return "\n".join(parts)
    ```
  - **Comments**: Code should be self-documenting - avoid redundant inline comments
    - Only use comments to explain complex business logic or non-obvious design decisions
- **Prompts**: Place at top of file in UPPER_SNAKE_CASE, use .strip()

## Class Design Principles

- **Cohesion**: Classes should have a single responsibility (high cohesion)
- **Coupling**: Minimize dependencies between classes (low coupling)
  - Prefer data coupling over control/stamp coupling
- **Abstraction**: Only create layers when justified by reuse needs
  - Avoid premature abstraction
  - Keep inheritance hierarchies shallow (≤3 levels)
- **Composition**: Favor composition over inheritance
- **Instance Methods**: Should either:
  1. Perform actions using object state
  2. Return computed values from state
  - Avoid methods that do both (command-query separation)

## Refactoring Guidelines

- **Function Creation**: Only extract methods when:
  - Code is reused in ≥2 places
  - Improves readability of complex logic
  - Needs different error handling
- **Class Creation**: Justified when:
  - Managing complex state transitions
  - Grouping related functionality
  - Implementing clear interfaces

## Anti-Patterns to Avoid

- **God Classes**: Classes doing too many unrelated things
- **Feature Envy**: Methods that access other classes' data more than their own
- **Shotgun Surgery**: Making many small changes across classes for single features
- **Excessive Inheritance**: Deep inheritance trees that are hard to follow

## Type Safety and Pattern Matching

- **Use pattern matching** over attribute checking (`hasattr`) when working with typed objects
- For Python 3.10+, prefer structural pattern matching with `match/case` for processing typed data
- For earlier Python versions, use `isinstance()` with explicit type checks
- Never use `hasattr()` to check for attributes that should be guaranteed by type definitions

## Data Representation and Serialization

- **Centralize representation logic** within model classes
- Implement `xml()`, `json()`, `artifact_xml()`, or similar methods directly on data classes/models
- For Pydantic models, use `@property` methods to define standardized serialization formats
- Consumer code should use these methods rather than reimplementing serialization logic
- **XML Representation Pattern**:

  - Models that need XML representation should provide an `xml` or `artifact_xml` property
  - External formatter utilities should call these model properties rather than duplicating formatting logic
  - Example:

    ```python
    class Recording(BaseModel):
        @property
        def artifact_xml(self) -> str:
            """Returns XML representation for use in artifacts."""
            # Implementation here

    def format_recording(recording: Recording) -> str:
        return recording.artifact_xml
    ```

  - When implementing serialization methods that build documents, prefer f-strings for simple cases and list concatenation for complex ones
  - Always include descriptive docstrings for serialization methods explaining their purpose

## Model Design Principles

- **Artifact System Design Pattern**:

  - For complex objects that need different presentation formats (like recordings):
    1. Create base artifact classes with common fields
    2. Derive specialized artifact types with specific fields and behaviors
    3. Implement custom XML/JSON serialization in each type via `@property` methods
    4. Provide utility functions to extract artifacts from raw data
  - Example:

    ```python
    class RecordingArtifact(BaseModel):
        """Base class for all recording-based artifacts."""
        id: str
        title: str

        @property
        def artifact_xml(self) -> str:
            """Base XML representation that derived classes extend."""

    class ConsoleLogArtifact(RecordingArtifact):
        """Specialized artifact for console logs."""
        log: ConsoleLog
        severity: str

        @property
        def artifact_xml(self) -> str:
            """Console-specific XML representation."""
    ```

- **Type Safety in Multi-Model Systems**:
  - When creating model hierarchies, ensure parameter types in functions accurately reflect expected models
  - Check for field compatibility when evolving models (e.g., field renames or removals)
  - Update default empty object creation to match current model structure
