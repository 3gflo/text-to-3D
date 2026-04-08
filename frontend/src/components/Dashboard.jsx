import React, { useState, useEffect, useRef } from 'react';
import './Dashboard.css';
import '@google/model-viewer';
import 'aframe';

/**
 * CLIP score thresholds for categorizing image-prompt alignment quality.
 * Scores below 0.24 are typically poor alignment; 0.29+ is strong alignment.
 */
const CLIP_THRESHOLD = 0.25;

/**
 * Main application dashboard. Manages the full text-to-3D generation workflow:
 *   1. Prompt optimization via LLM
 *   2. Batch image generation with CLIP quality scoring
 *   3. 3D model generation from a selected image
 *   4. Discrepancy analysis comparing the 2D concept to the 3D output
 *   5. Job logging to Google Sheets
 */
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

  // 3D generation state
  const [isGenerating3D, setIsGenerating3D] = useState(false);
  const [modelUrl, setModelUrl] = useState(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadFormat, setDownloadFormat] = useState("obj");
  const [isJobLocked, setIsJobLocked] = useState(false);
  const [jobAnalysis, setJobAnalysis] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const [showVR, setShowVR] = useState(false); // VR state

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

  /**
   * Map a numeric CLIP score to a human-readable quality label.
   * Thresholds are calibrated for the CLIP ViT-B/32 model.
   *
   * @param {number|string|null} score
   * @returns {"N/A"|"Low"|"Medium"|"High"}
   */
  const getClipLabel = (score) => {
    if (score === 0.0 || score === null || score === "N/A") return "N/A";
    if (score < 0.24) return "Low";
    if (score < 0.29) return "Medium";
    return "High";
  };

  /**
   * Read a user-selected image file and store it as a base64 data URI.
   * Also auto-selects the image for 3D generation.
   *
   * @param {React.ChangeEvent<HTMLInputElement>} event
   */
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result;
        setUploadedImage(base64String);
        setSelectedImageBase64(base64String);
      };
      reader.readAsDataURL(file);
    }
  };

  // Fetch the available model names for each pipeline stage on mount
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
            const fetchedModels = data.services || [];
            stateSetters[type].setList(fetchedModels);
          } else {
            throw new Error(`Backend not ready for ${type}`);
          }
        } catch (error) {
          console.warn(`Could not fetch models for type '${type}': ${error}`);
        }
      }
    };

    fetchAvailableModels();
  }, []);

  /**
   * Send the input prompt to the selected LLM service for optimization.
   * Warns the user if generated images will be cleared as a side effect.
   */
  const handleOptimizePrompt = async () => {
    if (!inputPrompt.trim()) {
      setError("Please enter a prompt to optimize");
      return;
    }

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
      console.error('Prompt optimization error:', err);
      setError(err.message || 'Failed to optimize prompt. Please try again.');
    } finally {
      setIsOptimizing(false);
    }
  };

  /**
   * Generate a batch of 3 images from the current prompt using the selected image model.
   * Scores each image with CLIP and sorts the results by score descending.
   */
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
    setSelectedImageBase64(null);

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
        const fetchedResults = data.images.map((imgStr, index) => ({
          id: index + 1,
          url: imgStr,
          score: "N/A",
          status: "EVALUATING"
        }));

        setGeneratedImages(fetchedResults);

        // CLIP evaluation pass
        try {
          const evalResponse = await fetch('/api/evaluate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ images: data.images, prompt: promptToUse })
          });

          if (evalResponse.ok) {
            const evalData = await evalResponse.json();
            if (evalData.status === 'success') {
              const scoredResults = fetchedResults.map((img, idx) => {
                const score = evalData.evaluations[idx].score;
                return {
                  ...img,
                  score,
                  status: getClipLabel(score).toUpperCase()
                };
              });

              // Sort by CLIP score descending so the best image appears first
              scoredResults.sort((a, b) => {
                const scoreA = typeof a.score === 'number' ? a.score : 0;
                const scoreB = typeof b.score === 'number' ? b.score : 0;
                return scoreB - scoreA;
              });

              setGeneratedImages(scoredResults);
            }
          }
        } catch (evalError) {
          console.error("CLIP evaluation failed:", evalError);
          setGeneratedImages(fetchedResults.map(img => ({ ...img, status: "N/A" })));
        }
      } else {
        throw new Error("Unexpected response structure from server.");
      }
    } catch (error) {
      console.error("Image generation error:", error);
      alert(error.message || "Failed to generate images. Check console.");
    } finally {
      setIsGenerating(false);
    }
  };

  /**
   * Send the selected image to the 3D generation service and load the returned GLB
   * into the model viewer. Locks the job controls after a successful generation.
   */
  const handleGenerate3DAsset = async () => {
    if (!selectedImageBase64) {
      alert("Please generate or select an image first!");
      return;
    }

    setIsGenerating3D(true);
    setModelUrl(null);

    try {
      const response = await fetch('/api/generate-3d-model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          images: [selectedImageBase64],
          service: selected3DModel
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const blob = await response.blob();
      setModelUrl(URL.createObjectURL(blob));
      setIsJobLocked(true);

    } catch (error) {
      console.error("3D generation error:", error);
      alert("Error generating 3D model. Check console.");
    } finally {
      setIsGenerating3D(false);
    }
  };

  /**
   * Download the generated model in the selected format.
   * GLB is served directly from the local blob URL. OBJ conversion goes through the backend,
   * which may return a ZIP archive when textures are included.
   */
  const handleDownloadModel = async () => {
    if (!modelUrl) {
      alert("Please generate a 3D model first.");
      return;
    }

    setIsDownloading(true);

    try {
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

      // Send the blob to the backend for format conversion
      const localResponse = await fetch(modelUrl);
      const blobData = await localResponse.blob();

      const formData = new FormData();
      formData.append('model_file', blobData, 'model.glb');
      formData.append('format', downloadFormat);

      const response = await fetch('/api/convert-model', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || "Failed to convert the model.");
      }

      const convertedBlob = await response.blob();
      const downloadUrl = URL.createObjectURL(convertedBlob);

      // OBJ exports with textures come back as a ZIP archive
      const extension = (downloadFormat === 'obj' && convertedBlob.type === 'application/zip')
        ? 'zip'
        : downloadFormat;

      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `generated_model.${extension}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(downloadUrl);

    } catch (error) {
      console.error("Download error:", error);
      alert("Error downloading model: " + error.message);
    } finally {
      setIsDownloading(false);
    }
  };

  /**
   * Save the current job to Google Sheets, then reset the 3D model state
   * so the user can start a new generation run with the same prompt.
   */
  const handleSaveJob = async () => {
    setIsSaving(true);
    try {
      const response = await fetch('/api/save-job', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user: userName,
          description: jobDescription,
          input_prompt: isManualMode ? "N/A (Manual Upload)" : inputPrompt,
          text_model: isManualMode ? "N/A" : selectedPromptService,
          optimized_prompt: isManualMode ? "N/A" : optimizedPrompt,
          image_model: isManualMode ? "Manual Upload" : selectedImageModel,
          image_1: "pending", // TODO: populate with image URLs when Sheets image embedding is supported
          image_2: "pending",
          image_3: "pending",
          image_4: "pending",
          three_d_model: selected3DModel,
          model_link: "pending", // TODO: populate when model storage is configured
          analysis: jobAnalysis
        })
      });

      if (response.ok) {
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

  /**
   * Capture a snapshot of the model viewer and send it alongside the 2D concept image
   * to Gemini for discrepancy analysis. Populates the analysis modal with results.
   */
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
      setJobAnalysis(`Discrepancies: ${data.analysis}`);
      setShowAnalysisModal(true);

    } catch (error) {
      console.error("Discrepancy analysis error:", error);
      alert("Failed to analyze model discrepancies.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="dashboard-container">
      <header className="header">
        <h1>Gulfstream Text to 3D Model Generator</h1>
        <h2>Dashboard</h2>
      </header>

      <main className="main-content">

        {/* ── COLUMN 1: PROMPT ENGINEERING ── */}
        <section className="column">
          <div className="column-header">INPUT: Prompt Engineering</div>

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
              <option key={modelName} value={modelName}>{modelName}</option>
            ))}
          </select>

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

          <textarea
            placeholder="Optimized prompt will appear here (editable)"
            value={optimizedPrompt}
            onChange={(e) => setOptimizedPrompt(e.target.value)}
            disabled={isGenerating || isJobLocked || isManualMode}
            style={{ minHeight: '200px' }}
          />

          <select
            className="dropdown-btn"
            value={selectedImageModel}
            onChange={(e) => setSelectedImageModel(e.target.value)}
            disabled={isGenerating || isJobLocked || isManualMode}
          >
            <option value="">Choose Image Model</option>
            {imageModels.map((modelName) => (
              <option key={modelName} value={modelName}>{modelName}</option>
            ))}
          </select>

          <button
            className="action-btn"
            onClick={handleGenerateImages}
            disabled={isGenerating || isJobLocked || isManualMode || !selectedImageModel}
          >
            {isGenerating ? 'Generating Images...' : 'Generate Batch Images'}
          </button>
        </section>

        {/* ── COLUMN 2: QUALITY CONTROL ── */}
        <section className="column">
          <div className="column-header">PROCESSING & QUALITY CONTROL</div>

          {isManualMode ? (
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
                    <img src={uploadedImage} alt="Uploaded file" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />

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
            <div className="image-grid">
              {generatedImages.length === 0 && !isGenerating && (
                <p style={{ textAlign: 'center', width: '100%', color: '#888' }}>No images generated yet.</p>
              )}
              {isGenerating && (
                <p style={{ textAlign: 'center', width: '100%', color: '#888' }}>Running pipeline... Please wait.</p>
              )}

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
                    <img src={img.url} alt="Generated view" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
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

        {/* ── COLUMN 3: 3D OUTPUT ── */}
        <section className="column output-column">
          <div className="column-header">OUTPUT: Final 3D Model</div>

          <select
            className="dropdown-btn"
            value={selected3DModel}
            onChange={(e) => setSelected3DModel(e.target.value)}
            disabled={isJobLocked}
          >
            <option value="">Choose 3D Generator</option>
            {threeDModels.map((modelName) => (
              <option key={modelName} value={modelName}>{modelName}</option>
            ))}
          </select>

          <button
            className="action-btn"
            onClick={handleGenerate3DAsset}
            disabled={isGenerating3D || isJobLocked || !selectedImageBase64}
          >
            {isGenerating3D ? "Generating..." : "Generate 3D Asset"}
          </button>

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

          <button // VR button
            className="action-btn"
            style={{
              backgroundColor: modelUrl ? '#8a2be2' : '#6c757d',
              width: '100%',
              marginTop: '0.5rem',
              cursor: modelUrl ? 'pointer' : 'not-allowed',
              opacity: modelUrl ? 1 : 0.5
            }}
            onClick={() => setShowVR(true)}
            disabled={!modelUrl || isGenerating3D}
          >
             🥽 View Model in VR
          </button>

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

      {/* ── SAVE JOB MODAL ── */}
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

      {/* ── DISCREPANCY ANALYSIS MODAL ── */}
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
              <strong>Want to use this prompt?</strong> <br />
              Copy the text above, close this pop-up, and click "Save and start new job" for a fresh run.
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

      {/* ── VR VIEWER OVERLAY ── */}
      {showVR && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          zIndex: 9999, backgroundColor: '#000'
        }}>
          {/* Exit Button */}
          <button
            onClick={() => setShowVR(false)}
            style={{
              position: 'absolute', top: '20px', right: '20px', zIndex: 10000,
              padding: '10px 20px', backgroundColor: '#ff4444', color: 'white', 
              border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold'
            }}
          >
            EXIT VR MODE
          </button>

          <a-scene embedded>
            {/* 1. Direct Model Injection (No <a-assets> needed for Blobs) */}
            <a-entity
              gltf-model={modelUrl} 
              position="0 1.2 -3"
              scale="1 1 1"
              rotation="0 0 0"
              animation="property: rotation; to: 0 360 0; loop: true; dur: 20000; easing: linear"
            ></a-entity>

            {/* 2. Added Lighting (Essential! AI models often don't have built-in lights) */}
            <a-light type="ambient" color="#ffffff" intensity="0.8"></a-light>
            <a-light type="directional" position="1 4 3" intensity="0.6" castShadow="true"></a-light>

            {/* 3. The Environment */}
            <a-sky color="#121212"></a-sky>
            <a-grid position="0 0 0" rotation="-90 0 0" width="100" height="100" static-body></a-grid>
            
            <a-camera position="0 1.6 0">
              <a-cursor color="#FAFAFA"></a-cursor>
            </a-camera>
          </a-scene>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
