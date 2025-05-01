from src.agents.implementer.tools.agent.tool import AgentTool
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.tools.bash.tool import BashTool
from src.agents.implementer.tools.file_edit.tool import FileEditTool
from src.agents.implementer.tools.file_read.tool import FileReadTool
from src.agents.implementer.tools.file_write.tool import FileWriteTool
from src.agents.implementer.tools.glob.tool import GlobTool
from src.agents.implementer.tools.grep.tool import GrepTool
from src.agents.implementer.tools.ls.tool import LSTool
from src.agents.implementer.tools.think.tool import ThinkTool
from src.agents.implementer.tools.validate.tool import ValidateTool


def get_all_tools() -> list[BaseTool]:
    return [
        AgentTool(),
        FileEditTool(),
        FileReadTool(),
        FileWriteTool(),
        GrepTool(),
        GlobTool(),
        LSTool(),
        ThinkTool(),
        BashTool(),
        ValidateTool(),
    ]


def get_read_only_tools() -> list[BaseTool]:
    return [tool for tool in get_all_tools() if tool.is_read_only]


def get_fs_exploration_tools() -> list[BaseTool]:
    return [
        BashTool(),
        LSTool(),
        GrepTool(),
        GlobTool(),
        FileReadTool(),
        FileWriteTool(),
    ]


def get_agent_tools(read_only: bool) -> list[BaseTool]:
    return get_read_only_tools() if read_only else get_all_tools()
