DATA_GEN_PROMPT_SYSTEM = """
You are a senior React engineer who's creating a ticket for a new hire to implement a change to the codebase.
""".strip()

DATA_GEN_PROMPT_USER = """
Your task is to take the following user requested change and data about the file the change will be implemented in, then generate a purpose and description for the change.

You are given the following:

Overall request - The user requested change that needs to be implemented:
<overall_request>
    {change_message}
</overall_request>

User requested change - The actual change that the user requested to be made:
<user_requested_change>
    {query_message}
</user_requested_change>

File path - The path to the file that the user requested to be changed:
<file_path>
    {file_path}
</file_path>

Specific selected component code - The code of the component that the user requested to be changed:
<selected_component_code>
    {selected_component_code}
</selected_component_code>

File contents:

File contents - The contents of the file that the component is in:
<file_contents>
    {file_content}
</file_contents>

Your task is to generate a purpose and description for the changes to be made to this component. The tone and exact verbiage should be the same as the user requested change. 
The purpose should be a short description of the change to be made, no longer than 1 sentence. This should be a high level description of the change. This should not stray from the original request.
The description should be a detailed description of the change to be made. The exact verbiage of the change should be included. No longer than 3 sentences.
""".strip()
