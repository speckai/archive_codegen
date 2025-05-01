import os

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

import asyncio
import json
import re
import shutil
import subprocess
from datetime import datetime

from src.agents.utils.task.debug.common import Debug, DebugSettings
from src.schemas.account import User
from src.schemas.core.common.files import SelectedComponents

# Hardcoded mapping from commits to completed user stories
COMMIT_TO_STORIES = {
    "cdafa6578affe0b93eac443e5e2bde8809b8c831": [2, 19, 20],
    "6b4512e6afe54985c62c29cb9a480807b4e1b3af": [3, 6, 7, 8, 13],
    "73cd2650972f9aef7b7dd8a568736e37abbaf46f": [9, 10, 11, 12],
    "bbf87d16280434beaf3ab9a63537d3e58bb174e8": [16, 17],
    "227aa20238a33d6822a425bd5ae793c9c0cd20a2": [14, 15],
    "08634fc8f8423b2a3209d9d3223a0bae22114e9e": [5],
}

# Also store the commit order for easy lookup
COMMIT_ORDER = [
    "cdafa6578affe0b93eac443e5e2bde8809b8c831",  # lesson 2
    "6b4512e6afe54985c62c29cb9a480807b4e1b3af",  # lesson 3
    "73cd2650972f9aef7b7dd8a568736e37abbaf46f",  # lesson 4
    "bbf87d16280434beaf3ab9a63537d3e58bb174e8",  # lesson 8
    "227aa20238a33d6822a425bd5ae793c9c0cd20a2",  # lesson 9
    "08634fc8f8423b2a3209d9d3223a0bae22114e9e",  # lesson 10
]

# Original repo path
ORIGINAL_REPO = "../../packages/nextjs-full-stack-project"

# Directory for test repos
TEST_REPOS_DIR = "test_repos"


def run_git_command(cmd: list[str], cwd: str = None) -> str:
    """Run a git command in the specified directory"""
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.stdout


def setup_test_repo(commit_hash: str) -> str:
    """Create a directory in test_repos and clone the repo at the specified commit"""
    # Create test_repos directory if it doesn't exist
    os.makedirs(TEST_REPOS_DIR, exist_ok=True)

    # Create a directory for this test run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_dir = os.path.join(TEST_REPOS_DIR, f"test_{commit_hash[:8]}_{timestamp}")
    os.makedirs(test_dir)

    # Clone the repo
    run_git_command(["git", "clone", ORIGINAL_REPO, test_dir])

    # Checkout the specific commit
    run_git_command(["git", "checkout", commit_hash], cwd=test_dir)

    return test_dir


def get_user_story_text(story_numbers: list[int], repo_dir: str) -> str:
    """Get the full text of user stories by their numbers"""
    stories_content = run_git_command(
        ["git", "show", "HEAD:UserStories.md"], cwd=repo_dir
    )
    story_texts = []

    for line in stories_content.split("\n"):
        for num in story_numbers:
            if line.startswith(f"{num}. "):
                # Remove the checkbox part and get just the requirement text
                story_text = re.sub(r"^\d+\. \[[ x]\] ", "", line)
                story_texts.append(f"#{num}: {story_text}")

    return "\n".join(story_texts)


async def test_commit_pair(
    prev_commit: str, current_commit: str, stories_completed: list[int]
):
    """Test a pair of commits where prev_commit is the starting state and current_commit is the ground truth"""

    # Create a directory with the repo at the previous commit
    test_dir = setup_test_repo(prev_commit)
    print(f"Created test repo at {test_dir}")

    try:
        # Initialize debug session
        user = User(
            id="e2534d13-0bda-42a1-8cf1-cb376b1a73bf", email="degtrdg@gmail.com"
        )
        debug_config = Debug(
            original_repo_dir=ORIGINAL_REPO,
            repo_dir=test_dir,
            settings=DebugSettings(
                user=user,
                created_repo_id="test-repo",
                package_manager="npm",
                port=3000,
                install_command="npm install",
                dev_command="npm run dev",
                root_directory="/",
            ),
        )

        task = Task(user, "test-session", debug=debug_config)
        await task.initializer.initialize()

        # Get the user story text for the prompt
        story_text = get_user_story_text(stories_completed, test_dir)
        prompt = f"I want to implement these user stories:\n{story_text}"

        # Run the session with the prompt
        await session.chat.handle_user_message(
            prompt,
            selected_components=SelectedComponents(selected_components=[]),
            api_requests=[],
            images=[],
        )

        # Get the expected diff from the original repo
        expected_diff = run_git_command(
            ["git", "diff", prev_commit, current_commit], cwd=ORIGINAL_REPO
        )

        # Store the results
        result = {
            "prev_commit": prev_commit,
            "current_commit": current_commit,
            "stories_completed": stories_completed,
            "prompt": prompt,
            "expected_diff": expected_diff,
            "test_repo_dir": test_dir,
        }

        return result

    except Exception as e:
        print(f"Error during testing: {e}")
        # Clean up on error
        shutil.rmtree(test_dir)
        raise


async def main():
    # Test a single commit pair
    commit = COMMIT_ORDER[1]  # Get second commit with stories
    prev_commit = COMMIT_ORDER[0]  # Get first commit
    stories = COMMIT_TO_STORIES[commit]

    print(f"\nTesting commit {commit[:8]}")
    print(f"Previous commit: {prev_commit[:8]}")
    print(f"Stories to complete: {stories}")

    result = await test_commit_pair(prev_commit, commit, stories)

    with open("test_results.json", "w") as f:
        json.dump([result], f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
