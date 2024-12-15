
// import React, { useState } from "react";
// // import "bootstrap/dist/css/bootstrap.min.css";
// import axios from "axios";

// const AdminUpload = () => {
//   const [file, setFile] = useState(null);
//   const [message, setMessage] = useState("");

//   const handleFileChange = (e) => {
//     setFile(e.target.files[0]);
//   };

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     if (!file) {
//       setMessage("Please select a file before uploading.");
//       return;
//     }
  
//     const formData = new FormData();
//     formData.append("file", file);
  
//     try {
//       const accessToken = localStorage.getItem("accessToken");

//       console.log('accessToken0000', accessToken);
      
  
//       const response = await axios.post("http://127.0.0.1:8000/api/chat/upload/", formData, {
//         headers: {
//           "Content-Type": "multipart/form-data",
//           Authorization: `Bearer ${accessToken}`,
//         },
//       });
  
//       setMessage("File uploaded successfully!");
//     } catch (error) {
//       setMessage("Failed to upload file. Please try again.");
//       console.error(error);
//     }
//   };

//   return (
//     <div>
//       {/* Header */}
//       <header className="bg-primary text-white py-3">
//         <div className="container text-center">
//           <h1>Admin Dashboard</h1>
//           <p>Upload Knowledge Base File</p>
//         </div>
//       </header>

//       {/* Upload Form Section */}
//       <div className="container mt-5">
//         <div className="row justify-content-center">
//           <div className="col-md-6">
//             <div className="card shadow">
//               <div className="card-header bg-secondary text-white text-center">
//                 <h4>Upload Knowledge Base</h4>
//               </div>
//               <div className="card-body">
//                 <form onSubmit={handleSubmit}>
//                   <div className="mb-3">
//                     <label htmlFor="file" className="form-label">
//                       Choose File
//                     </label>
//                     <input
//                       type="file"
//                       className="form-control"
//                       id="file"
//                       onChange={handleFileChange}
//                     />
//                   </div>
//                   <button type="submit" className="btn btn-primary w-100">
//                     Upload
//                   </button>
//                 </form>
//                 {message && (
//                   <div className="mt-3 alert alert-info text-center">
//                     {message}
//                   </div>
//                 )}
//               </div>
//             </div>
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default AdminUpload;



import React, { useState, useEffect } from "react";
import axios from "axios";

const KnowledgeBaseManager = () => {
  const [files, setFiles] = useState([]);
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");

  // Fetch all files
  const fetchFiles = async () => {
    try {
      const response = await axios.get("http://127.0.0.1:8000/api/chat/file/");
      setFiles(response.data.files);
    } catch (error) {
      console.error(error.response?.data || error.message);
      setMessage("Failed to fetch files.");
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  // Handle file selection
  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  // Handle file upload
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setMessage("Please select a file before uploading.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://127.0.0.1:8000/api/chat/upload/", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      setMessage(response.data.message);
      fetchFiles(); // Refresh file list
    } catch (error) {
      console.error(error.response?.data || error.message);
      setMessage("Failed to upload file. Please try again.");
    }
  };

  // Handle file update
  const handleUpdate = async (id) => {
    if (!file) {
      setMessage("Please select a file to update.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.put(`http://127.0.0.1:8000/api/chat/file/${id}/`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      setMessage(response.data.message);
      fetchFiles(); // Refresh file list
    } catch (error) {
      console.error(error.response?.data || error.message);
      setMessage("Failed to update the file.");
    }
  };

  // Handle file delete
  const handleDelete = async (id) => {
    try {
      const response = await axios.delete(`http://127.0.0.1:8000/api/chat/file/${id}/`);
      setMessage(response.data.message);
      fetchFiles(); // Refresh file list
    } catch (error) {
      console.error(error.response?.data || error.message);
      setMessage("Failed to delete the file.");
    }
  };

  return (
    <div>
      {/* Header */}
      <header className="bg-primary text-white py-3">
        <div className="container text-center">
          <h1>Knowledge Base Manager</h1>
          <p>Manage, Upload, and Update Knowledge Base Files</p>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mt-5">
        {/* Alert Message */}
        {message && <div className="alert alert-info text-center">{message}</div>}

        {/* Upload Form */}
        <div className="card mb-4 shadow">
          <div className="card-header bg-secondary text-white text-center">
            <h4>Upload New Knowledge Base File</h4>
          </div>
          <div className="card-body">
            <form onSubmit={handleUpload}>
              <div className="mb-3">
                <label htmlFor="file" className="form-label">
                  Choose File
                </label>
                <input
                  type="file"
                  className="form-control"
                  id="file"
                  onChange={handleFileChange}
                />
              </div>
              <button type="submit" className="btn btn-primary w-100">
                Upload
              </button>
            </form>
          </div>
        </div>

        {/* Files Table */}
        <div className="card shadow">
          <div className="card-header bg-dark text-white text-center">
            <h4>Uploaded Knowledge Base Files</h4>
          </div>
          <div className="card-body">
            {files.length > 0 ? (
              <table className="table table-bordered">
                <thead className="thead-dark">
                  <tr>
                    <th>ID</th>
                    <th>Content Preview</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((file) => (
                    <tr key={file.id}>
                      <td>{file.id}</td>
                      <td>{file.content_preview}</td>
                      <td>
                        <div className="d-flex justify-content-center">
                          <input
                            type="file"
                            className="form-control me-2"
                            onChange={handleFileChange}
                            style={{ width: "70%" }}
                          />
                          <button
                            className="btn btn-warning btn-sm me-2"
                            onClick={() => handleUpdate(file.id)}
                          >
                            Update
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => handleDelete(file.id)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-center">No files found.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeBaseManager;
