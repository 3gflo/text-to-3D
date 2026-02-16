import { useState, useEffect, React } from 'react'
import Dashboard from './components/Dashboard'

function App() {
  const [status, setStatus] = useState('Loading...')

  useEffect(() => {
    // The proxy directs this to http://127.0.0.1:5000/api/health
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => {
        console.log("Backend responded:", data)
        setStatus(`Backend is ${data.status}`)
      })
      .catch((err) => {
        console.error("Error connecting:", err)
        setStatus('Error connecting to backend')
      })
  }, [])

  return (
      <div>
        <Dashboard />
      </div>
  );
}

export default App