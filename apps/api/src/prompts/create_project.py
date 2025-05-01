def INITIAL_SITE_CREATION_PROMPT(requested_changes: str, has_images: bool):
    return f"""
The user has a template repository that they want to use to create a new site. 

The user has requested the following changes to the site:
<user_request>
{requested_changes}
</user_request>

Also make the README.md file match the user's request with an overview, installation instructions, and other relevant information.

If the user has only requested a single page or component, make the site in the / page. 
If making a multi-page app, by default if no other instructions are given, replace the root "/" page at `app/page.tsx` with a page of the user's request. The "Setting up your project..." component in `app/page.tsx` should NOT exist anymore after your edits. 
    - Example: If the user requests a multi-page app but doesn't specify what to do with the homepage, make the root page a landing page of the user's request.
    - Example: If the user requests a spotify clone, make the root page the spotify UI clone
Create any and all UI components and pages that are requested, and make it extremely good looking. If data sources or specific data is not given, create and use dummy data.
{"" if has_images else "If the user attaches any images and asks to use them as reference, make the site match the image EXACTLY and pixel perfect."}
You should change the site entirely to match the user's request and make them that site. 
If the user has not requested a specific style, make it fancy and stylish with animations. Ensure the site is repsonsive and looks good on both desktop and mobile.
Use placeholder images and logos where possible. Use unsplash for this.
""".strip()


def CREATE_PROJECT_CLASSIFICATION_PROMPT(message: str):
    return f"""
<message>
{message}
</message>

Based on the user's message, classify the user's request into one of the following categories:
- Start project
- Scrape site then start project.

If the user's message asks to clone a site or take inspiration from a site, then return the URL of the site.
""".strip()
