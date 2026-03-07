import { useEffect, useMemo, useState } from 'react'

import ProductoRecomendado from '../components/ProductoRecomendado'
import Table from '../components/Table'
import { djangoApi } from '../services/api_django'

function renderSegmento(segmento) {
  if (segmento === 'hormiga') return '🐜 Ahorrador Hormiga'
  if (segmento === 'gran_ahorrador') return '🐘 Gran Ahorrador'
  return '💤 Inactivo'
}

export default function SociosList() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const columns = useMemo(
    () => [
      { key: 'nombre', label: 'Nombre' },
      { key: 'email', label: 'Email' },
      { key: 'telefono', label: 'Teléfono' },
      { key: 'segmento', label: 'Segmento' },
      { key: 'producto', label: 'Producto recomendado' }
    ],
    []
  )

  useEffect(() => {
    djangoApi
      .get('/socios/')
      .then((response) => {
        const mapped = (response.data || []).map((socio) => ({
          id: socio.id,
          nombre: socio.nombre,
          email: socio.email,
          telefono: socio.telefono,
          segmento: renderSegmento(socio.segmento),
          producto: <ProductoRecomendado segmento={socio.segmento} />
        }))
        setRows(mapped)
      })
      .catch(() => {
        setError('No se pudo cargar la lista de socios.')
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <section className="socios-page">
      <h1>Socios</h1>
      <p>Vista de segmentación para acciones de captación.</p>

      {loading ? <p className="socios-page__status">Cargando...</p> : null}
      {error ? <p className="socios-page__status socios-page__status--error">{error}</p> : null}

      {!loading && !error ? <Table columns={columns} rows={rows} /> : null}
    </section>
  )
}
