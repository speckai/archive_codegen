from typing import TYPE_CHECKING

from src.utils.prompt_utils import format_prompt

if TYPE_CHECKING:
    from src.schemas.core.common import Image, ScrapedSite


def SECTION_SYSTEM_PROMPT() -> str:
    return format_prompt("""
You are a senior React engineer that specializes in determining the best way to clone a website. To do this, you need to split the page into individual sections.
""")


def SECTION_USER_PROMPT(num_lines: int, chunks: list["Image"]) -> str:
    return format_prompt(f"""
Analyze the website screenshot{"s" if chunks else ""} that has been given to you with numbered horizontal lines (1 through {num_lines}) and determine the best points to split the page into sections.
Consider the visual hierarchy, content grouping, and natural breaks in the layout.
Sections can have some overlap if needed, but should generally be distinct. Make sure the start and end lines encapsulate the entire section, if it bleeds into another section that's fine.
Analyze the images as a whole, not separately. Sections can span multiple chunks. Indices can overlap in sections."

We are using this to split the page into sections to recreate the page in React. Each section will be a separate component, so any sections that reuse the same component contiguously should be combined into a single section.

Try to keep the sections as large as possible, but still separate major sections of the page.
If there's some blank space above/below a section, include it in the section as padding.
Guess where <section> tags would be placed in the HTML, and use this to determine the boundaries of the sections.

In your thinking, explain:
1. How the page is structured overall
2. What the main sections are
3. Why you chose each section's boundaries
4. What content each section contains
5. Consider the visual hierarchy of the page.

You will then analyze the page line by line. This is to consider what each line contains.

For each section, provide:
- thinking: Think through the page's structure and how to split it into sections
- description: What content this section contains
- start_line: The line number where the section begins (must be between 1 and {num_lines})
- end_line: The line number where the section ends (must be between 1 and {num_lines})


Choose sections that:
- Separate major content sections.
    - Examples: Navbar, hero section, footer, call to action, demo section, etc.
- Don't break up cohesive content blocks.
- Have white space between them.
- Encapsulate the ENTIRE section. Do not cut off any content, buttons or images. You can overlap lines if needed if a line serves multiple sections.

Example:
- Navbar between lines 1 and 4
- Hero section between lines 3 and 10
This could be because the navbar ends between lines 3 and 4, and the hero section also starts between lines 3 and 4.

If there are sections highlighted in dashed blue (#0000FF) lines, you MUST split the sections at the dashed blue lines. These are <section> tags in the HTML.
""")


def INTERNAL_LINKS_USER_PROMPT(site: "ScrapedSite") -> str:
    return format_prompt(f"""
You are a helpful assistant that analyzes images and extracts the top internal links from a website. We're recreating a website and want to know which pages are most important to scrape. Bias towards links that are accessible through the main page UI.

<internal_links>
{"\n".join(site.internal_links)}
</internal_links>

You must return no more than 4 links.
""")


def PLACEHOLDER_TASKS_SYSTEM_PROMPT() -> str:
    return format_prompt("""
You are an engineering manager deciding what to build next for a website.
""")


def PLACEHOLDER_TASKS_USER_PROMPT() -> str:
    return format_prompt("""
You are to provide three concise UI related tasks that a developer could do to improve this website.
                         

The first should be to change some content on the site from one thing to another. 
The second should be to build some component with content.
The third should be to change some component styling.

Do NOT pick the same component or section for multiple tasks unless there are not enough components to choose from.
Each task should be no longer than 10 words. \
Be specific on where exactly the component should be placed (eg. above/below X component or "exact text", the navbar, the footer, etc.)
                         
Return the three tasks in an XML format.
<task>
...
</task>
<task>
...
</task>
<task>
...
</task>
""")
