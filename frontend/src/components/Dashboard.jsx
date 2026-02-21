// src/components/Dashboard.jsx
import React, { useState, useEffect } from 'react';
import './Dashboard.css';

const Dashboard = () => {
    // State management for prompt optimization (From Main)
  const [inputPrompt, setInputPrompt] = useState("A futuristic, sleek white chair with blue LED light accents");
  const [optimizedPrompt, setOptimizedPrompt] = useState("");
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [error, setError] = useState("");
  const [selectedPromptService, setSelectedPromptService] = useState("gpt-oss");

  // State management for image generation & selection (Ticket 12)
  const [imageModels, setImageModels] = useState([]);
  const [selectedImageModel, setSelectedImageModel] = useState("");
  const [generatedImages, setGeneratedImages] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const CLIP_THRESHOLD = 0.25;

  // Available prompt optimization services (From Main)
  const promptServices = [
    { value: "gpt-oss", label: "GPT-OSS " },
    { value: "gemini-2.5-flash", label: "Gemini 2.5 " },
  ];

  // Image generation state
  const [selectedImageBase64, setSelectedImageBase64] = useState(null);

  // 3D generation state
  const [selected3DModel, setSelected3DModel] = useState('trellis');
  const [isGenerating3D, setIsGenerating3D] = useState(false);
  const [modelUrl, setModelUrl] = useState(null);

  // Fetch available image models on mount (Ticket 12)
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
        console.warn("Backend unavailable, using mock image models for UI testing.");
        setImageModels(["imagen", "nano-banana", "GPT-image"]);
      }
    };

    fetchModels();
  }, []);

  // Handler for optimizing prompt via backend API (From Main)
  const handleOptimizePrompt = async () => {
    if (!inputPrompt.trim()) {
      setError("Please enter a prompt to optimize");
      return;
    }

    setError("");
    setIsOptimizing(true);

    try {
      const response = await fetch('/api/optimize-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

  // Handler for Image Generation & Mock CLIP Scoring (Ticket 12)
  const handleGenerateImages = async () => {
    if (!selectedImageModel || selectedImageModel === "Choose Image Model") {
      alert("Please select an image model from the dropdown first.");
      return;
    }

    // Use optimized prompt if available, otherwise fallback to input prompt
    const promptToUse = optimizedPrompt || inputPrompt;

    if (!promptToUse.trim()) {
      alert("Please provide a prompt to generate images.");
      return;
    }

    setIsGenerating(true);
    setGeneratedImages([]);

    // Simulate backend processing time for UI testing
    setTimeout(() => {
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
          url: "https://placehold.co/400x400/eeeeee/333333?text=Top+View",
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

          {/* Original Prompt Textarea */}
          <textarea
            placeholder="A futuristic, sleek white chair with blue LED light accents"
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            disabled={isOptimizing || isGenerating}
          />

          {/* Prompt Service Dropdown */}
          <select
            className="dropdown-btn"
            value={selectedPromptService}
            onChange={(e) => setSelectedPromptService(e.target.value)}
            disabled={isOptimizing || isGenerating}
          >
            {promptServices.map((service) => (
              <option key={service.value} value={service.value}>
                {service.label}
              </option>
            ))}
          </select>

          {/* Optimize Prompt Button */}
          <button
            className="action-btn"
            onClick={handleOptimizePrompt}
            disabled={isOptimizing || isGenerating || !inputPrompt.trim()}
          >
            {isOptimizing ? 'Optimizing...' : 'Optimize Prompt'}
          </button>

          {error && (
            <div style={{ color: 'red', fontSize: '14px', margin: '8px 0' }}>
              {error}
            </div>
          )}

          {/* Optimized Prompt Output (Editable) */}
          <textarea
            placeholder="Optimized prompt will appear here (editable)"
            value={optimizedPrompt}
            onChange={(e) => setOptimizedPrompt(e.target.value)}
            disabled={isGenerating}
          />

          {/* Dynamic Image Model Dropdown (Ticket 12) */}
          <select
            className="dropdown-btn"
            value={selectedImageModel}
            onChange={(e) => setSelectedImageModel(e.target.value)}
            disabled={isGenerating}
          >
            <option value="">Choose Image Model</option>
            {imageModels.map((modelName) => (
              <option key={modelName} value={modelName}>
                {modelName}
              </option>
            ))}
          </select>

          {/* Generate Batch Images Button (Ticket 12) */}
          <button
            className="action-btn"
            onClick={handleGenerateImages}
            disabled={isGenerating || !selectedImageModel}
          >
            {isGenerating ? 'Generating Images...' : 'Generate Batch Images'}
          </button>
        </section>

        {/* COLUMN 2: PROCESSING (Ticket 12) */}
        <section className="column">
          <div className="column-header">PROCESSING & QUALITY CONTROL</div>

          <div style={{fontSize: '0.85rem', color: '#ccc', marginBottom: '1rem', textAlign: 'center'}}>
            *Images must score a <strong>{CLIP_THRESHOLD}</strong> or higher to pass to 3D generation.
          </div>

          <div className="image-grid">
            {generatedImages.length === 0 && !isGenerating && (
              <p style={{textAlign: 'center', width: '100%', color: '#888'}}>No images generated yet.</p>
            )}

            {isGenerating && (
              <p style={{textAlign: 'center', width: '100%', color: '#888'}}>Running pipeline... (Mocking)</p>
            )}

            {/* Dynamically Populated Image Cards */}
            {generatedImages.map((img) => (
              <div key={img.id} className="image-card">
                <div className="image-slot">
                  <div className={`badge ${img.status.toLowerCase()}`}>
                    {img.status}
                  </div>
                  <img src={img.url} alt="Generated view" style={{width: '100%', height: '100%', objectFit: 'cover'}} />
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