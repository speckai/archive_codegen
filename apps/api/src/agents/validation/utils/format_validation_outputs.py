"""
Utility functions for formatting validation outputs in different formats.
"""

from src.schemas.core.validation import RuntimeResult, TestPlan, TestResult
from src.schemas.core.validation.test_plan import TestCase


def format_markdown_feedback(
    visual_results: list[TestResult],
    console_results: list[RuntimeResult],
    test_plan: TestPlan | None = None,
    visual_test_cases: list[TestCase] | None = None,
) -> str:
    """
    Format validation data into human-readable markdown feedback.

    Args:
        visual_results: Results from visual tests
        console_results: Results from console tests
        test_plan: The test plan that was executed
        visual_test_cases: Test cases from visual tester to ensure correct pairing

    Returns:
        Formatted markdown string with validation feedback
    """
    feedback_parts = ["## Validation Feedback"]

    if test_plan:
        feedback_parts.append("### Test Plan Summary")
        feedback_parts.append(f"- **URLs Tested**: {', '.join(test_plan.urls_to_test)}")
        feedback_parts.append(
            f"- **Number of Test Cases**: {len(test_plan.test_cases)}"
        )

    # Add visual test feedback
    if visual_results:
        feedback_parts.append("### Visual Test Results")

        for i, result in enumerate(visual_results):
            # Get the corresponding test case if available
            test_case: TestCase = (
                visual_test_cases[i]
                if visual_test_cases and i < len(visual_test_cases)
                else None
            )

            # Get validation results
            validation_results = result.validation_results
            if not validation_results:
                continue

            for validation in validation_results:
                test_description = (
                    test_case.test_instructions if test_case else "Unknown test"
                )
                status = "✅ Passed" if validation.success else "❌ Failed"

                feedback_parts.append(f"**{test_description}** - {status}")

                if not validation.success:
                    feedback_parts.append(f"- **Issue**: {validation.message}")

                    # Add screenshot references if available
                    if validation.screenshots:
                        screenshot_refs = [
                            f"Screenshot {k + 1}"
                            for k in range(len(validation.screenshots))
                        ]
                        feedback_parts.append(
                            f"- **Visual evidence**: {', '.join(screenshot_refs)}"
                        )

                    # Add validation criteria if available from test case
                    if test_case:
                        feedback_parts.append(
                            f"- **Expected behavior**: {test_case.validation_criteria}"
                        )

    # Add console test feedback
    if console_results:
        feedback_parts.append("### Console Test Results")
        for result in console_results:
            url = result.url_tested

            # Check if there are any errors
            has_stderr = bool(result.stderr)
            has_stdout_errors = any("error" in line.lower() for line in result.stdout)

            if has_stderr or has_stdout_errors:
                feedback_parts.append(f"**URL**: {url}")

                if has_stderr:
                    feedback_parts.append("**Console Errors**:")
                    for err in result.stderr:
                        feedback_parts.append(f"- `{err}`")

                if has_stdout_errors:
                    feedback_parts.append("**Output Errors**:")
                    for line in result.stdout:
                        if "error" in line.lower():
                            feedback_parts.append(f"- `{line}`")

    # Add summary and recommendations
    feedback_parts.append("### Summary")
    all_passed: bool = all(
        all(vr.success for vr in result.validation_results) for result in visual_results
    ) and not any(result.stderr for result in console_results)

    if all_passed:
        feedback_parts.append("✅ All tests passed successfully.")
    else:
        feedback_parts.append("❌ Some tests failed. Please address the issues above.")

    return "\n\n".join(feedback_parts)


def format_compact_summary(
    visual_results: list[TestResult], console_results: list[RuntimeResult]
) -> str:
    """
    Format validation data into a compact summary.

    Args:
        visual_results: Results from visual tests
        console_results: Results from console tests

    Returns:
        Compact summary of validation results
    """
    # Count visual test results
    visual_total = sum(len(result.validation_results) for result in visual_results)
    visual_passed = sum(
        sum(1 for vr in result.validation_results if vr.success)
        for result in visual_results
    )

    # Count console errors
    console_errors = sum(
        1
        for result in console_results
        if result.stderr or any("error" in line.lower() for line in result.stdout)
    )

    summary = [
        "## Validation Summary",
        f"- Visual Tests: {visual_passed}/{visual_total} passed",
        f"- Console Tests: {len(console_results) - console_errors}/{len(console_results)} passed",
    ]

    return "\n".join(summary)


def format_json_data(
    visual_results: list[TestResult],
    console_results: list[RuntimeResult],
    test_plan: TestPlan | None = None,
    visual_test_cases: list[TestCase] | None = None,
) -> dict:
    """
    Format validation data into a structured JSON object.

    Args:
        visual_results: Results from visual tests
        console_results: Results from console tests
        test_plan: The test plan that was executed
        visual_test_cases: Test cases from visual tester to ensure correct pairing

    Returns:
        Dictionary with structured validation data
    """
    # Format visual test results
    visual_data = []
    for i, result in enumerate(visual_results):
        test_case = (
            visual_test_cases[i]
            if visual_test_cases and i < len(visual_test_cases)
            else None
        )

        for validation in result.validation_results:
            visual_data.append(
                {
                    "test_description": (
                        test_case.test_instructions if test_case else "Unknown test"
                    ),
                    "success": validation.success,
                    "message": validation.message,
                    "screenshots": len(validation.screenshots),
                    "validation_criteria": (
                        test_case.validation_criteria if test_case else None
                    ),
                }
            )

    # Format console test results
    console_data = []
    for result in console_results:
        stderr_errors = result.stderr
        stdout_errors = [line for line in result.stdout if "error" in line.lower()]

        if stderr_errors or stdout_errors:
            console_data.append(
                {
                    "url": result.url_tested,
                    "stderr_errors": stderr_errors,
                    "stdout_errors": stdout_errors,
                }
            )

    # Create the final structure
    return {
        "test_plan": {
            "urls_tested": test_plan.urls_to_test if test_plan else [],
            "test_cases_count": len(test_plan.test_cases) if test_plan else 0,
        },
        "visual_results": visual_data,
        "console_results": console_data,
        "summary": {
            "visual_tests_passed": sum(1 for item in visual_data if item["success"]),
            "visual_tests_total": len(visual_data),
            "console_tests_with_errors": len(console_data),
            "console_tests_total": len(console_results),
        },
    }
