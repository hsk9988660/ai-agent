import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AdminLogin from './components/AdminLogin';
import UploadKnowledgeBase from './components/UploadKnowledgeBase';
import QueryKnowledgeBase from './components/QueryKnowledgeBase';

function App() {
  return (
    <Router>
      <div>
        <Routes>
          <Route path="/" element={<AdminLogin />} />
          <Route path="/upload" element={<UploadKnowledgeBase />} />
          <Route path="/query" element={<QueryKnowledgeBase />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
