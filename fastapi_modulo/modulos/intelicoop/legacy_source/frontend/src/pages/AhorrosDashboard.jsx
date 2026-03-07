import { useEffect, useMemo, useState } from 'react'

import Card from '../components/Card'
import PieChart from '../components/PieChart'
import { djangoApi } from '../services/api_django'

function calcularDistribucionSegmentos(socios) {
  const conteo = { hormiga: 0, gran_ahorrador: 0, inactivo: 0 }
  socios.forEach((s) => {
    if (conteo[s.segmento] !== undefined) conteo[s.segmento] += 1
  })
  return conteo
}

export default function AhorrosDashboard() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [kpis, setKpis] = useState({
    cuentas: 0,
    movimientos: 0,
    captacion: 0
  })
  const [segmentos, setSegmentos] = useState({ hormiga: 0, gran_ahorrador: 0, inactivo: 0 })

  const chartData = useMemo(
    () => [
      { label: '🐜 Hormiga', value: segmentos.hormiga, color: '#0b7285' },
      { label: '🐘 Gran Ahorrador', value: segmentos.gran_ahorrador, color: '#16a34a' },
      { label: '💤 Inactivo', value: segmentos.inactivo, color: '#b45309' }
    ],
    [segmentos]
  )

  useEffect(() => {
    Promise.all([djangoApi.get('/ahorros/cuentas/'), djangoApi.get('/ahorros/movimientos/'), djangoApi.get('/socios/')])
      .then(([cuentasRes, movsRes, sociosRes]) => {
        const cuentas = cuentasRes.data || []
        const movimientos = movsRes.data || []
        const socios = sociosRes.data || []

        const captacion = cuentas.reduce((acc, c) => acc + Number(c.saldo || 0), 0)
        setKpis({
          cuentas: cuentas.length,
          movimientos: movimientos.length,
          captacion
        })
        setSegmentos(calcularDistribucionSegmentos(socios))
      })
      .catch(() => {
        setError('No se pudo cargar el dashboard de ahorros.')
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <section className="ahorros-page">
      <h1>Ahorros y Segmentación</h1>
      <p>KPIs de captación y distribución de segmentos.</p>

      {loading ? <p className="ahorros-page__status">Cargando...</p> : null}
      {error ? <p className="ahorros-page__status ahorros-page__status--error">{error}</p> : null}

      {!loading && !error ? (
        <>
          <div className="kpi-grid">
            <Card title="Cuentas de ahorro">{kpis.cuentas}</Card>
            <Card title="Movimientos">{kpis.movimientos}</Card>
            <Card title="Captación total">${kpis.captacion.toFixed(2)}</Card>
          </div>

          <Card title="Distribución de segmentos">
            <div className="ahorros-page__chart">
              <PieChart slices={chartData} />
            </div>
          </Card>
        </>
      ) : null}
    </section>
  )
}
