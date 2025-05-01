from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from src.agents.utils.base_agent import BaseAgent
from src.schemas.llm import Model
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task

# Initial frontend filtering prompts
TREE_FILTER_SYSTEM_PROMPT = """You are a frontend code expert. Your task is to analyze directory trees and identify patterns of files and directories that should be ignored to focus on code relevant to frontend development."""

TREE_FILTER_USER_PROMPT = """Given this directory tree from 'tree -L 5 --gitignore -I {ignore_patterns}':

{tree_output}

List ONLY the patterns that should be ignored to focus on frontend-related code. 
Basically ignore folders at the high level which are languages other than js/ts (like python, go, etc.). Remove config folders like fern or openapi if you think they're not relevant to frontend development.

Keep shared packages and code that frontend engineers might need to modify. Entire Nextjs folders are fine to include even if they're technically fullstack.
"""

# Query-based refinement prompts
TREE_PROCESSOR_SYSTEM_PROMPT = """You are a strategic frontend development assistant. Your goal is to help filter a codebase to show only the most relevant files for implementing a specific frontend feature or task, while being cost-conscious about which files need to be processed.

Key considerations:
- Each file that remains visible will be processed by another LLM at a cost (~$0.01 per 100k chars)
- Generated/build files usually have low signal-to-noise ratio and high character count
- Consider which files are truly needed vs which can be filtered out
- Some patterns (like generated files) should always be filtered, while others might be task-specific"""

TREE_PROCESSOR_USER_PROMPT = """Given this frontend-focused directory tree:

{tree_output}

Task/Query from user: {focus_query}

Current filtering state:
- Persistent filters: {persistent_filters}  # These filters stay between different queries
- Query-specific filters: {query_filters}   # These filters only apply to current task

Your task is to suggest filter patterns to exclude irrelevant files while keeping necessary context for the task.

<example>
Task: "Add a loading spinner to the dashboard table when fetching data"
Round: 1 of 3 (Focus on removing large, obviously unrelated sections)

Given tree:
├── apps
│   ├── web
│   │   ├── pages
│   │   │   ├── analytics
│   │   │   │   ├── index.tsx
│   │   │   │   ├── reports.tsx
│   │   │   │   └── metrics.tsx
│   │   │   ├── inventory
│   │   │   │   ├── products
│   │   │   │   │   ├── index.tsx
│   │   │   │   │   ├── stats.tsx
│   │   │   │   │   └── trends.tsx
│   │   │   │   └── overview.tsx
│   │   │   ├── auth
│   │   │   │   ├── login.tsx
│   │   │   │   ├── signup.tsx
│   │   │   │   └── layout.tsx
│   │   │   ├── settings
│   │   │   │   ├── index.tsx
│   │   │   │   ├── profile.tsx
│   │   │   │   └── layout.tsx
│   │   │   └── admin
│   │   │       ├── index.tsx
│   │   │       ├── users.tsx
│   │   │       └── layout.tsx
│   │   ├── components
│   │   │   ├── WeatherWidget.tsx
│   │   │   ├── MetricsOverview.tsx
│   │   │   ├── PrinterStatus.tsx
│   │   │   ├── CoffeeOrderForm.tsx
│   │   │   ├── MeetingRoomBooking.tsx
│   │   │   ├── OfficeMap.tsx
│   │   │   ├── dashboard
│   │   │   │   ├── Table.tsx
│   │   │   │   ├── TableHeader.tsx
│   │   │   │   ├── TableRow.tsx
│   │   │   │   ├── TableCell.tsx
│   │   │   │   ├── TableFooter.tsx
│   │   │   │   ├── DashboardLayout.tsx
│   │   │   │   └── hooks
│   │   │   │       ├── useTableData.ts
│   │   │   │       ├── useTableSort.ts
│   │   │   │       └── useTableLoading.ts
│   │   │   ├── auth
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   ├── SignupForm.tsx
│   │   │   │   ├── ResetPassword.tsx
│   │   │   │   └── AuthLayout.tsx
│   │   │   ├── settings
│   │   │   │   ├── SettingsForm.tsx
│   │   │   │   ├── ProfileSection.tsx
│   │   │   │   ├── SecuritySection.tsx
│   │   │   │   └── NotificationsSection.tsx
│   │   │   └── shared
│   │   │       ├── Button.tsx
│   │   │       ├── Input.tsx
│   │   │       ├── Modal.tsx
│   │   │       ├── Spinner.tsx
│   │   │       ├── Card.tsx
│   │   │       └── icons
│   │   │           ├── Loading.tsx
│   │   │           ├── Check.tsx
│   │   │           └── Error.tsx
│   │   ├── hooks
│   │   │   ├── useApi.ts
│   │   │   ├── useLoading.ts
│   │   │   ├── useAuth.ts
│   │   │   ├── useNotifications.ts
│   │   │   └── useTheme.ts
│   │   ├── context
│   │   │   ├── LoadingContext.tsx
│   │   │   ├── ApiContext.tsx
│   │   │   ├── AuthContext.tsx
│   │   │   ├── NotificationsContext.tsx
│   │   │   └── ThemeContext.tsx
│   │   └── lib
│   ├── mobile
│   │   ├── src
│   │   │   ├── screens
│   │   │   ├── components
│   │   │   └── utils
│   │   └── ios
│   │       ├── assets
│   │       ├── src
│   │       │   ├── screens
│   │       └── tests
│   ├── desktop
│   │   ├── main
│   │   └── renderer
│   └── docs
│       ├── api
│       │   ├── reference.md
│       │   └── changelog.md
│       ├── guides
│       │   ├── getting-started.md
│       │   └── deployment.md
│       └── architecture
│           ├── diagrams
│           └── decisions
├── packages
│   ├── ui
│   │   ├── components
│   │   ├── hooks
│   │   └── styles
│   ├── api-client
│   ├── backend
│   │   ├── src
│   │   │   ├── controllers
│   │   │   ├── models
│   │   │   └── services
│   │   │   └── tests
│   │   └── tests
│   ├── mobile-core
│   └── desktop-core
├── tools
│   ├── scripts
│   ├── ci
│   └── dev
└── infrastructure
    ├── terraform
    ├── kubernetes
    └── docker

Good first-round filters (focusing on large sections):
- "apps/mobile/**" - Entire mobile app unrelated
- "apps/desktop/**" - Entire desktop app unrelated
- "apps/docs/**" - Documentation app unrelated
- "packages/mobile-core/**" - Mobile utilities unrelated
- "packages/desktop-core/**" - Desktop utilities unrelated
- "infrastructure/**" - Infrastructure code unrelated
- "tools/**" - Development tools unrelated
- "apps/web/components/auth/**" - Auth components unrelated

Round: 2 of 3 (Analyze potential dashboard locations and feature sections)
Remaining tree after first round:
├── apps
│   └── web
│       ├── pages
│       │   ├── analytics
│       │   │   ├── index.tsx
│       │   │   ├── reports.tsx
│       │   │   └── metrics.tsx
│       │   ├── inventory
│       │   │   ├── products
│       │   │   │   ├── index.tsx
│       │   │   │   ├── stats.tsx
│       │   │   │   └── trends.tsx
│       │   │   └── overview.tsx
│       │   ├── settings
│       │   │   ├── index.tsx
│       │   │   ├── profile.tsx
│       │   │   └── layout.tsx
│       │   └── admin
│       │       ├── index.tsx
│       │       ├── users.tsx
│       │       └── layout.tsx
│       ├── components
│       │   ├── WeatherWidget.tsx
│       │   ├── MetricsOverview.tsx
│       │   ├── PrinterStatus.tsx
│       │   ├── CoffeeOrderForm.tsx
│       │   ├── MeetingRoomBooking.tsx
│       │   ├── OfficeMap.tsx
│       │   ├── dashboard
│       │   │   ├── Table.tsx
│       │   │   ├── TableHeader.tsx
│       │   │   ├── TableRow.tsx
│       │   │   ├── TableCell.tsx
│       │   │   ├── TableFooter.tsx
│       │   │   ├── DashboardLayout.tsx
│       │   │   └── hooks
│       │   │       ├── useTableData.ts
│       │   │       ├── useTableSort.ts
│       │   │       └── useTableLoading.ts
│       │   └── shared
│       │       ├── Button.tsx
│       │       ├── Input.tsx
│       │       ├── Modal.tsx
│       │       ├── Spinner.tsx
│       │       ├── Card.tsx
│       │       └── icons
│       │           ├── Loading.tsx
│       │           ├── Check.tsx
│       │           └── Error.tsx
│       ├── hooks
│       │   ├── useApi.ts
│       │   ├── useLoading.ts
│       │   ├── useNotifications.ts
│       │   └── useTheme.ts
│       ├── context
│       │   ├── LoadingContext.tsx
│       │   ├── ApiContext.tsx
│       │   ├── NotificationsContext.tsx
│       │   └── ThemeContext.tsx
│       └── lib
└── packages
├── ui
│   ├── components
│   │   ├── table
│   │   ├── loading
│   │   └── buttons
│   └── hooks
└── api-client

Good later round filters:
- "apps/web/components/icons/**" - Icons are unrelated
- "apps/web/hooks/useNotifications.ts" - Notifications are unrelated
- "apps/web/context/NotificationsContext.tsx" - Notifications context is unrelated
- "apps/web/components/WeatherWidget.tsx" - Weather widget is unrelated
- "apps/web/components/PrinterStatus.tsx" - Printer status is unrelated
- "apps/web/components/CoffeeOrderForm.tsx" - Coffee ordering is unrelated
- "apps/web/components/MeetingRoomBooking.tsx" - Meeting room booking is unrelated
- "apps/web/components/OfficeMap.tsx" - Office map is unrelated

<example>

Remember:
1. Never fully filter the nextjs pages directory - contains critical route entry points. This might not be called pages and might be called something else. Use your judgement.
2. Each unfiltered file has processing costs. But filtering something that's necessary for the task is more expensive.
3. Retain relevant shared/utility code (stores, hooks with global state)
4. Safe to filter: tests, generated code
5. For monorepos: focus on relevant apps/packages
6. Add specific file-level filters when needed towards later rounds even if there are a lot of them
7. Use gitignore-compatible patterns
8. If you're repository is not that large (like the example), you actually don't need to filter that much. The example is just for illustration. If you were given the example, you probably don't need to filter anything.
9. Think deeply about the context of the query. For example, if the query is about a specific feature, you might need to think about how it would affect the other parts of the codebase (ex. inputting data might affect the data store or adding a page might affect the layout).

If uncertain about filter completeness:
- Set one_more_round=True
- Currently on round {curr_round} of {max_rounds}
- Start with high-confidence, broad filters. That let's you see a less cluttered tree for the later rounds.
- Later rounds: focus on remaining files needing detailed review

Give filters for the current task."""

FRONTEND_ANALYZER_PROMPT = """Analyze these TypeScript/JavaScript project directories found in the codebase:

{project_dirs}

For each directory, determine if it's:
1. A frontend application (containing pages/routes/views)
2. A package/library directory

Look for patterns like:
- Frontend apps usually have pages/routes/app directories, or similar Next.js/React routing structures
- Packages usually live in a packages/* directory or have package.json indicating they're libraries
- Packages are meant to be imported by other code, while frontends are complete applications

Output a JSON object with:
- frontends: list of frontend application paths
- packages: list of package directory paths
- reasoning: brief explanation of the classification
"""


class FrontendAnalysis(BaseModel):
    """Analysis of frontend project directories"""

    reasoning: str = Field(
        description="Explanation of how the directories were classified"
    )
    frontends: list[str] = Field(
        description="Paths to all frontend application directories"
    )
    packages: list[str] = Field(description="List of package directory paths")
    backend_dirs: list[str] = Field(
        description="Paths to all backend application directories"
    )


class IgnorePatterns(BaseModel):
    """Structured output for LLM-suggested ignore patterns"""

    reasoning: str = Field(description="Explanation for why these patterns were chosen")
    patterns: list[str] = Field(description="List of patterns to ignore")


class Filter(BaseModel):
    """Structured model for tree command filters"""

    pattern: str = Field(description="The pattern to filter")
    is_persistent: bool = Field(
        description="Whether this filter persists between queries",
    )


@dataclass
class TreeResult:
    """Structured output for tree command results"""

    tree_output: str
    ignore_patterns: set[str]
    command_used: str
    new_filters: list[Filter] = Field(
        description="New filters that were added",
        default_factory=list,
    )


class TreeCommandSuggestion(BaseModel):
    """Structured output for LLM-suggested tree command refinements"""

    reasoning: str = Field(description="Explanation for the suggested changes")
    add_filters: list[Filter] = Field(
        description="New filters to add",
    )
    remove_filters: list[str] = Field(
        description="Filter patterns to remove",
    )
    one_more_round: bool = Field(
        description="Whether to run the refinement again. If you think that the current state is good enough, you can set this to False.",
    )


@dataclass
class TreeState:
    """State management for tree operations"""

    raw_tree: str
    current_command: str
    tree_hash: str
    saved_filters: set[str]  # Persistent filters between runs
    query_filters: set[str]  # Temporary filters for current query


class TreeAgent(BaseAgent):
    def __init__(self, task: "Task") -> None:
        super().__init__(task)
        self._state: TreeState | None = None
        self.default_ignore = {
            # Build and cache directories
            "build",
            "dist",
            "__pycache__",
            "node_modules",
            ".venv",
            # Compiled files
            "*.pyc",
            "*.mjs",
            # Documentation and config
            "*.mdx",
            "*.xml",
            # Media files
            "*.zip",
            "*.jpg",
            "*.jpeg",
            "*.png",
            "*.svg",
            "*.gif",
            "*.ico",
            "*.webp",
            "*.lock",
            "*.ipynb",
        }
        self.frontend_tree_result: TreeResult | None = None
        self.filters: dict[str, Filter] = {}  # pattern -> Filter

    def normalize_path(self, path: str) -> str:
        """
        Removes leading or '/', and trailing '/'.
        Converts examples like:
          '/app/web', 'app/web/'
        into:
          'app/web'
        it's meant for paths that are relative to the workspace path.
        """
        return path.removeprefix("/").removesuffix("/")

    async def _find_typescript_projects(self) -> list[str]:
        """
        Discovers TypeScript/JavaScript project roots by finding tsconfig.json files.
        Returns a list of directory paths containing TypeScript/JavaScript projects.
        """
        # ts_dirs = await self.task.sandbox.run_command(
        #     r'fd -H tsconfig.json -E node_modules -x dirname {}'
        # )
        ts_dirs = await self.task.sandbox.run_command(
            r'find . -name tsconfig.json -not -path "*/node_modules/*" -exec dirname {} \;'
        )
        if not ts_dirs.stdout.strip():
            raise ValueError("No TypeScript/JavaScript projects found")

        # this is relative to the root directory so it'll start with ./
        output_dirs = ts_dirs.stdout.strip().split("\n")
        # remove the './'. now it's relative to the workspace path
        return [dir.removeprefix("./") for dir in output_dirs]

    async def _generate_frontend_patterns(
        self, keep_paths: list[str], gitignore_content: str
    ) -> list[str]:
        frontend_patterns = ["", "# Temporary patterns for frontend tree"]

        # Group paths by their parent directory path
        parent_dirs = {}
        for path in keep_paths:
            # Split from right once to get parent path and subdir. Takes care of / case as well.
            parent, subdir = path.rsplit("/", maxsplit=1) if "/" in path else ("", path)

            if parent not in parent_dirs:
                parent_dirs[parent] = set()
            parent_dirs[parent].add(subdir)

        # Add patterns for directories to ignore
        for parent_path, keep_subdirs in parent_dirs.items():
            # Handle root level differently
            search_path = "." if not parent_path else parent_path
            find_cmd = f'find {search_path} -maxdepth 1 -type d -not -name "."'
            if parent_path:
                find_cmd += f' -not -name "{parent_path.split("/")[-1]}"'

            all_subdirs_result = await self.task.sandbox.run_command(find_cmd)

            for subdir in all_subdirs_result.stdout.split("\n"):
                if subdir:
                    normalized = self.normalize_path(subdir)
                    subdir_name = normalized.split("/")[-1]
                    if subdir_name not in keep_subdirs:
                        frontend_patterns.append(f"/{normalized}")
        # Add scoped versions of existing gitignore patterns
        frontend_patterns.extend(["", "# Scoped patterns for kept directories"])
        for path in keep_paths:
            for pattern in gitignore_content.splitlines():
                if not pattern or pattern.startswith("#"):
                    continue
                frontend_patterns.append(f"/{path}/{pattern}")

        return frontend_patterns

    async def _with_temporary_gitignore(self, patterns: list[str]) -> TreeResult:
        """
        Context manager-like function that temporarily modifies .gitignore, runs tree command,
        and restores the original .gitignore. Returns the tree command result.
        """
        # Backup current .gitignore
        gitignore_backup = await self.task.sandbox.run_command("cat .gitignore")

        try:
            # Add our patterns to .gitignore
            patterns_str = "\n".join(patterns)
            await self.task.sandbox.run_command(f'echo "{patterns_str}" > .gitignore')

            # Run tree command with the modified gitignore
            result = await self.task.sandbox.run_command("tree --gitignore .")

            return result.stdout
        finally:
            # Always restore original .gitignore
            await self.task.sandbox.run_command(
                f'printf "%s" "{gitignore_backup.stdout}" > .gitignore'
            )

    async def get_frontend_tree(self) -> TreeResult:
        """Initial indexing: Generate a tree of frontend-relevant code"""
        # TODO: do we need this rn?
        logger.debug("TODO: do we need this rn?")
        # Find TypeScript/JavaScript projects relative to the workspace path
        project_roots = await self._find_typescript_projects()

        # Analyze project structure using LLM
        project_dirs_info = "\n".join(
            [
                f"- {root}\n"
                + (
                    await self.task.sandbox.run_command(
                        f'''ls -la {root} | grep "^d" | head -n 50; 
                   ls -la {root} | grep -v "^d" | grep -v "total" | head -n 50;
                   echo "...";
                   ls -la {root} | grep "total"'''
                    )
                ).stdout
                + "\n"
                for root in project_roots
            ]
        )

        project_analysis: FrontendAnalysis = await self.llm_response(
            model_type=Model.GEMINI_2_0_FLASH,
            system="You are a frontend architecture expert who analyzes TypeScript/JavaScript projects.",
            message=FRONTEND_ANALYZER_PROMPT.format(project_dirs=project_dirs_info),
            response_model=FrontendAnalysis,
        )
        logger.debug(f"Frontend analysis: {project_analysis.reasoning}")

        # Get the main frontend and package paths we want to keep
        main_frontend = await self.task.settings.get_root_directory()
        # all of them are relative to the workspace path so this is good
        package_paths = [self.normalize_path(p) for p in project_analysis.packages]
        keep_paths = [self.normalize_path(main_frontend)] + package_paths

        # Get current gitignore content
        gitignore_backup = await self.task.sandbox.run_command("cat .gitignore")

        # Generate frontend-specific patterns
        frontend_patterns = await self._generate_frontend_patterns(
            keep_paths, gitignore_backup.stdout
        )

        # Combine existing gitignore with frontend patterns
        all_patterns = gitignore_backup.stdout.splitlines() + frontend_patterns

        # Run tree command with temporary gitignore
        tree_output = await self._with_temporary_gitignore(all_patterns)

        # Create final result
        all_ignore_patterns = self.default_ignore.union(set(frontend_patterns))
        self.frontend_tree_result = TreeResult(
            tree_output=tree_output,
            ignore_patterns=all_ignore_patterns,
            command_used="tree --gitignore",
        )

        return self.frontend_tree_result

    def _get_filters_by_type(self, persistent: bool) -> set[str]:
        """Get set of filter patterns by persistence type"""
        return {
            pattern
            for pattern, filter_obj in self.filters.items()
            if filter_obj.is_persistent == persistent
        }

    async def refine_tree(self, focus_query: str, max_rounds: int = 3) -> TreeResult:
        """Query-based refinement: Further filter the frontend tree based on a specific query"""
        if not self.frontend_tree_result:
            self.frontend_tree_result = await self.get_frontend_tree()

        current_tree = self.frontend_tree_result
        rounds = 0

        while rounds < max_rounds:
            logger.debug(f"Round {rounds}")
            rounds += 1
            suggestion: TreeCommandSuggestion = await self.llm_response(
                model_type=Model.GEMINI_2_0_FLASH,
                system=TREE_PROCESSOR_SYSTEM_PROMPT,
                message=TREE_PROCESSOR_USER_PROMPT.format(
                    curr_round=rounds,
                    max_rounds=max_rounds,
                    tree_output=current_tree.tree_output,
                    focus_query=focus_query,
                    current_command=current_tree.command_used,
                    persistent_filters=self._get_filters_by_type(persistent=True),
                    query_filters=self._get_filters_by_type(persistent=False),
                ),
                response_model=TreeCommandSuggestion,
            )
            logger.debug(f"Round {rounds} - Suggestion: {suggestion.reasoning}")

            # Remove suggested filters
            for pattern in suggestion.remove_filters:
                self.filters.pop(pattern, None)

            # Add new filters
            for filter_obj in suggestion.add_filters:
                self.filters[filter_obj.pattern] = filter_obj

            # Backup current .gitignore
            try:
                gitignore_backup = await self.task.sandbox.run_command("cat .gitignore")

                # Add our patterns to .gitignore
                all_filters = self.frontend_tree_result.ignore_patterns.union(
                    pattern for pattern in self.filters.keys()
                )
                patterns_str = "\n".join(all_filters)
                await self.task.sandbox.run_command(
                    f'echo "{patterns_str}" >> .gitignore'
                )

                # Run tree command with just --gitignore
                result = await self.task.sandbox.run_command("tree --gitignore .")

                # Restore original .gitignore
                await self.task.sandbox.run_command(
                    f'printf "%s" "{gitignore_backup.stdout}" > .gitignore'
                )

                current_tree = TreeResult(
                    tree_output=result.stdout,
                    ignore_patterns=all_filters,
                    command_used="tree --gitignore .",
                    new_filters=suggestion.add_filters,
                )

                if not suggestion.one_more_round or rounds >= max_rounds:
                    logger.debug(f"Tree refinement complete after {rounds} rounds")
                    logger.debug(f"Tree output: {current_tree.tree_output}")
                    return current_tree

            except Exception as e:
                # If anything goes wrong, ensure we restore the original .gitignore
                await self.task.sandbox.run_command(
                    f'printf "%s" "{gitignore_backup.stdout}" > .gitignore'
                )
                raise e
