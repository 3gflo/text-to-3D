// src/components/Dashboard.jsx
import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import '@google/model-viewer' // npm install @google/model-viewer

const Dashboard = () => {
  // State management for prompt optimization
  const [inputPrompt, setInputPrompt] = useState("A futuristic, sleek white chair with blue LED light accents");
  const [optimizedPrompt, setOptimizedPrompt] = useState("");
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [error, setError] = useState("");

  // Dynamic Model States
  const [textModels, setTextModels] = useState([]);
  const [selectedPromptService, setSelectedPromptService] = useState("");

  const [imageModels, setImageModels] = useState([]);
  const [selectedImageModel, setSelectedImageModel] = useState("");

  const [threeDModels, setThreeDModels] = useState([]);
  const [selected3DModel, setSelected3DModel] = useState("");

  // State management for image generation & selection
  const [viewpointImages, setViewpointImages] = useState({});
  const [viewpoints, setViewpoints] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const CLIP_THRESHOLD = 0.25;

  // 3D generation state
  const [isGenerating3D, setIsGenerating3D] = useState(false);
  const [modelUrl, setModelUrl] = useState(null);

  // Helper to categorize the numerical CLIP score
  const getClipLabel = (score) => {
    if (score === 0.0 || score === null || score === "N/A") return "N/A";
    if (score < 0.2) return "Low"; // arbitrary for temp use
    if (score < 0.6) return "Medium"; // arbitrary for temp use
    return "High";
  };

  // Fetch available models on mount for all asset types
  useEffect(() => {
    const fetchAvailableModels = async () => {
      const assetTypes = ['text', 'image', '3D'];

      const stateSetters = {
        text: { setList: setTextModels, setSelected: setSelectedPromptService },
        image: { setList: setImageModels, setSelected: setSelectedImageModel },
        '3D': { setList: setThreeDModels, setSelected: setSelected3DModel }
      };

      for (const type of assetTypes) {
        try {
          const response = await fetch('/api/available-models', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ asset_type: type })
          });

          if (response.ok) {
            const data = await response.json();
            console.log(data)
            const fetchedModels = data.services || [];

            stateSetters[type].setList(fetchedModels);
          } else {
            throw new Error(`Backend not ready for ${type}`);
          }
        } catch (error) {
          console.warn(`Backend unavailable for ${type} with error ${error}`);
        }
      }
    };

    fetchAvailableModels();
  }, []);

  // Handler for optimizing prompt via backend API
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

  // Handler for Image Generation fetching from Backend
  const handleGenerateImages = async () => {
    if (!selectedImageModel || selectedImageModel === "Choose Image Model") {
      alert("Please select an image model from the dropdown first.");
      return;
    }

    const promptToUse = optimizedPrompt || inputPrompt;

    if (!promptToUse.trim()) {
      alert("Please provide a prompt to generate images.");
      return;
    }

    setIsGenerating(true);
    setViewpointImages({});
    setViewpoints([]);

    try {
      const response = await fetch('/api/generate-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          optimized_prompt: promptToUse,
          service: selectedImageModel
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to generate images');
      }

      const data = await response.json();

      if (data.status === 'success' && data.viewpoint_images) {
        setViewpointImages(data.viewpoint_images);
        setViewpoints(data.viewpoints);

        // Evaluate the Images (CLIP Score) — flatten viewpoint images into a list
        const imageList = data.viewpoints
          .map(vp => data.viewpoint_images[vp])
          .filter(img => img != null);

        if (imageList.length > 0) {
          try {
            const evalResponse = await fetch('/api/evaluate-image', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                images: imageList,
                prompt: promptToUse
              })
            });

            if (evalResponse.ok) {
              const evalData = await evalResponse.json();
              if (evalData.status === 'success') {
                // Store scores keyed by viewpoint
                const scored = { ...data.viewpoint_images };
                let scoreIdx = 0;
                for (const vp of data.viewpoints) {
                  if (scored[vp] != null) {
                    scored[vp] = {
                      url: scored[vp],
                      score: evalData.evaluations[scoreIdx]?.score ?? "N/A"
                    };
                    scoreIdx++;
                  }
                }
                setViewpointImages(scored);
              }
            }
          } catch (evalError) {
            console.error("Evaluation failed:", evalError);
          }
        }
      } else {
        throw new Error("Unexpected response structure from server.");
      }
    } catch (error) {
      console.error("Error generating images:", error);
      alert(error.message || "Failed to generate images. Check console.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerate3DAsset = async () => {
    // Collect images in viewpoint order (front, back, left, right)
    const orderedImages = viewpoints
      .map(vp => {
        const entry = viewpointImages[vp];
        if (!entry) return null;
        return typeof entry === 'object' ? entry.url : entry;
      })
      .filter(img => img != null);

    if (orderedImages.length === 0) {
      alert("Please generate viewpoint images first!");
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
          images: orderedImages,
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
            <option value="">Choose Text Model</option>
            {textModels.map((modelName) => (
              <option key={modelName} value={modelName}>
                {modelName}
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

          {/* Dynamic Image Model Dropdown */}
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

          {/* Generate Batch Images Button */}
          <button
            className="action-btn"
            onClick={handleGenerateImages}
            disabled={isGenerating || !selectedImageModel}
          >
            {isGenerating ? 'Generating Images...' : 'Generate Batch Images'}
          </button>
        </section>

        {/* COLUMN 2: PROCESSING */}
        <section className="column">
          <div className="column-header">PROCESSING & QUALITY CONTROL</div>

{/*           <div style={{fontSize: '0.85rem', color: '#ccc', marginBottom: '1rem', textAlign: 'center'}}> */}
{/*             *Images must score a <strong>{CLIP_THRESHOLD}</strong> or higher to pass to 3D generation. */}
{/*           </div> */}

          <div className="image-grid">
            {viewpoints.length === 0 && !isGenerating && (
              <p style={{textAlign: 'center', width: '100%', color: '#888'}}>No images generated yet.</p>
            )}

            {isGenerating && (
              <p style={{textAlign: 'center', width: '100%', color: '#888'}}>Running pipeline... Please wait.</p>
            )}

            {/* Viewpoint Image Cards */}
            {viewpoints.map((vp) => {
              const entry = viewpointImages[vp];
              const imgUrl = entry == null ? null : (typeof entry === 'object' ? entry.url : entry);
              const score = entry != null && typeof entry === 'object' ? entry.score : "N/A";
              const status = score !== "N/A" ? getClipLabel(score).toUpperCase() : (imgUrl ? "EVALUATING" : "FAILED");

              return (
                <div key={vp} className="image-card" style={{ boxSizing: 'border-box' }}>
                  <div className="image-slot">
                    <div className={`badge ${status.toLowerCase()}`}>
                      {vp.toUpperCase()}
                    </div>
                    {imgUrl ? (
                      <img src={imgUrl} alt={`${vp} view`} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
                    ) : (
                      <div style={{width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888'}}>
                        Failed
                      </div>
                    )}
                    <div className="overlay-text">
                      <div>{vp.toUpperCase()} View</div>
                      <div>
                        CLIP Score: {score !== "N/A"
                          ? `${getClipLabel(score)} (${score})`
                          : "N/A"}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

       {/* COLUMN 3: OUTPUT */}
        <section className="column output-column">
          <div className="column-header">OUTPUT: Final 3D Model</div>

          {/* Dynamic 3D Model Dropdown */}
          <select
            className="dropdown-btn"
            value={selected3DModel}
            onChange={(e) => setSelected3DModel(e.target.value)}
          >
            <option value="">Choose 3D Generator</option>
            {threeDModels.map((modelName) => (
              <option key={modelName} value={modelName}>
                {modelName}
              </option>
            ))}
          </select>

          {/* Bind button to fetch function */}
          <button
            className="action-btn"
            onClick={handleGenerate3DAsset}
            disabled={isGenerating3D || viewpoints.length === 0}
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
                  environment-image="neutral" // Adds a default HDRI lighting environment
                  exposure="1"                // Adjusts the brightness
                  shadow-intensity="1"        // Grounds the model with a shadow
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