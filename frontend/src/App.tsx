import { useEffect, useState } from 'react'
import Layout from './components/Layout'

function App() {
  const [backendStatus, setBackendStatus] = useState<string>('connecting...')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => setBackendStatus(data.status))
      .catch(() => setBackendStatus('offline'))
  }, [])

  return <Layout backendStatus={backendStatus} />
}

export default App
