import os

from dotenv import load_dotenv


class EnvConfig:
    def __init__(self):
        load_dotenv(
            ".env", override=True
        )  # Note: doesn't overwrite existing env vars in your shell

    def __call__(self, env_var_name: str, default: any = None) -> any:
        val = os.environ.get(env_var_name, default)
        if val is not None:
            val = val.replace("\\n", "\n")
        return val


config: EnvConfig = EnvConfig()

ANTHROPIC_API_KEY: str | None = config("ANTHROPIC_API_KEY")
OPENAI_API_KEY: str | None = config("OPENAI_API_KEY")
GEMINI_API_KEY: str | None = config("GEMINI_API_KEY")
GROQ_API_KEY: str | None = config("GROQ_API_KEY")
HELICONE_API_KEY: str | None = config("HELICONE_API_KEY")

AUTH_URL: str = config("AUTH_URL")
AUTH_CLIENT_ID: str = config("AUTH_CLIENT_ID")
AUTH_CLIENT_SECRET: str = config("AUTH_CLIENT_SECRET")

DEV: bool = config("DEV") == "True"

SUPABASE_JWT_SECRET: str = config("SUPABASE_JWT_SECRET")
SUPABASE_URL: str = config("SUPABASE_URL")
SUPABASE_KEY: str = config("SUPABASE_KEY")  # Service role key

RESEND_API_KEY: str = config("RESEND_API_KEY")
STRIPE_API_KEY: str = config("STRIPE_API_KEY")

MONGODB_URI: str = config("MONGODB_URI")

AWS_ACCESS_KEY_ID: str = config("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY: str = config("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION: str = config("AWS_DEFAULT_REGION")

AZURE_OPENAI_API_KEY: str = config("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT: str = config("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT: str = config("AZURE_OPENAI_DEPLOYMENT")
AZURE_API_VERSION: str = config("AZURE_API_VERSION")

BETTERSTACK_SOURCE_TOKEN: str = config("BETTERSTACK_SOURCE_TOKEN")

QDRANT_URL: str = config("QDRANT_URL")
QDRANT_API_KEY: str = config("QDRANT_API_KEY")

MORPHCLOUD_API_KEY: str = config("MORPHCLOUD_API_KEY")

GITHUB_REDIRECT_URI: str = config("GITHUB_REDIRECT_URI")
GITHUB_CLIENT_ID: str = config("GITHUB_CLIENT_ID")
GITHUB_APP_ID: str = config("GITHUB_APP_ID")
GITHUB_CLIENT_SECRET: str = config("GITHUB_CLIENT_SECRET")
GITHUB_PRIVATE_KEY: str = config("GITHUB_PRIVATE_KEY")

POSTHOG_KEY: str = config("POSTHOG_KEY")
POSTHOG_HOST: str = config("POSTHOG_HOST")

DISCORD_WEBHOOK_URL: str = config("DISCORD_WEBHOOK_URL")

IS_DOCKER: bool = config("IS_DOCKER") == "true"
USING_NGINX: bool = config("USING_NGINX") == "true"


"""
Initialize the logger here. Do not move.
"""

from src.utils.debug.session_replay import SessionRecorder

session_recorder: SessionRecorder = SessionRecorder()
