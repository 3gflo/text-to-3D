import { useState, useEffect } from 'react'

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
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>System Status</h1>
      <p>Current Status: <strong>{status}</strong></p>
    </div>
  )
}

export default App