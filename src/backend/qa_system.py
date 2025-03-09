import duckdb
import openai
from repo_parser import embedding_model


class QAProcessor:
    def __init__(self, collection, openai_key, db_path):
        self.collection = collection
        self.openai_key = openai_key
        self.db_path = db_path  # Path to DuckDB file
        # ✅ Initialize OpenAI client with API key
        self.client = openai.OpenAI(api_key=openai_key)

    def _fetch_metadata_fallback(self, question):
        """Fetch code metadata from DuckDB as a fallback."""
        try:
            conn = duckdb.connect(str(self.db_path))
            query = f"""
                    SELECT file_path, name, type, parent, start_line, end_line 
                    FROM code_metadata
                    WHERE name ILIKE '%{question}%' 
                       OR type ILIKE '%{question}%'
                       OR file_path ILIKE '%{question}%'
                    LIMIT 5
                """
            results = conn.execute(query).fetchall()
            conn.close()

            if results:
                return "\n".join(
                    [
                        f"{row[2]} '{row[1]}' in {row[0]} (Lines {row[4]}-{row[5]})"
                        for row in results
                    ]
                )
            return None

        except Exception as e:
            print(f"Metadata Fallback Error: {e}")
            return None

    def answer_question(self, question):
        """Retrieve relevant context and answer a question."""
        # relevant_docs = self.collection.query(query_texts=[question], n_results=5)
        """Finds the most relevant code snippet based on user input."""
        query_embedding = embedding_model.encode(question).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=3  # Get top 3 matches
        )

        # ✅ Extract relevant metadata & documents safely
        metadata_list = results.get("metadatas", [[]])  # Ensure list exists
        metadata_flat = [
            meta for sublist in metadata_list for meta in sublist if meta
        ]  # Flatten

        documents = results.get("documents", [[]])  # Extract documents (list of lists)
        documents_flat = [
            doc for sublist in documents for doc in sublist if doc
        ]  # Flatten

        # 🟢 Ensure we have valid extracted data
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

        # ✅ Query OpenAI with proper repository context
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
