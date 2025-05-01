from src.utils.prompt_utils import format_prompt


def SUMMARIZE_RECORDING_SYSTEM_PROMPT() -> str:
    return "You are a Senior QA Engineer who translates user bug report data to actionable bug reports for Product Managers to file."


def SUMMARIZE_RECORDING_USER_PROMPT(issue_annotation: str, recorded_events: str) -> str:
    return format_prompt(
        f"""
<task_instructions>
The user has used a tool to record their events to reproduce the issue they described. \
Your goal is to provide a list of reproduction steps, along with the expected success state for the developer to validate against.

Each action the user recorded be 1:1 mapped to a reproduction step, and the number of reproduction steps should be EXACTLY the \
same as the number of recorded steps the user. These should be specific enough for a non-technical user to perform, \
but provide enough details that there is no confusion on what the action is. Use the screenshots to confirm the actions. \
A rubric is below:
- Conciseness: Is the reproduction step as concise as possible while getting the point across?
- Uniqueness of elements: If we're clicking on an element, are there any other elements on the screen that this can be confused with?
- Specificity & Clarity: Is the step specific enough? Is the location of the element (if applicable) described and clear? Is the action completely unambiguous? \
Are the instructions clear?

You will be given the following:
- User provided recording annotation: An annotation of the recording by the user
- Recorded events: A chronologically ordered list of events. You'll get the full dump of information
- Screenshots: Screenshots you can use as context for helping create the steps. Any red boxes signal where exactly the user clicked.
</task_instructions>

<response_instructions>
You are to return a JSON with the following keys:
- thinking: Use this space to think very hard and comprehensively against every piece of context you're given. \
Relate the recorded events against the screenshots, analyze exactly what the user was trying to accomplish, and verify each \
step before you start drafting steps. For each drafted step, you should validate your step against the rubric described in the \
task instructions. Take as long as needed, you should create arguments and counterarguments against every analysis you perform. 
- reproduction_steps: A list of steps in order. For each step, you should provide a step description and the number of seconds \
of delay the step has. 
- expected_success_state: The exact ending state that the developer should expect after they validate the state. \
This is what will be tested when the developer validates their change. 
- current_incorrect_state: The exact ending state that the developer is currently experiencing.
</response_instructions>

User provided recording annotation:
<recording_annotation>
{issue_annotation}
</recording_annotation>

Recorded events:
<recorded_events>
{recorded_events}
</recorded_events>

Here are all the images attributed to the recording:
"""
    )
