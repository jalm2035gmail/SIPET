import { useEffect, useMemo, useState } from 'react'

import Table from '../components/Table'
import { djangoApi } from '../services/api_django'

function formatScore(value) {
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return '0%'
  return `${Math.round(numeric * 100)}%`
}

function clasificarPropension(value) {
  const numeric = Number(value)
  if (numeric >= 0.8) return 'Alta'
  if (numeric >= 0.5) return 'Media'
  return 'Baja'
}

export default function ProspectosList() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const columns = useMemo(
    () => [
      { key: 'nombre', label: 'Nombre' },
      { key: 'telefono', label: 'Teléfono' },
      { key: 'direccion', label: 'Dirección' },
      { key: 'fuente', label: 'Fuente' },
      { key: 'score', label: 'Score' },
      { key: 'propension', label: 'Propensión' }
    ],
    []
  )

  useEffect(() => {
    djangoApi
      .get('/prospectos/')
      .then((response) => {
        const mapped = (response.data || []).map((prospecto) => ({
          id: prospecto.id,
          nombre: prospecto.nombre,
          telefono: prospecto.telefono,
          direccion: prospecto.direccion,
          fuente: prospecto.fuente,
          score: formatScore(prospecto.score_propension),
          propension: clasificarPropension(prospecto.score_propension)
        }))
        setRows(mapped)
      })
      .catch(() => {
        setError('No se pudo cargar la lista de prospectos.')
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <section className="prospectos-page">
      <h1>Prospectos</h1>
      <p>Listado de potenciales socios para campañas de crecimiento.</p>

      {loading ? <p className="prospectos-page__status">Cargando...</p> : null}
      {error ? <p className="prospectos-page__status prospectos-page__status--error">{error}</p> : null}
      {!loading && !error ? <Table columns={columns} rows={rows} /> : null}
    </section>
  )
}
