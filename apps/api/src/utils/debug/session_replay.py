import json  # import dill as pickle
import os
import threading
import traceback
from functools import wraps
from typing import TYPE_CHECKING, Any, Optional

from loguru import logger
from pydantic import BaseModel
from src.config import DEV

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


def remove_self_from_args(args, func):
    saved_args = tuple(args)
    # Check if the first argument is self by checking if the first argument has the function name as an attribute
    if saved_args and hasattr(
        saved_args[0], func.__name__
    ):  # and callable(getattr(saved_args[0], func.__name__)):
        saved_args = saved_args[1:]
    return saved_args


def get_first_available_path(path: str = "{number}"):
    i = 0
    formatted_path = path.format(number=i)
    while os.path.exists(formatted_path):
        i += 1
        formatted_path = path.format(number=i)
    return formatted_path


class SessionReplay:
    def __init__(self, task: "Task"):
        self.task = task


class CachedMethodCall(BaseModel):
    method_name: str
    inputs: dict
    output: Optional[Any] = None
    error: Optional[str] = None
    error_stacktrace: Optional[str] = None

    @classmethod
    def from_func_call(
        cls,
        func: callable,
        inputs: dict,
        output: Any = None,
        error: str = None,
        error_stacktrace: str = None,
    ):
        return cls(
            method_name=func.__name__,
            inputs=inputs,
            output=output,
            error=error,
            error_stacktrace=error_stacktrace,
        )

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(self.model_dump_json()) + "\n")


class SessionRecorder:
    def __init__(self, save_path: str = "replays/{user}/{session}.json"):
        self.save_path_template = save_path
        self.session_storage = threading.local()

    @property
    def current_replay(self) -> SessionReplay:
        if not hasattr(self.session_storage, "replay"):
            raise Exception("Session replay not started")
        return self.session_storage.replay

    @property
    def current_task(self) -> "Task":
        if not hasattr(self.session_storage, "task"):
            return None
        return self.session_storage.task

    @property
    def current_task_path(self) -> str:
        if not hasattr(self.session_storage, "current_task_path"):
            raise Exception("Task not started")
        return self.session_storage.current_task_path

    def start(self, task: "Task"):
        path = self.save_path_template.format(user=task.user.name, session=task.user.id)
        self.session_storage.task = task
        self.session_storage.replay = SessionReplay(task)
        self.session_storage.save_path = path
        self.session_storage.current_task_path = get_first_available_path(
            f"records/{task.user.name}/{{number}}"
        )
        logger.trace(f"Started session recorder for {path}")
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.trace("Exiting session recorder", exc_type, exc_val, exc_tb)
        logger.trace(self.session_storage.save_path)
        # with open(save_path, 'wb') as f:
        #     pickle.dump(self.current_replay.records, f)

    """
    Section: record decorator
    """

    def _save_method_call(
        self, func: callable, saved_args: Any, output: Any, error: Optional[str] = None
    ):
        method_call = CachedMethodCall.from_func_call(
            func,
            saved_args,
            output=output,
            error=error,
            error_stacktrace=str(traceback.format_exc()) if error else None,
        )
        path = get_first_available_path(
            f"{self.current_task_path}/{func.__module__}/{func.__qualname__}/run{{number}}.json"
        )
        if DEV:
            method_call.save(path=path)

    @staticmethod
    def _get_inputs(func, args, kwargs) -> dict:
        saved_args = remove_self_from_args(args, func)
        inputs = {"args": saved_args, "kwargs": kwargs}
        return inputs

    def record(self, name: str = None, is_async: bool = False):
        def decorator(func: callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if self.current_task is None:
                    return await func(*args, **kwargs)

                saved_args = SessionRecorder._get_inputs(func, args, kwargs)
                try:
                    output = await func(*args, **kwargs)
                    self._save_method_call(func, saved_args, output)
                except Exception as e:
                    self._save_method_call(func, saved_args, None, str(e))
                    logger.warning(e)
                    logger.warning(traceback.format_exc())
                    raise e
                return output

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if self.current_task is None:
                    return func(*args, **kwargs)

                saved_args = SessionRecorder._get_inputs(func, args, kwargs)
                try:
                    output = func(*args, **kwargs)
                    self._save_method_call(func, saved_args, output)
                except Exception as e:
                    self._save_method_call(func, saved_args, None, str(e))
                    logger.warning(e)
                    logger.warning(traceback.format_exc())
                    raise e
                return output

            return async_wrapper if is_async else sync_wrapper

        return decorator

    def async_record(self, test: str = None):
        return self.record(test, is_async=True)


# Test the functionality in the main block
if __name__ == "__main__":
    test_session = Task(
        debug=True,
        user=None,
        created_repo_id=None,
    )
    session_recorder = SessionRecorder()

    @session_recorder.async_record()
    async def merge(content, original, new):
        return content.replace(original, new)

    import asyncio

    with session_recorder.start(test_session):
        res = asyncio.run(merge("Hello, world!", "world", "earth"))
        logger.info(res)
