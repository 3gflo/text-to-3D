// src/components/Dashboard.jsx
import React, { useState } from 'react';
import './Dashboard.css';

const Dashboard = () => {
  // State management for prompt optimization
  const [inputPrompt, setInputPrompt] = useState("A futuristic, sleek white chair with blue LED light accents");
  const [optimizedPrompt, setOptimizedPrompt] = useState("");
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [error, setError] = useState("");
  const [selectedPromptService, setSelectedPromptService] = useState("gpt-oss");

  // Available prompt optimization services
  const promptServices = [
    { value: "gpt-oss", label: "GPT-OSS " },
    { value: "gemini-2.5-flash", label: "Gemini 2.5 " },
  ];

  // Handler for optimizing prompt via backend API
  const handleOptimizePrompt = async () => {
    // Client-side validation
    if (!inputPrompt.trim()) {
      setError("Please enter a prompt to optimize");
      return;
    }

    // Clear previous error
    setError("");
    setIsOptimizing(true);

    try {
      const response = await fetch('/api/optimize-prompt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: inputPrompt.trim(),
          service: selectedPromptService
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to optimize prompt');
      }

      const data = await response.json();
      setOptimizedPrompt(data.optimized_prompt);
    } catch (err) {
      console.error('Error optimizing prompt:', err);
      setError(err.message || 'Failed to optimize prompt. Please try again.');
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="header">
        <h1>Gulfstream Text to 3D Model Generator</h1>
        <h2>Dashboard</h2>
      </header>

      {/* Main Content Area */}
      <main className="main-content">

        {/* COLUMN 1: INPUT */}
        <section className="column">
          <div className="column-header">INPUT: Prompt Engineering</div>

          <textarea
            placeholder="A futuristic, sleek white chair with blue LED light accents"
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            disabled={isOptimizing}
          />

          <select
            className="dropdown-btn"
            value={selectedPromptService}
            onChange={(e) => setSelectedPromptService(e.target.value)}
            disabled={isOptimizing}
          >
            {promptServices.map((service) => (
              <option key={service.value} value={service.value}>
                {service.label}
              </option>
            ))}
          </select>

          <button
            className="action-btn"
            onClick={handleOptimizePrompt}
            disabled={isOptimizing || !inputPrompt.trim()}
          >
            {isOptimizing ? 'Optimizing...' : 'Optimize Prompt'}
          </button>

          {error && (
            <div style={{ color: 'red', fontSize: '14px', margin: '8px 0' }}>
              {error}
            </div>
          )}

          <textarea
            placeholder="Optimized prompt will appear here (editable)"
            value={optimizedPrompt}
            onChange={(e) => setOptimizedPrompt(e.target.value)}
          />

          <select className="dropdown-btn">
            <option>Choose Image Model</option>
          </select>

          <button className="action-btn">Generate Batch Images</button>
        </section>

        {/* COLUMN 2: PROCESSING */}
        <section className="column">
          <div className="column-header">PROCESSING & QUALITY CONTROL</div>

          <div className="image-grid">
            {/* Image Card 1 - Rejected */}
            <div className="image-card">
              <div className="image-slot">
                <div className="badge rejected">REJECTED</div>
                <div className="overlay-text">
                  <div>Generated Image</div>
                  <div>CLIP Score: 0.18 (Below Threshold)</div>
                </div>
              </div>
            </div>

            {/* Image Card 2 - Rejected */}
            <div className="image-card">
              <div className="image-slot">
                <div className="badge rejected">REJECTED</div>
                <div className="overlay-text">
                  <div>Generated Image</div>
                  <div>CLIP Score: 0.15 (Below Threshold)</div>
                </div>
              </div>
            </div>

            {/* Image Card 3 - Accepted */}
            <div className="image-card">
              <div className="image-slot">
                <div className="badge accepted">ACCEPTED</div>
                <div className="overlay-text">
                  <div>Generated Image</div>
                  <div>CLIP Score: 0.36 (Passed)</div>
                </div>
              </div>
            </div>

            {/* Image Card 4 - Accepted */}
            <div className="image-card">
              <div className="image-slot">
                <div className="badge accepted">ACCEPTED</div>
                <div className="overlay-text">
                  <div>Generated Image</div>
                  <div>CLIP Score: 0.37 (Passed)</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* COLUMN 3: OUTPUT */}
        <section className="column output-column">
          <div className="column-header">OUTPUT: Final 3D Model</div>

          <select className="dropdown-btn">
            <option>Choose 3D Asset Model</option>
          </select>

          <button className="action-btn">Generate 3D Asset</button>

          {/* 3D Asset Placeholder */}
          <div className="asset-display">
              {/* 3D Model Canvas goes here */}
          </div>

          {/* New Download Row */}
          <div className="download-row">
            <select className="dropdown-btn download-select">
              <option value="obj">Download as OBJ</option>
              <option value="fbx">Download as FBX</option>
            </select>
            <button className="action-btn download-trigger">Download</button>
          </div>

        </section>

      </main>
    </div>
  );
};

export default Dashboard;