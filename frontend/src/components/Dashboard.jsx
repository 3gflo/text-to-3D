import React, { useState, useEffect } from 'react';
import './Dashboard.css';

const Dashboard = () => {
  // State for Inputs
  const [prompt, setPrompt] = useState("A futuristic, sleek white chair with blue LED light accents");
  const [imageModels, setImageModels] = useState([]);
  const [selectedImageModel, setSelectedImageModel] = useState("");
  
  // State for Outputs
  const [generatedImages, setGeneratedImages] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);

  // Configuration
  const CLIP_THRESHOLD = 0.24;

  // Fetch available models on component mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch('/api/available-models', {
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ asset_type: 'image' })
        });

        if (response.ok) {
          const data = await response.json();
          setImageModels(data.services || []);
        } else {
          throw new Error("Backend not ready");
        }
      } catch (error) {
        console.warn("Backend unavailable, using mock models for UI testing.");
        setImageModels(["imagen", "nano-banana", "GPT-image"]); // Mock models
      }
    };

    fetchModels();
  }, []);

  // Handle Image Generation (MOCKED FOR UI TESTING)
  const handleGenerateImages = async () => {
    if (!selectedImageModel || selectedImageModel === "Choose Image Model") {
      alert("Please select an image model from the dropdown first.");
      return;
    }

    setIsGenerating(true);
    setGeneratedImages([]); // Clear previous images

    // Simulate backend processing time (2 seconds)
    setTimeout(() => {
      // Create mock data to populate the UI grid
      const mockResults = [
        {
          id: 1,
          url: "https://placehold.co/400x400/eeeeee/333333?text=Front+View",
          score: 0.36,
          status: "ACCEPTED"
        },
        {
          id: 2,
          url: "https://placehold.co/400x400/eeeeee/333333?text=Left+View",
          score: 0.28,
          status: "ACCEPTED"
        },
        {
          id: 3,
          url: "https://placehold.co/400x400/eeeeee/333333?text=Back+View",
          score: 0.15,
          status: "REJECTED"
        },
        {
          id: 4,
          url: "https://placehold.co/400x400/eeeeee/333333?text=Right+View",
          score: 0.18,
          status: "REJECTED"
        }
      ];

      setGeneratedImages(mockResults);
      setIsGenerating(false);
    }, 2000);
  };

  return (
    <div className="dashboard-container">
      <header className="header">
        <h1>Gulfstream Text to 3D Model Generator</h1>
        <h2>Dashboard</h2>
      </header>

      <main className="main-content">
        {/* COLUMN 1: INPUT */}
        <section className="column">
          <div className="column-header">INPUT: Prompt Engineering</div>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="A futuristic, sleek white chair..."
          />

          <button className="action-btn">Optimize Prompt</button>

          <textarea
            placeholder="Example optimized prompt"
            readOnly
          />

          {/* DYNAMIC DROPDOWN */}
          <select 
            className="dropdown-btn" 
            value={selectedImageModel} 
            onChange={(e) => setSelectedImageModel(e.target.value)}
          >
            <option value="">Choose Image Model</option>
            {imageModels.map((modelName) => (
              <option key={modelName} value={modelName}>
                {modelName}
              </option>
            ))}
          </select>

          {/* GENERATE BUTTON */}
          <button 
            className="action-btn" 
            onClick={handleGenerateImages} 
            disabled={isGenerating}
          >
            {isGenerating ? "Generating..." : "Generate Images"}
          </button>
        </section>

        {/* COLUMN 2: PROCESSING & QUALITY CONTROL */}
        <section className="column">
          <div className="column-header">PROCESSING & QUALITY CONTROL</div>
          
          <div style={{fontSize: '0.85rem', color: '#ccc', marginBottom: '1rem', textAlign: 'center'}}>
            *Images must score a <strong>{CLIP_THRESHOLD}</strong> or higher on semantic accuracy to pass to 3D generation.
          </div>

          <div className="image-grid">
            {generatedImages.length === 0 && !isGenerating && (
              <p style={{textAlign: 'center', width: '100%', color: '#888'}}>No images generated yet.</p>
            )}

            {isGenerating && (
              <p style={{textAlign: 'center', width: '100%', color: '#888'}}>Running pipeline... (Mocking)</p>
            )}

            {/* DYNAMICALLY POPULATE RETURNED IMAGES */}
            {generatedImages.map((img) => (
              <div key={img.id} className="image-card">
                <div className="image-slot">
                  <div className={`badge ${img.status.toLowerCase()}`}>
                    {img.status}
                  </div>
                  <img src={img.url} alt="Generated" style={{width: '100%', height: '100%', objectFit: 'cover'}} />
                  <div className="overlay-text">
                    <div>Generated Image</div>
                    <div>CLIP Score: {img.score}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* COLUMN 3: OUTPUT */}
        <section className="column output-column">
          <div className="column-header">OUTPUT: Final 3D Model</div>

          <select className="dropdown-btn">
            <option>Choose 3D Asset Model</option>
          </select>

          <button className="action-btn">Generate 3D Asset</button>

          <div className="asset-display">
              <span style={{color: '#888'}}>3D Viewer Placeholder</span>
          </div>

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