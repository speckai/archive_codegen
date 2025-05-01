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
