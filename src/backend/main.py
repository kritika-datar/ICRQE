import os
import subprocess
from pathlib import Path

import pandas as pd
from chromadb import PersistentClient
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer

from plantuml_generator import PlantUMLGenerator  # Custom module for diagrams
from pydantic import BaseModel
from qa_system import QAProcessor  # Custom module for Q&A using OpenAI API
from repo_parser import RepositoryParser  # Custom module for parsing Java/Python code

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ChromaDB and Model
chroma_client = PersistentClient(path="./.chroma_storage")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")  # Fast and efficient


class RepoInput(BaseModel):
    repo_url: str
    openai_key: str


@app.post("/process_repository/")
def process_repository(input_data: RepoInput):
    repo_url = input_data.repo_url
    openai_key = input_data.openai_key

    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = f"./.repositories/{repo_name}"

    # Clone or update the repository
    if os.path.exists(repo_path):
        subprocess.run(["git", "-C", repo_path, "pull"], check=True)
    else:
        subprocess.run(["git", "clone", repo_url, repo_path], check=True)

    # Parse repository for Java & Python code
    parser = RepositoryParser(repo_path)
    extraction_result = parser.extract_code_structure()

    # Validate repository metadata
    repo_path = Path(f"./repositories/{repo_name}")
    db_path = repo_path / "metadata.duckdb"
    parquet_path = repo_path / "embeddings.parquet"

    if not db_path.exists() or not parquet_path.exists():
        raise HTTPException(
            status_code=500, detail="Failed to extract repository metadata."
        )

    # Read embeddings from Parquet
    df_embeddings = pd.read_parquet(parquet_path)
    if df_embeddings.empty:
        raise HTTPException(status_code=500, detail="No embeddings generated.")

    # Add embeddings to ChromaDB
    collection = chroma_client.get_or_create_collection(repo_name)

    # Ensure unique IDs by appending file path and line number
    df_embeddings["unique_id"] = df_embeddings.apply(
        lambda row: f"{row['id']}_{row['file_path'].replace('/', '_')}_{row['start_line']}",
        axis=1,
    )

    collection.add(
        ids=df_embeddings["unique_id"].astype(str).tolist(),  # Use unique ID
        embeddings=df_embeddings["embedding"].apply(lambda x: x.tolist()).tolist(),
        metadatas=[
            {
                "repo_name": repo_name,
                "file_path": row["file_path"],
                "artifact_type": row["type"],
                "artifact_name": row["name"],
                "docstring": row["docstring"],
                "code": row["code"],
                "id": row["id"]
            } for _, row in df_embeddings.iterrows()
        ]
    )

    # Generate PlantUML diagrams
    diagram_generator = PlantUMLGenerator(repo_path)
    diagrams = diagram_generator.generate_all()

    return {
        "message": "Repository processed successfully",
        "metadata_count": extraction_result["metadata_count"],
        "embeddings_count": extraction_result["embeddings_count"],
        "diagrams": diagrams,
    }


class QuestionInput(BaseModel):
    question: str
    repo_name: str
    openai_key: str


@app.post("/ask_question/")
def ask_question(input_data: QuestionInput):
    repo_name = input_data.repo_name.replace("-", "_")

    # Validate repository metadata
    repo_path = Path(f"./repositories/{repo_name}")
    db_path = repo_path / "metadata.duckdb"
    parquet_path = repo_path / "embeddings.parquet"

    if not db_path.exists() or not parquet_path.exists():
        raise HTTPException(status_code=404, detail="Repository metadata not found.")

    # Load ChromaDB collection
    collection = chroma_client.get_collection(repo_name)
    if not collection:
        raise HTTPException(status_code=404, detail="ChromaDB collection not found.")

    # Initialize QA Processor
    qa_processor = QAProcessor(collection, input_data.openai_key, db_path)
    answer = qa_processor.answer_question(input_data.question)

    return {"answer": answer}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
