import logging
import os
import shutil

import pydantic2zod

logging.basicConfig(level=logging.INFO)
logging.getLogger("pydantic2zod._parser").setLevel(logging.DEBUG)


class Compiler(pydantic2zod.Compiler):
    IGNORE_TYPES = {}
    MODEL_RENAME_RULES = {}

    def _modify_models(self, pydantic_models) -> list:
        for model in pydantic_models:
            for field in model.fields:
                field.name = self._to_camel_case(field.name)
        return pydantic_models

    @staticmethod
    def _to_camel_case(snake_str: str) -> str:
        components = snake_str.split("_")
        return components[0] + "".join(x.title() for x in components[1:])


def _parse_py_file(compiler: Compiler, root: str, file: str) -> tuple[bool, str | None]:
    try:
        if file.endswith(".py") and file != "__init__.py":
            py_file_path: str = os.path.join(root, file)
            ts_file_path: str = os.path.join(
                "ts", os.path.relpath(py_file_path, "py")
            ).replace(".py", ".ts")

            py_module_path: str = py_file_path.replace("/", ".").replace(".py", "")
            ts_src: str = compiler.parse(py_module_path).to_zod()

            with open(ts_file_path, "w") as ts_file:
                ts_file.write(ts_src)
    except Exception as e:
        logging.error(f"Error parsing {py_file_path}: {e}")
        return False, e
    return True, None


def parse_all_py_models():
    ts_dir: str = os.path.join(os.path.dirname(__file__), "ts")
    if os.path.exists(ts_dir):
        shutil.rmtree(ts_dir)
    os.makedirs(ts_dir)

    for root, dirs, files in os.walk("py"):
        for dir in dirs:
            py_dir_path: str = os.path.join(root, dir)
            ts_dir_path: str = os.path.join("ts", os.path.relpath(py_dir_path, "py"))
            os.makedirs(ts_dir_path, exist_ok=True)

    files_processed: int = 0
    compiler: Compiler = Compiler()
    for root, _, files in os.walk("py"):
        for file in files:
            success, error = _parse_py_file(compiler, root, file)
            if success:
                files_processed += 1
            else:
                logging.error(f"Error parsing {file}")
                logging.error(error)

    logging.info(f"Processed {files_processed} files")


parse_all_py_models()
