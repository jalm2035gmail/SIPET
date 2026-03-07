import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import Button from '../components/Button'
import Table from '../components/Table'
import { djangoApi } from '../services/api_django'

function mapEstado(estado) {
  if (estado === 'aprobado') return 'Aprobado'
  if (estado === 'rechazado') return 'Rechazado'
  return 'Solicitado'
}

export default function CreditosList() {
  const [creditos, setCreditos] = useState([])
  const [scoringResumen, setScoringResumen] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const columns = useMemo(
    () => [
      { key: 'id', label: 'ID' },
      { key: 'socio', label: 'Socio' },
      { key: 'monto', label: 'Monto' },
      { key: 'plazo', label: 'Plazo' },
      { key: 'estado', label: 'Estado' },
      { key: 'fecha', label: 'Fecha' },
      { key: 'acciones', label: 'Acciones' }
    ],
    []
  )

  useEffect(() => {
    djangoApi
      .get('/analitica/ml/scoring/resumen/')
      .then((response) => {
        setScoringResumen(response.data || null)
      })
      .catch(() => {
        setScoringResumen(null)
      })

    djangoApi
      .get('/creditos/')
      .then((response) => {
        const rows = (response.data || []).map((credito) => ({
          id: credito.id,
          socio: credito.socio_nombre || `Socio #${credito.socio}`,
          monto: `$${Number(credito.monto).toFixed(2)}`,
          plazo: `${credito.plazo} meses`,
          estado: mapEstado(credito.estado),
          fecha: (credito.fecha_creacion || '').slice(0, 10),
          acciones: <Link to={`/web/creditos/${credito.id}`}>Ver detalle</Link>
        }))
        setCreditos(rows)
      })
      .catch(() => {
        setError('No se pudo cargar la lista de créditos.')
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <section className="creditos-page">
      <h1>Créditos</h1>
      <p>Solicitudes registradas en el sistema.</p>
      <div className="creditos-page__actions">
        <Link to="/web/creditos/nuevo">
          <Button variant="primary">Nueva solicitud</Button>
        </Link>
      </div>

      {scoringResumen ? (
        <div className="credito-form-page__scoring">
          <strong>Resumen de riesgo (scoring)</strong>
          <p>Total inferencias: {scoringResumen.total_inferencias}</p>
          <p>Score promedio: {Number(scoringResumen.score_promedio || 0).toFixed(2)}</p>
          <p>
            Riesgo:
            {' '}Bajo {scoringResumen.por_riesgo?.bajo || 0}
            {' | '}Medio {scoringResumen.por_riesgo?.medio || 0}
            {' | '}Alto {scoringResumen.por_riesgo?.alto || 0}
          </p>
          <p>
            Recomendación:
            {' '}Aprobar {scoringResumen.por_recomendacion?.aprobar || 0}
            {' | '}Evaluar {scoringResumen.por_recomendacion?.evaluar || 0}
            {' | '}Rechazar {scoringResumen.por_recomendacion?.rechazar || 0}
          </p>
        </div>
      ) : null}

      {loading ? <p className="creditos-page__status">Cargando...</p> : null}
      {error ? <p className="creditos-page__status creditos-page__status--error">{error}</p> : null}

      {!loading && !error ? <Table columns={columns} rows={creditos} /> : null}
    </section>
  )
}
