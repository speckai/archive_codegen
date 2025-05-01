import os

from dotenv import load_dotenv


class EnvConfig:
    def __init__(self):
        load_dotenv(".env", override=True)

    def __call__(self, env_var_name: str, default: any = None) -> any:
        val = os.environ.get(env_var_name, default)
        if val is not None:
            val = val.replace("\\n", "\n")
        return val


config: EnvConfig = EnvConfig()


DEV: bool = config("DEV") == "True"
GITHUB_APP_SMEE_URL: str = config("GITHUB_APP_SMEE_URL")
GITHUB_CLIENT_ID: str = config("GITHUB_CLIENT_ID")
GITHUB_PRIVATE_KEY: str = config("GITHUB_PRIVATE_KEY")


MONGODB_URI: str = config("MONGODB_URI")
