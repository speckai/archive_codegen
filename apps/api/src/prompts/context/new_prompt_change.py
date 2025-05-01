from typing import TYPE_CHECKING

from src.utils.prompt_utils import format_prompt

if TYPE_CHECKING:
    from src.schemas.core.common import ChatMessage


def PROMPT_WITH_QUESTIONS(
    message: str,
    context: str,
) -> str:
    return format_prompt(f"""
User's request:
<user_request>
{message.strip()}
</user_request>

{
        f'''
Now, consider the questions and answers that the user has provided when asked about the request:
<user_provided_answers>
{context.strip()}
</user_provided_answers>
'''.strip()
        if context
        else ""
    }
""")


def NEW_SITE_START_MESSAGE_SYSTEM() -> str:
    return format_prompt("""
You are a skilled software engineer tasked with interacting with a non-technical user.
""")


def NEW_SITE_START_MESSAGE_USER(
    message: str, relevant_chats: list["ChatMessage"]
) -> str:
    return format_prompt(f"""
First, review the original change request:
<original_request>
{message.strip()}
</original_request>



{
        f'''
Here are the relevant chats to the change request:
<relevant_chats>
{"\n".join([chat.xml for chat in relevant_chats])}
</relevant_chats>
'''.strip()
        if relevant_chats
        else ""
    }

Analyze both the original request and any additional context. Think about how you can combine this information to respond to the user.

Based on your analysis, create a response message to the user. Your response should:
- Be clear and concise.
- Address all aspects of the change mentioned in the original request and additional context.
- Be decisive and specific.
- Not be verbose. This should be around the same length as the original request, just adding any context given.
- Be in the first person.

Remember to tailor your language to be understandable by a non-technical user while still capturing all the necessary details from the developer's perspective.
""")
