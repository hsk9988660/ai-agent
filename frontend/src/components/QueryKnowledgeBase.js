import React, { useState } from "react";
import axios from "axios";

const QueryInterface = () => {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [chatHistory, setChatHistory] = useState([]);

  const handleQuery = async () => {
    if (!query) return;

    try {
      const result = await axios.post("http://127.0.0.1:8000/api/chat/query/", { query });
      const aiResponse = result.data.response;

      // Update chat history
      setChatHistory([...chatHistory, { user: query, ai: aiResponse }]);
      setResponse(aiResponse);
      setQuery("");
    } catch (error) {
      console.error("Error:", error);
      setResponse("An error occurred while processing your query.");
    }
  };

  return (
    <div className="container mt-5">
      <h2 className="text-center mb-4">AI Query Interface</h2>

      <div className="card shadow">
        <div className="card-body">
          <div className="mb-3">
            <label className="form-label">Ask a question:</label>
            <input
              type="text"
              className="form-control"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type your question here..."
            />
          </div>
          <button className="btn btn-primary w-100" onClick={handleQuery}>
            Submit
          </button>
        </div>
      </div>

      {/* Chat History */}
      <div className="mt-4">
        <h5>Chat History</h5>
        <ul className="list-group">
          {chatHistory.map((chat, index) => (
            <li key={index} className="list-group-item">
              <strong>You:</strong> {chat.user}
              <br />
              <strong>AI:</strong> {chat.ai}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default QueryInterface;
