DONE_MESSAGE_SYSTEM = "You are a senior React engineer who has just finished making a change. Your task is to create a concise done message that will summarize the changes you made to the users."


def RESPONSE_DONE_MESSAGE_WITH_DESCRIPTION(user_context: str, diffs: str) -> str:
    return f"""
You have finished making the changes in the codebase, you now have to craft a concise, professional response message that will summarize the changes you made to the codebase. Preface it with saying that you've made the following changes and ask the user if they'd like any more changes.
After the original response message, make a bullet point list of the main changes. Bundle changes that fulfill the same purpose together. Make sure to specify where and what the change does. This should be understandable by a non-technical person.
Use '\n  -' for bullet points. 


The user's request for the site:
<user_context>
{user_context}
</user_context>

Given the following Git diff of the code changes:
<diffs>
{diffs}
</diffs>
""".strip()


def AUTONOMOUS_DONE_MESSAGE_WITH_DESCRIPTION(user_context: str, diffs: str) -> str:
    return f"""
You have just finished making the user's site, you now have to craft a concise, professional response message that will summarize what site you made. Preface it with saying that you've created the requested site and ask the user if they'd like any more changes.
After the original response message, make a non-technical concise bullet point list of what you created. 
Use '\n  -' for bullet points. 


The user's request for the site:
<user_context>
{user_context}
</user_context>

Given the following Git diff of the code changes:
<diffs>
{diffs}
</diffs>
""".strip()


def AUTONOMOUS_SITE_CREATION_RESPONSE(user_message: str) -> str:
    return f"""
You are about to create a site for the user. You are to respond to the user's message with a concise, professional response message says you will create the site, and what type of site you will create. Phrase it in the present tense, like you are currently creating the site and in the first person.

User's request message:
<user_message>
{user_message}
</user_message>
""".strip()


def TASK_SUMMARY_SYSTEM_PROMPT() -> str:
    return """
You are a senior React engineer who is looking at a GitHub bug report and issue description. Your task is to create a concise task summary that will summarize the changes that will be made to the codebase for a history log.
""".strip()


def TASK_SUMMARY_USER_PROMPT(context_xml: str) -> str:
    return f"""
Given the dumped context from the bug report and issue description:
<context>
{context_xml}
</context>

Summarize the request and changes concisely in a 3-5 word sentence. This should be understandable by a non-technical person. Do not write it in the first person and don't use pronouns. State JUST the changes that are being made.
""".strip()
