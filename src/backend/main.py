import os
import subprocess
from pathlib import Path

import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from plantuml_generator import PlantUMLGenerator  # Custom module for diagrams
from pydantic import BaseModel
from qa_system import QAProcessor  # Custom module for Q&A using OpenAI API
from repo_parser import RepositoryParser  # Custom module for parsing Java/Python code
from sentence_transformers import SentenceTransformer

# Initialize ChromaDB and Model
chroma_client = chromadb.PersistentClient(path="./.chroma_db",
settings=chromadb.Settings(
        is_persistent=True,  # Ensure persistence
        persist_directory="./chroma_storage",  # Folder where Parquet files will be stored
        anonymized_telemetry=False
    )
                                          )
embedding_function = embedding_functions.DefaultEmbeddingFunction()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Serve the diagrams directory
app.mount("/diagrams", StaticFiles(directory="/Users/kritikadatar/PycharmProjects/ICRQE/src/backend/.repositories/ICRQE/diagrams"), name="diagrams")

class RepoInput(BaseModel):
    repo_url: str
    openai_key: str

class QuestionInput(BaseModel):
    question: str
    repo_name: str
    openai_key: str


def get_local_commit(repo_path):
    """Get the latest local commit hash."""
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_path)
            .strip()
            .decode()
        )
    except subprocess.CalledProcessError:
        return None


def get_remote_commit(repo_path):
    """Get the latest remote commit hash."""
    try:
        subprocess.run(["git", "fetch", "origin"], cwd=repo_path, check=True)
        return (
            subprocess.check_output(["git", "rev-parse", f"origin/main"], cwd=repo_path)
            .strip()
            .decode()
        )
    except subprocess.CalledProcessError:
        return None


@app.post("/process_repository/")
def process_repository(input_data: RepoInput):
    repo_url = input_data.repo_url

    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = f"./.repositories/{repo_name}"

    # Clone or update the repository
    if os.path.isdir(repo_path) and os.path.isdir(os.path.join(repo_path, ".git")):
        print("Repository exists. Checking for updates...")
        local_commit = get_local_commit(repo_path)
        remote_commit = get_remote_commit(repo_path)

        if local_commit and remote_commit and local_commit != remote_commit:
            print("New changes detected. Pulling latest updates...")
            subprocess.run(["git", "-C", repo_path, "pull"], check=True)
        else:
            print("Already up to date.")
    else:
        subprocess.run(["git", "clone", repo_url, repo_path], check=True)

    # Parse repository for Java & Python code
    parser = RepositoryParser(repo_path)
    extraction_result = parser.extract_code_structure()

    # Validate repository metadata
    repo_path = Path(f"./.repositories/{repo_name}")
    db_path = repo_path / "metadata.duckdb"
    parquet_path = repo_path / "embeddings.parquet"

    if not db_path.exists() or not parquet_path.exists():
        raise HTTPException(
            status_code=500, detail="Failed to extract repository metadata."
        )

    # # Read embeddings from Parquet
    df_embeddings = pd.read_parquet(parquet_path)
    if df_embeddings.empty:
        raise HTTPException(status_code=500, detail="No embeddings generated.")

    # Add embeddings to ChromaDB
    collection = chroma_client.get_or_create_collection(
        repo_name, embedding_function=embedding_function
    )

    ids = df_embeddings["id"].tolist()
    metadatas = df_embeddings.drop(columns=["code"]).to_dict(orient="records")
    documents = df_embeddings["code"].tolist()

    collection.add(
        ids=ids,
        metadatas=metadatas,
        documents=documents
    )

    # Generate PlantUML diagrams
    diagram_generator = PlantUMLGenerator(repo_path)
    diagrams = diagram_generator.generate_all()

    return {
        "message": "Repository processed successfully",
        "diagrams": diagrams,
    }

@app.post("/ask_question/")
def ask_question(input_data: QuestionInput):
    repo_name = input_data.repo_name.replace("-", "_")

    # Validate repository metadata
    repo_path = Path(f"./.repositories/{repo_name}")
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
