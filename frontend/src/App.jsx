import { useEffect, useState } from 'react'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

function App() {
  const [apiStatus, setApiStatus] = useState('Comprobando conexion...')

  useEffect(() => {
    const controller = new AbortController()

    async function checkApi() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/health/`, {
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error(`La API respondio con ${response.status}`)
        }

        const data = await response.json()
        setApiStatus(data.status === 'ok' ? 'API conectada' : 'Respuesta inesperada de la API')
      } catch (error) {
        if (error.name !== 'AbortError') {
          setApiStatus('No fue posible conectar con la API')
        }
      }
    }

    checkApi()
    return () => controller.abort()
  }, [])

  return (
    <main className="flex min-h-screen items-center justify-center bg-stone-50 px-6 text-stone-900">
      <section className="w-full max-w-xl rounded-2xl border border-stone-200 bg-white p-8 text-left shadow-sm">
        <p className="text-sm font-medium tracking-widest text-amber-700 uppercase">Alquimia Dulce</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight">Entorno configurado</h1>
        <p className="mt-4 text-stone-600">
          React, Tailwind, Django y PostgreSQL de Supabase estan listos para desarrollar.
        </p>
        <p className="mt-6 rounded-lg bg-stone-100 px-4 py-3 text-sm font-medium text-stone-700">
          Estado del backend: {apiStatus}
        </p>
      </section>
    </main>
  )
}

export default App
