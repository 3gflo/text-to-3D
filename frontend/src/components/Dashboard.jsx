// src/components/Dashboard.jsx
import React from 'react';
import './Dashboard.css';

const Dashboard = () => {
  // Image generation state
  const [selectedImageBase64, setSelectedImageBase64] = useState(null);

  // 3D generation state
  const [selected3DModel, setSelected3DModel] = useState('trellis');
  const [isGenerating3D, setIsGenerating3D] = useState(false);
  const [modelUrl, setModelUrl] = useState(null);

  const handleGenerate3DAsset = async () => {
    if (!selectedImageBase64) {
      alert("Please generate or select an image first!");
      return;
    }

    setIsGenerating3D(true);
    setModelUrl(null); // Clear the viewer before starting

    try {

      const response = await fetch('/api/generate-3d-model', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          images: [selectedImageBase64],
          service: selected3DModel
        }),
      });

      if (!response.ok) {
        // Attempt to parse the backend error message if available
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      // Convert the returned binary to a local blob URL
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);

      // Update state to render the model
      setModelUrl(objectUrl);

    } catch (error) {
      console.error("Failed to generate 3D model:", error);
      alert("Error generating 3D model. Check console.");
    } finally {
      setIsGenerating3D(false);
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

       {/* COLUMN 3: OUTPUT */}
        <section className="column output-column">
          <div className="column-header">OUTPUT: Final 3D Model</div>

          {/* Bind select to state */}
          <select
            className="dropdown-btn"
            value={selected3DModel}
            onChange={(e) => setSelected3DModel(e.target.value)}
          >
            <option value="trellis">Trellis</option>
            <option value="hunyuan">Hunyuan</option>
          </select>

          {/* Bind button to fetch function */}
          <button
            className="action-btn"
            onClick={handleGenerate3DAsset}
            disabled={isGenerating3D}
          >
            {isGenerating3D ? "Generating..." : "Generate 3D Asset"}
          </button>

          {/* 3D Asset Display Canvas */}
          <div className="asset-display" style={{ overflow: 'hidden', position: 'relative' }}>
              {isGenerating3D && (
                <div style={{ color: 'white', textAlign: 'center' }}>
                  <p>Building 3D model...</p>
                  <small>This may take a minute.</small>
                </div>
              )}

              {!isGenerating3D && modelUrl && (
                <model-viewer
                  src={modelUrl}
                  auto-rotate
                  camera-controls
                  style={{ width: '100%', height: '100%', backgroundColor: 'transparent' }}
                ></model-viewer>
              )}

              {!isGenerating3D && !modelUrl && (
                <p style={{ color: '#666' }}>No model generated yet.</p>
              )}
          </div>

          <div className="download-row">
            <select className="dropdown-btn download-select">
              <option value="FBX">Download as FBX</option>
              <option value="obj">Download as OBJ</option>
            </select>
            <button className="action-btn download-trigger">Download</button>
          </div>
        </section>
      </main>
    </div>
  );
};

export default Dashboard;