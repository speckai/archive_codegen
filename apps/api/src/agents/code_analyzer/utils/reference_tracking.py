import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def parse_markdown_links(issue_description: str) -> tuple[set[str], set[str]]:
    """
    Extracts file paths and image references from markdown links in the issue description.
    Uses a negative lookahead to handle Next.js route parentheses properly.

    :param issue_description: Text containing markdown file references
    :return: Tuple of (referenced_file_paths, referenced_image_indices) as sets
    """
    pattern: str = r"\[(?:[^\[\]])*\]\(([^()]*(?:\([^()]*\)[^()]*)*)\)"
    matches: list[str] = re.findall(pattern, issue_description)

    file_paths: set[str] = {match for match in matches if not match.isdigit()}
    image_references: set[str] = {match for match in matches if match.isdigit()}

    return file_paths, image_references


# Add regex test cases
if __name__ == "__main__":
    test_cases: list[tuple[str, set[str], set[str]]] = [
        # Basic links
        ("[Link text](path/to/file.js)", {"path/to/file.js"}, set()),
        # Image references
        ("[Screenshot](1)", set(), {"1"}),
        # Multiple links
        (
            "Check [this file](src/components/Button.tsx) and [this one](src/utils/helpers.js)",
            {"src/components/Button.tsx", "src/utils/helpers.js"},
            set(),
        ),
        # Next.js parentheses in paths
        ("See [dynamic route](pages/[id]/index.tsx)", {"pages/[id]/index.tsx"}, set()),
        # Complex case with nested parentheses
        (
            "Multiple: [link1](path/with/(nested)/file.js) and [link2](another/[path].tsx)",
            {"path/with/(nested)/file.js", "another/[path].tsx"},
            set(),
        ),
        # Mixed image and file references
        (
            "Files: [file1](path1.js), [file2](path2.js) Images: [img1](1), [img2](2)",
            {"path1.js", "path2.js"},
            {"1", "2"},
        ),
    ]

    # Run tests
    for i, (input_text, expected_files, expected_images) in enumerate(test_cases):
        files: set[str]
        images: set[str]
        files, images = parse_markdown_links(input_text)
        assert (
            files == expected_files
        ), f"Test {i + 1} failed for files: got {files}, expected {expected_files}"
        assert (
            images == expected_images
        ), f"Test {i + 1} failed for images: got {images}, expected {expected_images}"

    print("All tests passed!")
