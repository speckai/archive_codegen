from src.utils.prompt_utils import format_prompt

MULTI_SECTION_EDIT_EXAMPLE = format_prompt(
    """
<edits>
<section_edit>
<original_code_section>return <div>Hello World Old</div>;</original_code_section>
<new_code_section>return <div>Hello World New</div>;</new_code_section>
</section_edit>
</section_edit>
<section_edit>
<original_code_section>export default function Foo() {
    return <div>Foo Old</div>;
}</original_code_section>
<new_code_section>export default function Bar() {
    return <div>Bar Foo</div>;
}</new_code_section>
</section_edit>
</edits>
"""
)

FULL_EDIT_EXAMPLE = format_prompt(
    """
<edits>
<full_file_contents>
<file_contents>export default function Home() {
    return <div>Hello World</div>;
}
</file_contents>
</full_file_contents>
</edits>
"""
)


def EDIT_FILE_USER_PROMPT(
    purpose: str,
    description: str,
    thinking: str,
    task_context: str,
    where_to_add: str,
    current_file_path: str,
    all_file_paths: str,
    file_contents: str,
    needs_search: bool,
    is_scraped_site: bool,
    dependencies_xml: str,
    special_instructions_to_follow: str,
) -> str:
    return format_prompt(
        f"""
The assistant is about to edit a file and overwrite the current file contents. The following information is provided:

The purpose of the edit:
<purpose>
{purpose.strip()}
</purpose>

The description of what to edit in the file:
<description>
{description.strip()}
</description>

The thought process behind the edit from the planner:
<thinking>
{thinking.strip()}
</thinking>

The context of the current task the user is trying to complete:
<task_context>
{task_context.strip()}
</task_context>

The location within the file where the changes should be made:
<where_to_add>
{where_to_add.strip()}
</where_to_add>

The path to the file:
<current_file_path>
{current_file_path.strip()}
</current_file_path>

The full current file contents:
<file_contents>
{file_contents.strip()}
</file_contents>

The dependencies and devDependencies from package.json:
{dependencies_xml.strip()}

{
            f'''
All file paths in the codebase:
<all_file_paths>
{all_file_paths.strip()}
</all_file_paths>
'''.strip()
            if needs_search
            else ""
        }


{
            f'''
Special rules from the end user to follow. If any rules are relevant, you MUST consider them when editing the file:
{special_instructions_to_follow}
'''.strip()
            if special_instructions_to_follow
            else ""
        }

---

Your task:
1. Carefully review the provided information, especially the purpose and thinking behind the edit.
2. Analyze the current file contents and the suggested location for the changes.
3. Review the initial user request. This is what the user wants to achieve, so tailor your implementation to achieve the goal. This may have details or content that you will need to use for your implementation. Implement any and all details that are provided.
    - Consider the purpose, description, context and the initial user request to plan out what needs to be implemented.
4. Consider the similar files for context and consistency.
    - Specifically consider if the file uses lighter or darker colors and keep that consistent unless the user requests a specific color. For example if the button is light blue and we want to change the color to purple, we should change it to light purple.
5. Make the necessary edits to the file and return the full updated file contents. The file should not be truncated or minimized.
6. If the file does NOT need to be changed, return an empty <edits></edits> tag.
7. Pay attention if we're using server or client components. If we're using client components like Chakra or using React states/effects, make SURE we do "use client" at the top of the file. This includes any client component providers, they also need to have "use client".
    - For example, if we're using a Chakra provider in Next.js, we need to do "use client" at the top of the file.
8. If you need images, use unsplash images.
9. If an image is attached, analyze the image and think about how the image is relevant.
10. If asked to match an image, think about how to copy it EXACTLY almost pixel by pixel. Every attribute of it should be cloned perfectly, including all text, styling, colors unless otherwise stated.
{
            "11. If you are given a reference image with the section, use the assets given. Red bounding boxes are for images, purple bounding boxes are for svgs or videos. Any assets are listed in the <assets> section."
            if is_scraped_site
            else ""
        }

Do NOT change any of the code that is not specifically requested by the instructions. Only change lines of code that need to be changed.

Respond with:
1. Your thought process and reasoning wrapped in <thinking></thinking> tags:
    - Specifically think about purpose the edits need to fulfill and how to best implement them. Also think about if you should replace the entire file, or edit smaller portions.
<thinking>...</thinking>
2. Write down how many sections you need to modify. For edits that are over >30% of the file, you will modify 1 section, which is the whole file. If the edit is <30% of the file, you will modify multiple sections. Think about how many sections you need to modify and how you need to edit them.
3. List of edits you need to make wrapped in <edits></edits> tags. You have two options for the edit response:
    - List of <section_edit><original_code_section> </original_code_section> + <new_code_section> </new_code_section></section_edit> tags: Use this if the code being edited is <30% of the file. We will be using .replace() to edit the file, so this has to be a direct replacement. Consider whitespace, so start the string that needs to be replaced right after the ending bracket of <original_code_section>.
        - Small example:
{MULTI_SECTION_EDIT_EXAMPLE}
    - Singular <full_file_contents><file_contents> </file_contents></full_file_contents> tags: Use this if you are modifying more than 30% of the file. This has to be the entire working file contents.
        - Small example:
{FULL_EDIT_EXAMPLE}
4. A follow up step to perform after this step ONLY if needed. If you don't need to perform a follow up step, do not include this tag at all. Either return an empty string or the <follow_up_step> tag with the required keys "thinking" and "step_to_perform".
<follow_up_step>
<thinking>...</thinking>
<step_to_perform>...</step_to_perform>
</follow_up_step>

OR

Empty string, NO <follow_up_step> tag at all.

Remember to maintain code style consistency, design language and ensure the changes align with the overall purpose. You should NOT use wrap the code in ```, we will be parsing the tags to get the file contents and putting that directly into the file. 
"""
    )
