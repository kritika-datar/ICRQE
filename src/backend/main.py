import asyncio
import subprocess
from pathlib import Path, PosixPath

import chromadb
import numpy as np
import pandas as pd
from chromadb.utils import embedding_functions
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sklearn.decomposition import PCA

from plantuml_generator import PlantUMLGenerator
from pydantic import BaseModel
from qa_system import QAProcessor
from repo_parser import RepositoryParser

from concurrent.futures import ThreadPoolExecutor
import pandas as pd

# Initialize ChromaDB Client
CHROMA_DB_PATH = "./.chroma_db"
chroma_client = chromadb.PersistentClient(
    path=CHROMA_DB_PATH,
    settings=chromadb.Settings(
        is_persistent=True,
        persist_directory=CHROMA_DB_PATH,
        anonymized_telemetry=False,
        allow_reset=False
    ),
)

embedding_function = embedding_functions.DefaultEmbeddingFunction()

# Initialize FastAPI App
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
REPO_BASE_PATH = Path("./.repositories")


class RepoInput(BaseModel):
    repo_url: str
    openai_key: str


class QuestionInput(BaseModel):
    question: str
    repo_name: str
    openai_key: str


def get_commit_hash(repo_path, ref="HEAD"):
    """Returns the latest commit hash for a given branch or HEAD."""
    try:
        commit_hash = subprocess.check_output(
            ["git", "-C", str(repo_path), "rev-parse", ref]
        ).decode().strip()
        return commit_hash
    except subprocess.CalledProcessError:
        print(f"Warning: Could not retrieve commit hash for {ref}")
        return None


def get_remote_main_branch(repo_path):
    """Finds the correct main branch (main/master) from the remote."""
    try:
        branches = subprocess.check_output(
            ["git", "-C", str(repo_path), "branch", "-r"]
        ).decode().strip().split("\n")

        branches = [b.strip() for b in branches]

        if "origin/main" in branches:
            return "origin/main"
        elif "origin/master" in branches:
            return "origin/master"
        else:
            print("Error: No main or master branch found in remote.")
            return None
    except subprocess.CalledProcessError:
        print("Error: Could not fetch remote branches.")
        return None


def clone_or_update_repo(repo_url, repo_path):
    """Clones the repository if it doesn't exist, otherwise updates it."""
    if repo_path.is_dir() and (repo_path / ".git").is_dir():
        print("Checking for updates...")

        # Ensure we fetch the latest updates from the remote
        subprocess.run(["git", "-C", repo_path, "fetch", "origin"], check=True)

        # Detect the correct remote branch
        remote_branch = get_remote_main_branch(repo_path)
        if remote_branch is None:
            return []

        local_commit = get_commit_hash(repo_path)
        remote_commit = get_commit_hash(repo_path, remote_branch)

        if remote_commit is None:
            print(f"Error: Could not retrieve remote commit for {remote_branch}.")
            return []

        if local_commit == remote_commit:
            print("Repository is up to date.")
            return []

        print(f"Updating repository from {remote_branch}...")
        subprocess.run(["git", "-C", repo_path, "pull", "origin", remote_branch.split('/')[-1]], check=True)

        changed_files = (
            subprocess.check_output(["git", "-C", repo_path, "diff", "--name-only", local_commit, remote_commit])
            .decode()
            .splitlines()
        )
        return changed_files
    else:
        print("Cloning repository...")
        subprocess.run(["git", "clone", repo_url, str(repo_path)], check=True)
        return None


def validate_repo_metadata(repo_path):
    """Validates if the repository metadata exists."""
    parquet_path = repo_path / "embeddings.parquet"
    if not parquet_path.exists():
        raise HTTPException(status_code=500, detail="Repository metadata is missing.")
    return parquet_path

def reduce_embedding_size(embeddings, new_dim=128):
    pca = PCA(n_components=new_dim)
    return pca.fit_transform(np.array(embeddings))

async def upsert_batch_async(collection, batch):
    ids = batch["id"].tolist()
    metadatas = batch.drop(columns=["code", "docstring", "parent"]).to_dict(orient="records")
    documents = []
    for _, row in batch.iterrows():
        doc_text = f"{row['code']}\n"
        if 'docstring' in row and row['docstring']:
            doc_text += f"\nDocstring:\n{row['docstring']}\n"
        if 'parent' in row and row['parent']:
            doc_text += f"\nParent Class/Module: {row['parent']}\n"
        documents.append(doc_text)
    await asyncio.to_thread(collection.upsert, ids=ids, metadatas=metadatas, documents=documents)

async def process_embeddings_async(repo_name, parquet_path, changed_files, batch_size=100):
    df_embeddings = pd.read_parquet(parquet_path)
    if df_embeddings.empty:
        raise HTTPException(status_code=500, detail="No embeddings found.")

    if changed_files:
        df_embeddings = df_embeddings[df_embeddings["file_path"].isin(changed_files)]

    collection = chroma_client.get_or_create_collection(repo_name, embedding_function=embedding_function)

    tasks = []
    for start in range(0, len(df_embeddings), batch_size):
        end = min(start + batch_size, len(df_embeddings))
        batch = df_embeddings.iloc[start:end]
        tasks.append(upsert_batch_async(collection, batch))

    await asyncio.gather(*tasks)


def generate_diagrams(repo_path):
    """Generates PlantUML diagrams for the repository and mounts them if available."""
    diagram_generator = PlantUMLGenerator(repo_path)
    diagrams = diagram_generator.generate_all()

    diagram_path = repo_path / "diagrams"
    if diagram_path.exists():
        app.mount("/diagrams", StaticFiles(directory=str(diagram_path)), name="diagrams")

    return diagrams


@app.post("/process_repository/")
def process_repository(input_data: RepoInput):
    repo_url = input_data.repo_url
    repo_name = repo_url.split("/")[-1].replace(".git", "").replace("-", "_")
    repo_path = REPO_BASE_PATH / repo_name

    diagram_path = repo_path / "diagrams"
    if diagram_path.exists():
        app.mount("/diagrams", StaticFiles(directory=str(diagram_path)), name="diagrams")

    # Clone or update repository
    changed_files = clone_or_update_repo(repo_url, repo_path)
    if changed_files == []:
        return {
            "message": "Repository is up to date.",
            "diagrams": {
            'class': PosixPath(
                f'/Users/kritikadatar/PycharmProjects/ICRQE/src/backend/.repositories/{repo_name}/diagrams/class_diagram.png'),
            'component': PosixPath(
                f'/Users/kritikadatar/PycharmProjects/ICRQE/src/backend/.repositories/{repo_name}/diagrams/component_diagram.png'),
            'sequence': PosixPath(
                f'/Users/kritikadatar/PycharmProjects/ICRQE/src/backend/.repositories/{repo_name}/diagrams/sequence_diagram.png')
        }
        }

    changed_files = None

    """Validates if the repository metadata exists."""
    parquet_path = repo_path / "embeddings.parquet"
    # Parse repository
    parser = RepositoryParser(repo_path)
    parser.extract_code_structure(changed_files)
    asyncio.run(process_embeddings_async(repo_name, parquet_path, changed_files))

    # Generate diagrams
    diagrams = generate_diagrams(repo_path)

    return {"message": "Repository processed successfully", "diagrams": diagrams}


@app.post("/ask_question/")
def ask_question(input_data: QuestionInput):
    repo_name = input_data.repo_name.replace("-", "_")
    repo_path = REPO_BASE_PATH / repo_name

    # Validate repository metadata
    validate_repo_metadata(repo_path)

    # Load ChromaDB collection
    collection = chroma_client.get_collection(repo_name)
    if not collection:
        raise HTTPException(status_code=404, detail="ChromaDB collection not found.")

    # Get answer from QAProcessor
    qa_processor = QAProcessor(collection, input_data.openai_key, repo_path)
    answer = qa_processor.answer_question(input_data.question)

    return {"answer": answer}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
