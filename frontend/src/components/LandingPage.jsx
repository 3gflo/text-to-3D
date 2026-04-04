import React from 'react';
import './LandingPage.css';

import iconText from '../assets/icon-text.png';
import iconImage from '../assets/icon-image.png';
import iconClip from '../assets/icon-clip.png';
import icon3d from '../assets/icon-3d.png';

/**
 * Landing page shown before the user enters the dashboard.
 * Displays a high-level overview of the 4-step generation pipeline.
 *
 * @param {{ onStart: () => void }} props
 */
const LandingPage = ({ onStart }) => {
  return (
    <div className="landing-container">
      <header className="landing-header">
        <h1>Gulfstream Text to 3D Model Generator</h1>
      </header>

      <div className="hero-section">
        <h2 className="hero-title">
          Generate high quality <br /> 3D assets in minutes
        </h2>
        <p className="hero-subtitle">
          Powered by our autonomous AI pipeline with integrated CLIP-based
          quality control. No more bad generations.
        </p>
        <button className="start-btn" onClick={onStart}>
          Start Generating Now
        </button>
      </div>

      <div className="steps-container">
        <div className="step-item">
          <div className="icon-bubble">
            <img src={iconText} alt="Text Input" />
          </div>
          <div className="step-label">1. Text Input</div>
        </div>

        <div className="connector-line"></div>

        <div className="step-item">
          <div className="icon-bubble">
            <img src={iconImage} alt="2D Gen" />
          </div>
          <div className="step-label">2. AI 2D Image Generation</div>
        </div>

        <div className="connector-line"></div>

        <div className="step-item">
          <div className="icon-bubble">
            <img src={iconClip} alt="CLIP Check" />
          </div>
          <div className="step-label">3. Automated CLIP Check</div>
        </div>

        <div className="connector-line"></div>

        <div className="step-item">
          <div className="icon-bubble">
            <img src={icon3d} alt="3D Gen" />
          </div>
          <div className="step-label">4. 3D Model Generation</div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
