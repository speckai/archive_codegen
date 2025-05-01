from src.utils.prompt_utils import format_prompt


def CREATE_FILE_USER_PROMPT(
    purpose: str,
    description: str,
    thinking: str,
    task_context: str,
    all_file_paths: str,
    new_file_directory: str,
    is_scraped_site: bool,
    dependencies_xml: str,
    special_instructions_to_follow: str,
) -> str:
    return format_prompt(
        f"""
The assistant is about to create a new file. The following information is provided:

The purpose of the new file:
<purpose>
{purpose.strip()}
</purpose>

The description of the new file:
<description>
{description.strip()}
</description>

The thought process behind the new file from the planner:
<thinking>
{thinking.strip()}
</thinking>

The context of the current task the user is trying to complete:
<task_context>
{task_context.strip()}
</task_context>

The dependencies and devDependencies from package.json:
{dependencies_xml.strip()}

All file paths in the codebase:
<all_file_paths>
{all_file_paths.strip()}
</all_file_paths>

The path to the directory where the new file needs to be created:
<new_file_directory>
{new_file_directory.strip()}
</new_file_directory>


{
            f'''
Special rules from the end user to follow. If any rules are relevant, you MUST consider them when creating the new file:
{special_instructions_to_follow}
'''.strip()
            if special_instructions_to_follow
            else ""
        }

---

Your task:
1. Analyze the purpose and description of the new file.
2. Review the provided thinking. 
3. Review the initial user request. This is what the user wants to achieve, so tailor your implementation to achieve the goal. \
This may have details or content that you will need to use for your implementation. Implement any and all details that are provided.
4. Think about the best plan to implement the new file. Consider the purpose, description, context and the initial user request to plan out what needs to be implemented.
5. Create the new file with appropriate content based on the given information. The file should not be truncated or minimized, return the full new file contents.
    - If you are writing an MDX file, DO NOT write any React or JavaScript within the file. Especially do NOT embed any React components within the MDX file. Our MDX files break when this happens. 
6. Pay attention if we're using server or client components. If we're using client components like Chakra or using React states/effects, make SURE we do "use client" at the top of the file. This includes any providers, they also need to be wrapped in "use client".
7. If you need images, use unsplash images.
8. If an image is attached, analyze the image and think about how the image is relevant.
9. If asked to match an image, think about how to copy it EXACTLY almost pixel by pixel. Every attribute of it should be cloned perfectly, including all text, styling, colors unless otherwise stated.
{
            "9. If you are given a reference image with the section, use the assets given. Red bounding boxes are for images, purple bounding boxes are for svgs or videos. Any assets are listed in the <assets> section."
            if is_scraped_site
            else ""
        }


Respond with:
1. Your thought process and reasoning wrapped in <thinking></thinking> tags.
2. The path to the new file wrapped in <new_file_path></new_file_path> tags. This should start with the new_file_directory and end with the file name you've chosen. \
Use any context given to you to determine the best file name. 
3. The entire contents of the new file wrapped in <file_contents></file_contents> tags. You should not cut off the file before it's supposed to end. \
    - You should NOT use wrap the code in ```, we will be parsing the tags to get the file contents and putting that directly into the file.
    - For example, do NOT wrap the file contents in ```tsx```, just return the file contents.
4. A follow up step to perform after this step ONLY if needed. If you don't need to perform a follow up step, do not include this tag at all. Either return an empty string or the <follow_up_step> tag with the required keys "thinking" and "step_to_perform".
<follow_up_step>
<thinking>...</thinking>
<step_to_perform>...</step_to_perform>
</follow_up_step>

OR

Empty string, NO <follow_up_step> tag at all.

Ensure that the new file adheres to the project's coding standards, design language and integrates well with the existing codebase.
"""
    )
