import ast
from pathlib import Path

import duckdb
import pandas as pd
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")  # Small, fast model


def _generate_embedding(code_snippet):
    return (
        embedding_model.encode(code_snippet).tolist() if code_snippet else [0.0] * 384
    )


def _parse_python_file(file_path, code_data, embedding_data):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
        class_stack = []  # Track class nesting

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_stack.append(node.name)
                code_data.append(
                    {
                        "name": node.name,
                        "code": ast.unparse(node),
                        "parent": None,
                        "docstring": ast.get_docstring(node) or "",
                        "start_line": node.lineno,
                        "end_line": getattr(node, "end_lineno", None),
                    }
                )
                embedding_data.append(
                    {
                        "id": f"{node.name}_{file_path.stem}_{node.lineno}",
                        "name": node.name,
                        "type": "class",
                        "file_path": str(file_path),
                        "start_line": node.lineno,
                        "end_line": getattr(node, "end_lineno", None),
                        "code": ast.unparse(node),
                    }
                )

            elif isinstance(node, ast.FunctionDef):
                parent = class_stack[-1] if class_stack else None
                code_data.append(
                    {
                        "name": node.name,
                        "code": ast.unparse(node),
                        "parent": parent,
                        "docstring": ast.get_docstring(node) or "",
                        "start_line": node.lineno,
                        "end_line": getattr(node, "end_lineno", None),
                    }
                )
                embedding_data.append(
                    {
                        "id": f"{node.name}_{file_path.stem}_{node.lineno}",
                        "name": node.name,
                        "type": "method" if parent else "function",
                        "file_path": str(file_path),
                        "start_line": node.lineno,
                        "end_line": getattr(node, "end_lineno", None),
                        "code": ast.unparse(node),
                    }
                )

    except Exception as e:
        print(f"Error parsing Python file {file_path}: {e}")


class RepositoryParser:
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.db_path = self.repo_path / "metadata.duckdb"
        self.parquet_path = self.repo_path / "embeddings.parquet"

        # Initialize DuckDB connection
        self.conn = duckdb.connect(str(self.db_path))

        # Ensure tables exist
        self._init_db()

    def _init_db(self):
        """Initialize the DuckDB database schema."""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS code_metadata (
                id INTEGER,  -- No auto-increment
                name TEXT,
                code TEXT,
                parent TEXT,
                docstring TEXT,
                start_line INTEGER,
                end_line INTEGER
            )
        """
        )

    def insert_metadata(self, metadata):
        # Ensure all required columns exist
        required_columns = [
            "name",
            "code",
            "parent",
            "docstring",
            "start_line",
            "end_line",
        ]
        for col in required_columns:
            if col not in metadata.columns:
                metadata[col] = None  # Fill missing columns with None

        # Convert DataFrame to a list of tuples
        data = list(metadata.itertuples(index=False, name=None))

        # Insert into DuckDB
        self.conn.executemany(
            """
            INSERT INTO code_metadata (name, code, parent, docstring, start_line, end_line) VALUES (?, ?, ?, ?, ?, ?)
            """,
            data,
        )

    def fetch_metadata(self):
        """Fetch all stored metadata."""
        return self.conn.execute("SELECT * FROM code_metadata").fetchall()

    def extract_code_structure(self):
        code_data = []
        embedding_data = []
        for file_path in self.repo_path.rglob("*.py"):
            _parse_python_file(file_path, code_data, embedding_data)
        df_metadata = pd.DataFrame(code_data)
        if not df_metadata.empty:
            self.insert_metadata(df_metadata)
        df_embeddings = pd.DataFrame(embedding_data)
        if not df_embeddings.empty:
            df_embeddings.to_parquet(self.parquet_path, index=False)
        return {"code_metadata": df_metadata, "embedding_metadata": df_embeddings}
