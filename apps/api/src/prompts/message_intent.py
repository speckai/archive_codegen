from typing import TYPE_CHECKING

from src.utils.prompt_utils import format_prompt

if TYPE_CHECKING:
    from src.agents.utils.task.task import ChatMessage


def MESSAGE_INTENT_SYSTEM_PROMPT() -> str:
    return """
You are an message intent classifier designed to route requests to the right version of Speck, a frontend engineer. Use the user's message and previous context.
""".strip()


def MESSAGE_INTENT_USER_PROMPT(
    user_message: str,
    message_history: list["ChatMessage"],
) -> str:
    return format_prompt(f"""
Your goal is to classify the user's message so that we can route it to the right handler. 
You are also to analyze the chat history and determine which (if any) messages are relevant to the task at hand so that we can use them as context when handling the user's message.

User message: The most recent message the user sent. You should classify this message.
<user_message>
{user_message}
<user_message>

Chat history: Previous messages in this chat. 
<chat_history>
{"\n".join(message.indexed_xml(idx) for idx, message in enumerate(message_history))}
<chat_history>

You can classify the message as one of the following:
TASK: The user wants to create a new task to edit the site. This is when the user has a specific change they want to make to the project.
QUESTION: The user has a question about the codebase of the site, or the site directly.
GIT: The user wants to push/commit changes to the git repo. Key words for this are "save", "commit", "push", "git", etc.
VALIDATE_BUILD: The user wants to validate the build of the site.
UNDEFINED: The message is not one of the above.

Keep context of conversations in mind. For example, if the user asks a question about something, then asks a follow up question related to the first question, you should return the indexes of both messages since they are both relevant.
\
You should also return the exact message indexes for any pertinent chat history that is DIRECTLY relevant to the task, so the router can use that context.

For example, if the user performs a task, then performs a task that is related to the first task, you should also return the index of the first task since it is relevant to the second task.
""")
