import React, { useState } from 'react';
import './AdminLogin.css'; // Import the CSS for styling
import { useNavigate } from 'react-router-dom'; // For redirecting after successful login
import axios from 'axios';

const AdminLogin = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(''); // Clear previous error messages

    try {
      // Make an API request to the login endpoint
      const response = await axios.post('http://127.0.0.1:8000/api/chat/admin-login/', {
        username,
        password,
      });

      console.log('response.data90999', response.data);
      
      const { access, refresh } = response.data;


   // Save tokens to localStorage
   localStorage.setItem("accessToken", access);
   localStorage.setItem("refreshToken", refresh);

      // Redirect to the Upload Knowledge Base page
      navigate('/upload');
    } catch (error) {
      // Set an error message if the login fails
      setError('Invalid username or password, or you are not an admin.');
    }
  };


  return (
    <div className="login-container">
      <div className="login-box">
        <h2 className="login-header">Ai Agent Administration</h2>
        {error && <p className="login-error">{error}</p>}
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label htmlFor="username">Username:</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password:</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
            />
          </div>
          <button type="submit" className="login-button">Log in</button>
        </form>
      </div>
    </div>
  );
};

export default AdminLogin;
