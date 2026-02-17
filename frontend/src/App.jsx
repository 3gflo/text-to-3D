import { useState, useEffect, React } from 'react'
import Dashboard from './components/Dashboard'
import LandingPage from './components/LandingPage'

function App() {
  // State to track which page is visible. Options: 'landing' or 'dashboard'
  const [currentPage, setCurrentPage] = useState('landing');

  return (
    <div>
      {currentPage === 'landing' && (
        <LandingPage onStart={() => setCurrentPage('dashboard')} />
      )}

      {currentPage === 'dashboard' && (
        <Dashboard />
      )}
    </div>
  );
}

export default App;