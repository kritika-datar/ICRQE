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
    <div className="p-10 max-w-4xl mx-auto">
      <h1 className="text-4xl font-bold mb-10 text-center">ICRQE</h1>

      {/* Process Repository Section */}
      <h2 className="text-3xl font-bold mb-6">📂 Process Repository</h2>

      <div className="flex flex-col space-y-6">
        <input
          type="text"
          placeholder="Enter Repository URL"
          className="border p-5 w-full h-20 text-2xl rounded-lg focus:ring-4 focus:ring-blue-300"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          style={{width: "370px"}}
        />
        <br/>
        <input
          type="text"
          placeholder="Enter OpenAI API Key"
          className="border p-5 w-full h-20 text-2xl rounded-lg focus:ring-4 focus:ring-blue-300"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          style={{width: "370px"}}
        />
        <br/>
        <button
          onClick={processRepository}
          className="bg-blue-600 text-white w-full h-20 text-3xl font-bold rounded-lg transition-all hover:scale-105 hover:bg-opacity-90 active:scale-95"
          style={{width: "370px"}}
        >
          Process Repository
        </button>
      </div>

      {loading && <p className="text-center text-2xl mt-6">Loading...</p>}

      {/* Diagrams Section */}
      <div className="mt-10 space-y-10">
        {diagrams.context && (
          <div className="text-center">
            <p className="font-bold text-3xl mb-4">Context Diagram</p>
            <img
              src={`http://localhost:8000/diagrams/${diagrams.context.split("/").pop()}`}
              alt="Context Diagram"
              className="mx-auto border shadow-lg rounded-lg"
              style={{ maxWidth: "100%", maxHeight: "600px" }}
            />
          </div>
        )}

        {diagrams.container && (
          <div className="text-center">
            <p className="font-bold text-3xl mb-4">Container Diagram</p>
            <img
              src={`http://localhost:8000/diagrams/${diagrams.container.split("/").pop()}`}
              alt="Container Diagram"
              className="mx-auto border shadow-lg rounded-lg"
              style={{ maxWidth: "100%", maxHeight: "600px" }}
            />
          </div>
        )}

        {diagrams.c4_component && (
          <div className="text-center">
            <p className="font-bold text-3xl mb-4">C4_Container Diagram</p>
            <img
              src={`http://localhost:8000/diagrams/${diagrams.c4_component.split("/").pop()}`}
              alt="C4 Component Diagram"
              className="mx-auto border shadow-lg rounded-lg"
              style={{ maxWidth: "100%", maxHeight: "600px" }}
            />
          </div>
        )}

        {diagrams.class && (
          <div className="text-center">
            <p className="font-bold text-3xl mb-4">Class Diagram</p>
            <img
              src={`http://localhost:8000/diagrams/${diagrams.class.split("/").pop()}`}
              alt="Class Diagram"
              className="mx-auto border shadow-lg rounded-lg"
              style={{ maxWidth: "100%", maxHeight: "600px" }}
            />
          </div>
        )}

        {diagrams.sequence && (
          <div className="text-center">
            <p className="font-bold text-3xl mb-4">Sequence Diagram</p>
            <img
              src={`http://localhost:8000/diagrams/${diagrams.sequence.split("/").pop()}`}
              alt="Sequence Diagram"
              className="mx-auto border shadow-lg rounded-lg"
              style={{ maxWidth: "100%", maxHeight: "600px" }}
            />
          </div>
        )}

        {diagrams.component && (
          <div className="text-center">
            <p className="font-bold text-3xl mb-4">Component Diagram</p>
            <img
              src={`http://localhost:8000/diagrams/${diagrams.component.split("/").pop()}`}
              alt="Component Diagram"
              className="mx-auto border shadow-lg rounded-lg"
              style={{ maxWidth: "100%", maxHeight: "600px" }}
            />
          </div>
        )}

      </div>

      {/* Ask Question Section */}
      <h2 className="text-3xl font-bold mt-16 mb-6">❓ Ask a Question</h2>

      <div className="flex flex-col space-y-6">
        <input
          type="text"
          placeholder="Ask a question about the repo"
          className="border p-5 w-full h-20 text-2xl rounded-lg focus:ring-4 focus:ring-green-300"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          style={{width: "370px"}}
        />
        <br/>
        <button
          onClick={askQuestion}
          className="bg-green-600 text-white w-full h-20 text-3xl font-bold rounded-lg transition-all hover:scale-105 hover:bg-opacity-90 active:scale-95"
          style={{width: "370px"}}
        >
          Ask Question
        </button>
      </div>

      {/* Answer Display */}
      {answer && (
        <p className="mt-8 p-6 border bg-gray-100 rounded-lg text-2xl shadow-lg">
          {answer}
        </p>
      )}
    </div>
  );
}
