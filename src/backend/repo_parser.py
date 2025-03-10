import ast
import re
from pathlib import Path

import pandas as pd

SUPPORTED_EXTENSIONS = {
    ".py",
    ".txt",
    ".yaml",
    ".yml",
    ".sh",
    ".md",
    ".toml",
    ".java",
    ".js",
    ".cpp",
    ".hpp",
    ".h",
    ".c",
    ".cs",
}


def _parse_python_file(file_path, embedding_data):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
        class_stack = []

        found_code = False

        file_hash = hash(str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                found_code = True
                class_stack.append(node.name)
                embedding_data.append(
                    {
                        "id": f"{node.name}_{file_path.stem}_{node.lineno}_{file_hash}",
                        "name": node.name,
                        "type": "class",
                        "file_path": str(file_path),
                        "start_line": node.lineno,
                        "end_line": getattr(node, "end_lineno", None),
                        "code": ast.unparse(node),
                        "parent": None,
                        "docstring": ast.get_docstring(node) or "",
                    }
                )

            elif isinstance(node, ast.FunctionDef):
                found_code = True
                parent = class_stack[-1] if class_stack else None
                embedding_data.append(
                    {
                        "id": f"{node.name}_{file_path.stem}_{node.lineno}_{file_hash}",
                        "name": node.name,
                        "type": "method" if parent else "function",
                        "file_path": str(file_path),
                        "start_line": node.lineno,
                        "end_line": getattr(node, "end_lineno", None),
                        "code": ast.unparse(node),
                        "parent": parent,
                        "docstring": ast.get_docstring(node) or "",
                    }
                )
    except Exception as e:
        print(f"Error parsing Python file {file_path}: {e}")


def _parse_other_languages(file_path, embedding_data):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        found_code = False

        file_hash = hash(str(file_path))

        class_pattern = re.compile(r"class\s+(\w+)\s*[{|:]")
        function_pattern = re.compile(
            r"(public|private|protected)?\s*\w+[<>]*\s+(\w+)\s*\(.*\)\s*[{|;]"
        )

        for i, line in enumerate(code):
            class_match = class_pattern.search(line)
            function_match = function_pattern.search(line)

            if class_match:
                found_code = True
                name = class_match.group(1)
                embedding_data.append(
                    {
                        "id": f"{name}_{file_path.stem}_{i + 1}_{file_hash}",
                        "name": name,
                        "type": "class",
                        "file_path": str(file_path),
                        "start_line": i + 1,
                        "end_line": None,
                        "code": None,
                        "parent": None,
                        "docstring": "",
                    }
                )

            if function_match:
                found_code = True
                name = function_match.group(2)
                embedding_data.append(
                    {
                        "id": f"{name}_{file_path.stem}_{i + 1}_{file_hash}",
                        "name": name,
                        "type": "function",
                        "file_path": str(file_path),
                        "start_line": i + 1,
                        "end_line": None,
                        "code": None,
                        "parent": None,
                        "docstring": "",
                    }
                )
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")


class RepositoryParser:
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.parquet_path = self.repo_path / "embeddings.parquet"

    def extract_code_structure(self, changed_files=None):
        embedding_data = []

        if changed_files:
            files_to_process = [
                self.repo_path / file for file in changed_files if file.endswith(".py")
            ]
        else:
            files_to_process = list(self.repo_path.rglob("*.py"))

        for file_path in files_to_process:
            ext = file_path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            if ext == ".py":
                _parse_python_file(file_path, embedding_data)
            # else:
            #     _parse_other_languages(file_path, embedding_data)

        if embedding_data:
            df_embeddings = pd.DataFrame(embedding_data)
            df_embeddings.to_parquet(self.parquet_path, index=False)
        else:
            df_embeddings = pd.DataFrame()

        return {"embedding_metadata": df_embeddings}
