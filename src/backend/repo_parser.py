import ast
from pathlib import Path

import duckdb
import pandas as pd
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")  # Small, fast model


class RepositoryParser:
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.db_path = self.repo_path / "metadata.duckdb"
        self.parquet_path = self.repo_path / "embeddings.parquet"
        self.chroma_client = PersistentClient(path="./chroma_storage")

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
                type TEXT,
                name TEXT,
                file_path TEXT,
                parent TEXT,
                start_line INTEGER,
                end_line INTEGER
            )
        """
        )

    def insert_metadata(self, metadata):
        # Ensure all required columns exist
        required_columns = [
            "file_path",
            "language",
            "type",
            "name",
            "parent",
            "start_line",
            "end_line",
            "docstring",
            "code"
        ]
        for col in required_columns:
            if col not in metadata.columns:
                metadata[col] = None  # Fill missing columns with None

        # Convert DataFrame to a list of tuples
        data = list(metadata.itertuples(index=False, name=None))

        # Insert into DuckDB
        self.conn.executemany(
            """
            INSERT INTO code_metadata (file_path, language, type, name, parent, start_line, end_line) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            data,
        )

    def fetch_metadata(self):
        """Fetch all stored metadata."""
        return self.conn.execute("SELECT * FROM code_metadata").fetchall()

    # def extract_code_structure(self):
    #     """Parses Java & Python files, stores metadata, and saves embeddings."""
    #     code_data = []
    #     embedding_data = []
    #
    #     for file_path in self.repo_path.rglob("*.py"):
    #         self._parse_python_file(file_path, code_data, embedding_data)
    #
    #     # Store metadata in DuckDB
    #     df_metadata = pd.DataFrame(code_data)
    #     if not df_metadata.empty:
    #         self.insert_metadata(df_metadata)
    #
    #     # Store embeddings in Parquet
    #     df_embeddings = pd.DataFrame(embedding_data)
    #     if not df_embeddings.empty:
    #         df_embeddings.to_parquet(self.parquet_path, index=False)
    #
    #     return {
    #         "metadata_count": len(code_data),
    #         "embeddings_count": len(embedding_data),
    #     }

    def extract_code_structure(self):
        code_data = []
        embedding_data = []
        for file_path in self.repo_path.rglob("*.py"):
            self._parse_python_file(file_path, code_data, embedding_data)
        df_metadata = pd.DataFrame(code_data)
        # if not df_metadata.empty:
        #     self.conn.executemany(
        #         "INSERT INTO code_metadata (type, name, file_path, parent, start_line, end_line, docstring, code) "
        #         "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        #         df_metadata.itertuples(index=False, name=None)
        #     )
        df_embeddings = pd.DataFrame(embedding_data)
        if not df_embeddings.empty:
            df_embeddings.to_parquet(self.parquet_path, index=False)
        return {"metadata_count": len(code_data), "embeddings_count": len(embedding_data)}

    # def _parse_python_file(self, file_path, code_data, embedding_data):
    #     """Extracts structure from Python files: classes, functions, and methods."""
    #     try:
    #         with open(file_path, "r", encoding="utf-8") as f:
    #             code = f.read()
    #
    #         tree = ast.parse(code)  # Parse Python code into an AST
    #
    #         class_stack = []  # To track class hierarchy (for methods)
    #
    #         for node in ast.walk(tree):
    #             if isinstance(node, ast.ClassDef):  # Class Definition
    #                 class_stack.append(node.name)  # Track class name
    #
    #                 code_data.append(
    #                     {
    #                         "type": "class",
    #                         "name": node.name,
    #                         "file_path": str(file_path),
    #                         "parent": None,  # No parent for top-level classes
    #                         "start_line": node.lineno,
    #                         "end_line": getattr(node, "end_lineno", None),
    #                     }
    #                 )
    #
    #                 embedding = self._generate_embedding(
    #                     ast.get_source_segment(code, node)
    #                 )
    #                 embedding_data.append(
    #                     {
    #                         "id": f"{node.name}",
    #                         "file_path": str(file_path),
    #                         "start_line": node.lineno,
    #                         "embedding": embedding,
    #                     }
    #                 )
    #
    #             elif isinstance(node, ast.FunctionDef):  # Function Definition
    #                 parent = (
    #                     class_stack[-1] if class_stack else None
    #                 )  # Check if inside a class
    #
    #                 code_data.append(
    #                     {
    #                         "type": "method" if parent else "function",
    #                         "name": node.name,
    #                         "file_path": str(file_path),
    #                         "parent": parent,
    #                         "start_line": node.lineno,
    #                         "end_line": getattr(node, "end_lineno", None),
    #                     }
    #                 )
    #
    #                 embedding = self._generate_embedding(
    #                     ast.get_source_segment(code, node)
    #                 )
    #                 embedding_data.append(
    #                     {
    #                         "id": f"{node.name}_{file_path.name}",
    #                         "file_path": str(file_path),
    #                         "embedding": embedding,
    #                         "start_line": node.lineno
    #                     }
    #                 )
    #
    #     except Exception as e:
    #         print(f"Error parsing Python file {file_path}: {e}")
    #
    # def _generate_embedding(self, code_snippet):
    #     if not code_snippet:
    #         return [0.0] * 384  # Adjust for model size
    #     return model.encode(code_snippet).tolist()

    def _parse_python_file(self, file_path, code_data, embedding_data):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            tree = ast.parse(code)
            class_stack = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_stack.append(node.name)
                    code_data.append({
                        "type": "class", "name": node.name,
                        "file_path": str(file_path), "parent": None,
                        "start_line": node.lineno, "end_line": getattr(node, "end_lineno", None),
                        "docstring": ast.get_docstring(node) or "",
                        "code": ast.unparse(node)
                    })
                    embedding_data.append({
                        "id": node.name, "file_path": str(file_path),
                        "start_line": node.lineno,
                        "embedding": self._generate_embedding(ast.get_source_segment(code, node)),
                        "type": "class", "name": node.name,
                        "parent": None,
                        "end_line": getattr(node, "end_lineno", None),
                        "docstring": ast.get_docstring(node) or "",
                        "code": ast.unparse(node)
                    })
                elif isinstance(node, ast.FunctionDef):
                    parent = class_stack[-1] if class_stack else None
                    code_data.append({
                        "type": "method" if parent else "function", "name": node.name,
                        "file_path": str(file_path), "parent": parent,
                        "start_line": node.lineno, "end_line": getattr(node, "end_lineno", None),
                        "docstring": ast.get_docstring(node) or "",
                        "code": ast.unparse(node)
                    })
                    embedding_data.append({
                        "id": f"{node.name}_{file_path.name}", "file_path": str(file_path),
                        "start_line": node.lineno,
                        "embedding": self._generate_embedding(ast.get_source_segment(code, node)),
                        "type": "method" if parent else "function", "name": node.name,
                        "parent": None,
                        "end_line": getattr(node, "end_lineno", None),
                        "docstring": ast.get_docstring(node) or "",
                        "code": ast.unparse(node)
                    })
        except Exception as e:
            print(f"Error parsing Python file {file_path}: {e}")

    def _generate_embedding(self, code_snippet):
        return embedding_model.encode(code_snippet).tolist() if code_snippet else [0.0] * 384

