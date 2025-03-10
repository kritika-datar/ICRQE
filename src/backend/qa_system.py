import openai
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


class QAProcessor:
    def __init__(self, collection, openai_key, repo_path):
        self.collection = collection
        self.openai_key = openai_key
        self.client = openai.OpenAI(api_key=openai_key)
        self.repo_path = repo_path

    def answer_question(self, question):
        query_embedding = embedding_model.encode(question).tolist()

        results = self.collection.query(query_embeddings=[query_embedding], n_results=3)

        metadata_list = results.get("metadatas", [[]])
        metadata_flat = [meta for sublist in metadata_list for meta in sublist if meta]

        documents = results.get("documents", [[]])
        documents_flat = [doc for sublist in documents for doc in sublist if doc]

        if metadata_flat and documents_flat:
            context_snippets = []
            for meta, doc in zip(metadata_flat, documents_flat):
                context_snippets.append(
                    f"File: {meta.get('file_path', 'Unknown')}\n"
                    f"Name: {meta.get('name', 'Unknown')}\n"
                    f"Type: {meta.get('type', 'Unknown')}\n"
                    f"Code:\n{doc}\n"
                )
            context_str = "\n\n".join(context_snippets)
        else:
            context_str = "No relevant context found."

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI assistant that answers questions using code from a repository. "
                        "Ensure your responses reference specific classes, functions, or files when applicable."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Repository Context:\n{context_str}\n\n"
                    f"Answer the following question based on the repository content above:\n"
                    f"{question}\n\n"
                    "If you do not find an exact match, try to infer based on related code structures.",
                },
            ],
        )

        return response.choices[0].message.content
