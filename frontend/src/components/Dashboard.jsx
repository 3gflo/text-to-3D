// src/components/Dashboard.jsx
import React from 'react';
import './Dashboard.css';

const Dashboard = () => {
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
            defaultValue="A futuristic, sleek white chair with blue LED light accents"
          />

          <button className="action-btn">Optimize Prompt</button>

          <textarea
            placeholder="Example optimized prompt"
            readOnly
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

        {/* COLUMN 3: OUTPUT - Added "output-column" class for tighter spacing */}
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

          <div className="button-group">
            <button className="download-btn">Download as OBJ</button>
            <button className="download-btn">Download as FBX</button>
          </div>
        </section>

      </main>
    </div>
  );
};

export default Dashboard;