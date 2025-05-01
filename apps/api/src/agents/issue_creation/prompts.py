"""
Prompts for the issue creation agent.
"""

ISSUE_CREATION_SYSPROMPT = """You are a frontend engineer who will write a detailed issue description based on the provided context. This issue will be used by a junior engineer to implement the feature or fix. The issue will be displayed on GitHub."""

ISSUE_CREATION_PROMPT = """
You have been given a structured bug report and other information from a QA engineer.

Based on the components and the screenshot URLs that the QA has given so far, these are the code files that were picked up through search. This is the basis of your issue description without which you can't write a good issue description. The junior engineer can only edit the files that you reference in your issue description. You should bring up any files that you think should be added here in order to complete the issue description as that will inform the language model to look for more files to show you.

This is the bug report that the QA made.
<bug_report>
{bug_report_text}
</bug_report>

Your issue description should have an in-depth description of the bug. It should be detailed and include all the information that is needed to implement the fix. Detail which files need to be changed and what changes need to be made to each file or what files would be useful as reference even if they won't directly be changed (this will help with the search). End up with a single course of action that the engineer can take to fix the bug.

Reference the code files in your description using markdown link formats (ex. ![file_path](file_path)). This issue description will be the only thing left over to be given to a junior engineer to implement the fix. Have the exact file paths in your issue description because it will be regexed. Every file that you reference in your issue description will be weighted in the search of files to show you on the next iteration. The files you don't reference will be removed from the next search result.

When referencing bug report artifacts, use the provided names in markdown link syntax. For example:
<example_link>
![Console error showing 405 status](console_f50196c1)
</example_link>

Make sure these are on their own lines since they are block elements

Since we're already rendering the bug report in the issue description, don't include any visual artifacts that were already used in the bug report unless necessary to explain something. We'll be giving the junior engineer the issue description that you're writing after they're done reading the bug report.

Do not go outside the scope of the issue unless specifically asked to do so. You have a propensity to do this. This includes trying to rewrite something instead of fixing it like the issue writer intended (unless the rewrite is absolutely necessary). This is supposed to be a bug fix, so you don't want to be intrusive and change things, you should be targeted. You want to make it easy for the human devs to review the changes once they are made and not have to edit them.

<hint>
Be careful to not mess up the implementation in one viewport when fixing an issue in another viewport. Also be sublte in your changes.

for this specific issue, you only need to make this change to fix the issue:
      position: {{{{ top: `${{cardHeight * 1.5 + 30}}px`, right: "0" }}}},
</hint>

Only output the issue description, no other text. Make sure to maintain the practices that are seen in the codebase (ex. if they use tailwind, don't use inline styles or shadcn vs material-ui, etc).
""".strip()
