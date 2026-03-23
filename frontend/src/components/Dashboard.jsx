// src/components/Dashboard.jsx
import React, { useState, useEffect, useRef } from 'react';
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
  const [generatedImages, setGeneratedImages] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedImageBase64, setSelectedImageBase64] = useState(null);
  const CLIP_THRESHOLD = 0.25;

  // 3D generation state
  const [isGenerating3D, setIsGenerating3D] = useState(false);
  const [modelUrl, setModelUrl] = useState(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadFormat, setDownloadFormat] = useState("obj");
  const [isJobLocked, setIsJobLocked] = useState(false);
  const [jobAnalysis, setJobAnalysis] = useState("");
  const [jobDescription, setJobDescription] = useState("")
  const [isSaving, setIsSaving] = useState(false);

  const [showSaveModal, setShowSaveModal] = useState(false);
  const [userName, setUserName] = useState(null);

  const [isManualMode, setIsManualMode] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);
  const fileInputRef = useRef(null);

  const modelViewerRef = useRef(null);
  const [discrepancyAnalysis, setDiscrepancyAnalysis] = useState("");
  const [suggestedPrompt, setSuggestedPrompt] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);

  // Helper to categorize the numerical CLIP score
  const getClipLabel = (score) => {
    if (score === 0.0 || score === null || score === "N/A") return "N/A";
    
    // A score below 0.24 usually means the image missed the prompt entirely
    if (score < 0.24) return "Low"; 
    
    // A score between 0.24 and 0.29 is average/acceptable alignment
    if (score < 0.29) return "Medium"; 
    
    // A score of 0.29+ is exceptionally good semantic alignment for this model
    return "High";
  };

  // Handle local file upload and convert to base64
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result;
        setUploadedImage(base64String);
        // Automatically select the uploaded image for 3D generation
        setSelectedImageBase64(base64String);
      };
      reader.readAsDataURL(file);
    }
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

    // Warn user and clear images if they are starting a new optimization path
    if (generatedImages.length > 0) {
      const confirmClear = window.confirm("Optimizing a new prompt will clear your currently generated images. Do you want to continue?");
      if (!confirmClear) return;
      setGeneratedImages([]);
      setSelectedImageBase64(null);
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
    setGeneratedImages([]);
    setSelectedImageBase64(null); // Clear previous selection

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

      if (data.status === 'success' && data.images) {
        // Map the backend base64 strings to the UI array format
        const fetchedResults = data.images.map((imgStr, index) => ({
          id: index + 1,
          url: imgStr, // The python backend already appends "data:image/png;base64,"
          score: "N/A", // Placeholder until backend CLIP evaluation is implemented
          status: "EVALUATING" // Placeholder
        }));

        setGeneratedImages(fetchedResults);

        // Evaluate the Images (CLIP Score)
        try {
          const evalResponse = await fetch('/api/evaluate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              images: data.images,
              prompt: promptToUse
            })
          });

          if (evalResponse.ok) {
            const evalData = await evalResponse.json();
            if (evalData.status === 'success') {
              // Update state with the new scores and categorical statuses
              const scoredResults = fetchedResults.map((img, idx) => {
                const score = evalData.evaluations[idx].score;
                return {
                  ...img,
                  score: score,
                  status: getClipLabel(score).toUpperCase() // Sets status to LOW, MEDIUM, or HIGH
                };
              });

              // --- NEW SORTING LOGIC ---
              // Sort the array in descending order (highest score first)
              // We use a fallback to 0 in case a score somehow comes back as "N/A"
              scoredResults.sort((a, b) => {
                const scoreA = typeof a.score === 'number' ? a.score : 0;
                const scoreB = typeof b.score === 'number' ? b.score : 0;
                return scoreB - scoreA;
              });
              
              setGeneratedImages(scoredResults);
            }
          }
        } catch (evalError) {
           console.error("Evaluation failed:", evalError);
           // Fallback to N/A instead of ACCEPTED if the server errors
           const fallbackResults = fetchedResults.map(img => ({...img, status: "N/A"}));
           setGeneratedImages(fallbackResults);
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

      // LOCK THE UI AFTER SUCCESSFUL GENERATION
      setIsJobLocked(true);

    } catch (error) {
      console.error("Failed to generate 3D model:", error);
      alert("Error generating 3D model. Check console.");
    } finally {
      setIsGenerating3D(false);
    }
  };

  // Handler for downloading the 3D model
  const handleDownloadModel = async () => {
    if (!modelUrl) {
      alert("Please generate a 3D model first.");
      return;
    }

    setIsDownloading(true);

    try {
      // FAST PATH: If they want the native GLB, we don't need the backend!
      if (downloadFormat === 'glb') {
          const link = document.createElement('a');
          link.href = modelUrl;
          link.download = `generated_model.glb`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          setIsDownloading(false);
          return;
      }

      // CONVERSION PATH: Send the blob to the backend for OBJ/FBX
      // 1. Fetch the binary blob from our local model viewer
      const localResponse = await fetch(modelUrl);
      const blobData = await localResponse.blob();

      // 2. Attach it to a form payload
      const formData = new FormData();
      formData.append('model_file', blobData, 'model.glb');
      formData.append('format', downloadFormat);

      // 3. Request conversion
      const response = await fetch('/api/convert-model', {
          method: 'POST',
          body: formData
      });

      if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || "Failed to convert the model.");
      }

      // 4. Download the newly converted file
      const convertedBlob = await response.blob();
      const downloadUrl = URL.createObjectURL(convertedBlob);

      // NEW: Check if the backend sent a ZIP package (for colored OBJs)
      let extension = downloadFormat;
      if (downloadFormat === 'obj' && convertedBlob.type === 'application/zip') {
          extension = 'zip';
      }

      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `generated_model.${extension}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(downloadUrl); // Clean up memory

    } catch (error) {
        console.error("Download error:", error);
        alert("Error downloading model: " + error.message);
    } finally {
        setIsDownloading(false);
    }
  };

  // Save job data to backend and reset the 3D portion for the next run
  const handleSaveJob = async () => {
    setIsSaving(true);
    try {
      const response = await fetch('/api/save-job', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user: userName,
          description: jobDescription,

          // Conditionally submit prompt data based on the mode
          input_prompt: isManualMode ? "N/A (Manual Upload)" : inputPrompt,
          text_model: isManualMode ? "N/A" : selectedPromptService,
          optimized_prompt: isManualMode ? "N/A" : optimizedPrompt,
          image_model: isManualMode ? "Manual Upload" : selectedImageModel,

          image_1: "pending", // TODO update when we are able to show images in google sheets
          image_2: "pending",
          image_3: "pending",
          image_4: "pending",
          three_d_model: selected3DModel,
          model_link: "pending", // TODO update when we decide how to populate the model in gsheet
          analysis: jobAnalysis
        })
      });

      if (response.ok) {
        // Unlock and reset ONLY the 3D model/job states
        setIsJobLocked(false);
        setModelUrl(null);
        setJobAnalysis("");
        setJobDescription("");
        setShowSaveModal(false);
      } else {
        alert("Failed to save job to Sheets.");
      }
    } catch (error) {
      alert("Error saving job.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleAnalyzeDiscrepancies = async () => {
    if (!selectedImageBase64 || !modelUrl) {
      alert("You need both a selected image and a generated 3D model to compare.");
      return;
    }

    setIsAnalyzing(true);
    setDiscrepancyAnalysis("");
    setSuggestedPrompt("");

    try {
      const viewer = modelViewerRef.current;
      const blob = await viewer.toBlob({ idealAspect: true });

      const snapshotBase64 = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.readAsDataURL(blob);
      });

      const response = await fetch('/api/analyze-discrepancies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          original_prompt: optimizedPrompt || inputPrompt,
          input_images: [selectedImageBase64],
          model_snapshots: [snapshotBase64]
        }),
      });

      if (!response.ok) throw new Error("Analysis failed");

      const data = await response.json();
      setDiscrepancyAnalysis(data.analysis);
      setSuggestedPrompt(data.suggested_prompt);

      // Auto-populate the save job modal notes
      setJobAnalysis(`Discrepancies: ${data.analysis}`);
      setShowAnalysisModal(true);

    } catch (error) {
      console.error("Error analyzing discrepancies:", error);
      alert("Failed to analyze model discrepancies.");
    } finally {
      setIsAnalyzing(false);
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

          {/* NEW: Mode Toggle */}
          <div className="mode-toggle">
            <button
              className={`toggle-btn ${!isManualMode ? 'active' : ''}`}
              onClick={() => setIsManualMode(false)}
              disabled={isJobLocked || isGenerating}
            >
              Text to Image
            </button>
            <button
              className={`toggle-btn ${isManualMode ? 'active' : ''}`}
              onClick={() => setIsManualMode(true)}
              disabled={isJobLocked || isGenerating}
            >
              Manual Upload
            </button>
          </div>

          <textarea
            placeholder="A futuristic, sleek white chair with blue LED light accents"
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            disabled={isOptimizing || isGenerating || isJobLocked || isManualMode}
          />

          <select
            className="dropdown-btn"
            value={selectedPromptService}
            onChange={(e) => setSelectedPromptService(e.target.value)}
            disabled={isOptimizing || isGenerating || isJobLocked || isManualMode}
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
            disabled={isOptimizing || isGenerating || isJobLocked || isManualMode || !inputPrompt.trim()}
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
            disabled={isGenerating || isJobLocked || isManualMode}
            style={{ minHeight: '200px' }}
          />

          {/* Dynamic Image Model Dropdown */}
          <select
            className="dropdown-btn"
            value={selectedImageModel}
            onChange={(e) => setSelectedImageModel(e.target.value)}
            disabled={isGenerating || isJobLocked || isManualMode}
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
            disabled={isGenerating || isJobLocked || isManualMode || !selectedImageModel}
          >
            {isGenerating ? 'Generating Images...' : 'Generate Batch Images'}
          </button>
        </section>

        {/* COLUMN 2: PROCESSING */}
        <section className="column">
          <div className="column-header">PROCESSING & QUALITY CONTROL</div>

          {isManualMode ? (
            /* NEW: Manual Upload UI */
            <div className="upload-container">
              <input
                type="file"
                accept="image/*"
                style={{ display: 'none' }}
                ref={fileInputRef}
                onChange={handleFileUpload}
              />

              {!uploadedImage ? (
                <button
                  className="action-btn"
                  style={{ width: '60%', padding: '1rem' }}
                  onClick={() => fileInputRef.current.click()}
                  disabled={isJobLocked}
                >
                  Click to Upload Image
                </button>
              ) : (
                <div className="image-card" style={{ width: '80%', margin: '0 auto' }}>
                  <div
                    className="image-slot"
                    style={{
                      border: selectedImageBase64 === uploadedImage ? '3px solid #4CAF50' : 'none',
                      boxSizing: 'border-box'
                    }}
                  >
                    <div className="badge n\/a" style={{ backgroundColor: '#6c757d' }}>MANUAL</div>
                    <img src={uploadedImage} alt="Uploaded file" style={{width: '100%', height: '100%', objectFit: 'cover'}} />

                    {/* Clear Button */}
                    {!isJobLocked && (
                      <button
                        onClick={() => { setUploadedImage(null); setSelectedImageBase64(null); }}
                        style={{ position: 'absolute', top: 5, right: 5, cursor: 'pointer', background: 'rgba(0,0,0,0.6)', color: 'white', border: 'none', borderRadius: '50%', width: '24px', height: '24px' }}
                      >
                        ✕
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* EXISTING: Generated Image Grid */
            <div className="image-grid">
              {generatedImages.length === 0 && !isGenerating && (
                <p style={{textAlign: 'center', width: '100%', color: '#888'}}>No images generated yet.</p>
                )}
              {isGenerating && (
                <p style={{textAlign: 'center', width: '100%', color: '#888'}}>Running pipeline... Please wait.</p>
              )}

            {/* Dynamically Populated Image Cards */}
            {generatedImages.map((img) => (
              <div
                key={img.id}
                className="image-card"
                onClick={() => !isJobLocked && setSelectedImageBase64(img.url)}
                style={{
                  cursor: isJobLocked ? 'not-allowed' : 'pointer',
                  border: selectedImageBase64 === img.url ? '3px solid #4CAF50' : 'none',
                  boxSizing: 'border-box',
                  opacity: isJobLocked && selectedImageBase64 !== img.url ? 0.5 : 1
                }}
              >
                <div className="image-slot">
                  <div className={`badge ${img.status.toLowerCase()}`}>
                    {img.status}
                  </div>
                  <img src={img.url} alt="Generated view" style={{width: '100%', height: '100%', objectFit: 'cover'}} />
                  <div className="overlay-text">
                    <div>Generated Image</div>
                    <div>
                      CLIP Score: {img.score !== "N/A"
                        ? `${getClipLabel(img.score)} (${img.score})`
                        : "N/A"}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          )}
        </section>

       {/* COLUMN 3: OUTPUT */}
        <section className="column output-column">
          <div className="column-header">OUTPUT: Final 3D Model</div>

          {/* Dynamic 3D Model Dropdown */}
          <select
            className="dropdown-btn"
            value={selected3DModel}
            onChange={(e) => setSelected3DModel(e.target.value)}
            disabled={isJobLocked}
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
            disabled={isGenerating3D || isJobLocked || !selectedImageBase64}
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
                  ref={modelViewerRef}
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

          {/* VLM Comparison Section */}
          <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem' }}>
            <button
              className="action-btn"
              onClick={handleAnalyzeDiscrepancies}
              disabled={isAnalyzing || !modelUrl || !selectedImageBase64}
              style={{ width: '100%', padding: '8px' }}
            >
              {isAnalyzing ? 'Analyzing Differences...' : 'Compare Image to 3D Model'}
            </button>
          </div>

         <div className="download-row" style={{ marginTop: '0.25rem', paddingBottom: '0' }}>
            <select
              className="dropdown-btn download-select"
              value={downloadFormat}
              onChange={(e) => setDownloadFormat(e.target.value)}
              disabled={!modelUrl || isDownloading || isGenerating3D}
            >
              <option value="glb">Download as GLB (Native)</option>
              <option value="obj">Download as OBJ</option>
              <option value="fbx">Download as FBX</option>
            </select>
            <button
              className="action-btn download-trigger"
              onClick={handleDownloadModel}
              disabled={!modelUrl || isDownloading || isGenerating3D}
            >
              {isDownloading ? "Processing..." : "Download"}
            </button>
          </div>

          {/* Save button */}
          <button
            className="action-btn"
            style={{
              backgroundColor: modelUrl ? 'var(--badge-green)' : '#6c757d',
              width: '100%',
              marginTop: '0.25rem',
              cursor: modelUrl ? 'pointer' : 'not-allowed',
              opacity: modelUrl ? 1 : 0.5
            }}
            onClick={() => setShowSaveModal(true)}
            disabled={!modelUrl}
          >
            Save and start new job (only the 3D Model will be cleared)
          </button>

        </section>
      </main>

      {/* NEW: MODAL OVERLAY PORTION (Add right before the final closing </div>) */}
      {showSaveModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Log Run Analysis</h3>

            <label className="modal-label">User</label>
            <input
              type="text"
              className="modal-input"
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              disabled={isSaving}
            />

            <label className="modal-label">Brief Description of Goal</label>
            <textarea
              className="modal-textarea"
              placeholder="What was the goal of this run?"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              disabled={isSaving}
            />

            <label className="modal-label">Brief Analysis / Notes</label>
            <textarea
              className="modal-textarea"
              placeholder="What worked well? What failed? General observations..."
              value={jobAnalysis}
              onChange={(e) => setJobAnalysis(e.target.value)}
              disabled={isSaving}
            />

            <div className="modal-actions">
              <button
                className="action-btn"
                style={{ backgroundColor: '#6c757d', width: 'auto' }}
                onClick={() => setShowSaveModal(false)}
                disabled={isSaving}
              >
                Cancel
              </button>
              <button
                className="action-btn"
                style={{ backgroundColor: 'var(--badge-green)', width: 'auto' }}
                onClick={handleSaveJob}
                disabled={isSaving}
              >
                {isSaving ? "Saving..." : "Save Job & Start New Run"}
              </button>
            </div>
          </div>
        </div>
      )}

     {/* VLM ANALYSIS MODAL */}
      {showAnalysisModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '600px' }}>
            <h3>QA Analysis Results</h3>

            <div style={{ marginBottom: '1rem' }}>
              <strong style={{ color: 'var(--badge-red)', display: 'block', marginBottom: '0.5rem' }}>Discrepancies Found:</strong>
              <p style={{ margin: 0, lineHeight: '1.5', fontSize: '0.95rem' }}>{discrepancyAnalysis}</p>
            </div>

            <div style={{ marginBottom: '1rem', backgroundColor: '#f8f9fa', padding: '1rem', borderRadius: '4px', border: '1px solid #dee2e6' }}>
              <strong style={{ color: 'var(--badge-green)', display: 'block', marginBottom: '0.5rem' }}>Suggested Optimized Prompt:</strong>
              <p style={{ margin: 0, lineHeight: '1.5', fontStyle: 'italic', fontSize: '0.95rem', userSelect: 'all' }}>
                {suggestedPrompt}
              </p>
            </div>

            <div style={{ fontSize: '0.9rem', color: '#555', backgroundColor: '#e9ecef', padding: '10px', borderRadius: '4px', textAlign: 'center' }}>
              <strong>Want to use this prompt?</strong> <br/>
              Copy the text above to your clipboard, close this pop-up, and click "Save and start new job" for a fresh run.
            </div>

            <div className="modal-actions" style={{ justifyContent: 'center', marginTop: '1.5rem' }}>
              <button
                className="action-btn"
                style={{ width: 'auto', padding: '10px 20px' }}
                onClick={() => setShowAnalysisModal(false)}
              >
                Close Analysis
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;