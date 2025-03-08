import { useState } from "react";
import axios from "axios";

export default function RepoQABot() {
  const [repoUrl, setRepoUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [diagrams, setDiagrams] = useState({});
  const [loading, setLoading] = useState(false);

  const processRepository = async () => {
    setLoading(true);
    try {
      const response = await axios.post("http://localhost:8000/process_repository/", {
        repo_url: repoUrl,
        openai_key: apiKey,
      });
      setDiagrams(response.data.diagrams);
    } catch (error) {
      console.error("Error processing repository", error);
    }
    setLoading(false);
  };

  const askQuestion = async () => {
    setLoading(true);
    try {
      const response = await axios.post("http://localhost:8000/ask_question/", {
        question,
        repo_name: repoUrl.split("/").pop().replace(".git", ""),
        openai_key: apiKey,
      });
      setAnswer(response.data.answer);
    } catch (error) {
      console.error("Error fetching answer", error);
    }
    setLoading(false);
  };

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold mb-4">Repo QA Bot</h1>
      <input
        type="text"
        placeholder="Enter Repository URL"
        className="border p-2 w-full mb-2"
        value={repoUrl}
        onChange={(e) => setRepoUrl(e.target.value)}
      />
      <input
        type="text"
        placeholder="Enter OpenAI API Key"
        className="border p-2 w-full mb-2"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
      />
      <button
        onClick={processRepository}
        className="bg-blue-500 text-white px-4 py-2 rounded mb-4"
      >
        Process Repository
      </button>
      {loading && <p>Loading...</p>}
      {diagrams.class && <img src={diagrams.class} alt="Class Diagram" className="mb-4" />}
      {diagrams.sequence && <img src={diagrams.sequence} alt="Sequence Diagram" className="mb-4" />}
      {diagrams.component && <img src={diagrams.component} alt="Component Diagram" className="mb-4" />}
      <input
        type="text"
        placeholder="Ask a question about the repo"
        className="border p-2 w-full mb-2"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />
      <button
        onClick={askQuestion}
        className="bg-green-500 text-white px-4 py-2 rounded"
      >
        Ask Question
      </button>
      {answer && <p className="mt-4 p-2 border">{answer}</p>}
    </div>
  );
}
