import os

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/client_scripts")

CURRENT_DIR = os.path.dirname(__file__)
SCRIPTS_PATH = os.path.join(CURRENT_DIR, "scripts")
COMPONENT_SCRIPT_PATH = os.path.join(
    SCRIPTS_PATH, "component_hook.js"
)  # Speck hook that runs on top of react devtools
DEVTOOL_SCRIPT_PATH = os.path.join(
    SCRIPTS_PATH, "react_devtools.js"
)  # React devtools script

RECORDER_MAIN_PATH = os.path.join(SCRIPTS_PATH, "recorder_main.js")
REPLAYER_PATH = os.path.join(SCRIPTS_PATH, "replayer.js")
UTILS_PATH = os.path.join(SCRIPTS_PATH, "utils.js")


@router.get("/devtools.js", response_class=PlainTextResponse)
async def get_speck_hook_script():
    with open(COMPONENT_SCRIPT_PATH, "r") as npm_file:
        npm_content = npm_file.read()

    with open(DEVTOOL_SCRIPT_PATH, "r") as devtool_file:
        devtool_content = devtool_file.read()

    with open(UTILS_PATH, "r") as utils_file:
        utils_content = utils_file.read()

    return npm_content + "\n" + devtool_content + "\n" + utils_content


@router.get("/recorder.js", response_class=PlainTextResponse)
async def get_recorder_scripts():
    script_paths: list[str] = [RECORDER_MAIN_PATH, REPLAYER_PATH]
    script_contents: list[str] = []

    for path in script_paths:
        with open(path, "r") as file:
            script_contents.append(file.read())

    return "\n".join(script_contents)
