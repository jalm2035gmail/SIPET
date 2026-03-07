import { useEffect, useState } from 'react'

import Card from '../components/Card'
import { djangoApi } from '../services/api_django'

function semaforoClassName(value) {
  if (value === 'Rojo') return 'semaforo-pill semaforo-pill--rojo'
  if (value === 'Amarillo') return 'semaforo-pill semaforo-pill--amarillo'
  return 'semaforo-pill semaforo-pill--verde'
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('es-MX', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatTrendItems(series = []) {
  return (series || [])
    .map((item) => `${item.periodo}: ${Number(item.valor || 0).toFixed(2)}`)
    .join(' | ')
}

export default function Dashboards18() {
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [loadingTableros, setLoadingTableros] = useState(true)
  const [error, setError] = useState('')
  const [resumen, setResumen] = useState({ total: 0, rojo: 0, amarillo: 0, verde: 0 })
  const [semaforos, setSemaforos] = useState([])
  const [tableros, setTableros] = useState(null)
  const [actualizacion, setActualizacion] = useState(null)
  const [drilldown, setDrilldown] = useState(null)
  const [drilldownLoading, setDrilldownLoading] = useState(false)
  const [drilldownError, setDrilldownError] = useState('')
  const [sucursalSeleccionada, setSucursalSeleccionada] = useState('')
  const [acceso, setAcceso] = useState({ vista: 'consejo_gerencia', drilldown_habilitado: true })
  const [filtroSemaforo, setFiltroSemaforo] = useState('')
  const [filtroAmbito, setFiltroAmbito] = useState('')
  const [filtroTexto, setFiltroTexto] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    const params = {}
    if (filtroSemaforo) params.semaforo = filtroSemaforo
    if (filtroAmbito) params.ambito = filtroAmbito
    if (filtroTexto.trim()) params.q = filtroTexto.trim()

    djangoApi
      .get('/analitica/ml/dashboard/semaforos/', { params })
      .then((res) => {
        setResumen(res?.data?.resumen || { total: 0, rojo: 0, amarillo: 0, verde: 0 })
        setSemaforos(res?.data?.semaforos || [])
        if (res?.data?.actualizacion) setActualizacion(res.data.actualizacion)
        if (res?.data?.acceso) setAcceso(res.data.acceso)
      })
      .catch(() => {
        setError('No se pudo cargar el dashboard ejecutivo-operativo (1.8).')
      })
      .finally(() => setLoading(false))
  }, [filtroSemaforo, filtroAmbito, filtroTexto])

  useEffect(() => {
    setLoadingTableros(true)
    djangoApi
      .get('/analitica/ml/dashboard/ejecutivos-operativos/')
      .then((res) => {
        setTableros(res?.data || null)
        if (res?.data?.actualizacion) setActualizacion(res.data.actualizacion)
        if (res?.data?.acceso) setAcceso(res.data.acceso)
      })
      .catch(() => {
        setError('No se pudieron cargar los tableros ejecutivos (1.8).')
      })
      .finally(() => setLoadingTableros(false))
  }, [])

  const descargarCsv = () => {
    setExporting(true)
    const params = { export: 'csv' }
    if (filtroSemaforo) params.semaforo = filtroSemaforo
    if (filtroAmbito) params.ambito = filtroAmbito
    if (filtroTexto.trim()) params.q = filtroTexto.trim()

    djangoApi
      .get('/analitica/ml/dashboard/semaforos/', { params, responseType: 'blob' })
      .then((res) => {
        const blobUrl = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv;charset=utf-8;' }))
        const link = document.createElement('a')
        link.href = blobUrl
        link.setAttribute('download', 'dashboard_semaforos.csv')
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(blobUrl)
      })
      .catch(() => {
        setError('No se pudo exportar el CSV del dashboard.')
      })
      .finally(() => setExporting(false))
  }

  const cargarDrilldownSucursal = (sucursal) => {
    setSucursalSeleccionada(sucursal)
    setDrilldownLoading(true)
    setDrilldownError('')
    djangoApi
      .get('/analitica/ml/dashboard/ejecutivos-operativos/', { params: { sucursal, detalle: 1 } })
      .then((res) => {
        setDrilldown(res?.data?.drilldown || null)
      })
      .catch(() => {
        setDrilldownError('No se pudo cargar el detalle operativo de la sucursal.')
        setDrilldown(null)
      })
      .finally(() => setDrilldownLoading(false))
  }

  return (
    <section className="dashboards18-page">
      <h1>Dashboards Ejecutivos y Operativos (1.8)</h1>
      <p>Semaforizacion de alertas activas para cartera, colocacion, captacion, riesgo y cobranza.</p>
      <p className="dashboards18-page__updated-at">
        Ultima actualizacion:{' '}
        {actualizacion?.ultima_actualizacion_utc ? formatDate(actualizacion.ultima_actualizacion_utc) : 'Sin registro'}
      </p>

      {loading ? <p className="dashboards18-page__status">Cargando...</p> : null}
      {error ? <p className="dashboards18-page__status dashboards18-page__status--error">{error}</p> : null}

      {!loading && !error ? (
        <>
          {loadingTableros ? <p className="dashboards18-page__status">Cargando tableros...</p> : null}

          {!loadingTableros && tableros ? (
            <div className="dashboards18-page__boards">
              <Card title="Salud de cartera">
                <div className="dashboards18-page__metrics">
                  <p>Cartera total: ${Number(tableros?.salud_cartera?.cartera_total || 0).toFixed(2)}</p>
                  <p>Cartera vigente: ${Number(tableros?.salud_cartera?.cartera_vigente || 0).toFixed(2)}</p>
                  <p>Cartera vencida: ${Number(tableros?.salud_cartera?.cartera_vencida_estimada || 0).toFixed(2)}</p>
                  <p>IMOR: {Number(tableros?.salud_cartera?.imor_pct || 0).toFixed(2)}%</p>
                  <p>Meta IMOR: {Number(tableros?.salud_cartera?.meta_imor_pct || 0).toFixed(2)}%</p>
                  <p className="dashboards18-page__trend">
                    Tendencia mensual: {formatTrendItems(tableros?.tendencias?.mensual?.salud_cartera_imor_pct)}
                  </p>
                  <p className="dashboards18-page__trend">
                    Tendencia trimestral: {formatTrendItems(tableros?.tendencias?.trimestral?.salud_cartera_imor_pct)}
                  </p>
                </div>
              </Card>

              <Card title="Colocación">
                <div className="dashboards18-page__metrics">
                  <p>Meta 30d: ${Number(tableros?.colocacion?.meta_colocacion_30d || 0).toFixed(2)}</p>
                  <p>Real 30d: ${Number(tableros?.colocacion?.colocacion_real_30d || 0).toFixed(2)}</p>
                  <p>Cumplimiento: {Number(tableros?.colocacion?.cumplimiento_meta_pct || 0).toFixed(2)}%</p>
                  <p>Embudo (sol/apr/rech): {tableros?.colocacion?.embudo_solicitados || 0}/{tableros?.colocacion?.embudo_aprobados || 0}/{tableros?.colocacion?.embudo_rechazados || 0}</p>
                  <p>Tiempo respuesta: {Number(tableros?.colocacion?.tiempo_respuesta_promedio_h || 0).toFixed(2)} h</p>
                  <p className="dashboards18-page__trend">
                    Tendencia mensual: {formatTrendItems(tableros?.tendencias?.mensual?.colocacion_monto)}
                  </p>
                  <p className="dashboards18-page__trend">
                    Tendencia trimestral: {formatTrendItems(tableros?.tendencias?.trimestral?.colocacion_monto)}
                  </p>
                </div>
              </Card>

              <Card title="Captación">
                <div className="dashboards18-page__metrics">
                  <p>Depósitos 30d: ${Number(tableros?.captacion?.depositos_30d || 0).toFixed(2)}</p>
                  <p>Retiros 30d: ${Number(tableros?.captacion?.retiros_30d || 0).toFixed(2)}</p>
                  <p>Crecimiento neto: ${Number(tableros?.captacion?.crecimiento_neto_30d || 0).toFixed(2)}</p>
                  <p>Estabilidad ahorro: {Number(tableros?.captacion?.estabilidad_ahorro_pct || 0).toFixed(2)}%</p>
                  <p>Meta estabilidad: {Number(tableros?.captacion?.meta_estabilidad_ahorro_pct || 0).toFixed(2)}%</p>
                  <p className="dashboards18-page__trend">
                    Tendencia mensual: {formatTrendItems(tableros?.tendencias?.mensual?.captacion_neto)}
                  </p>
                  <p className="dashboards18-page__trend">
                    Tendencia trimestral: {formatTrendItems(tableros?.tendencias?.trimestral?.captacion_neto)}
                  </p>
                </div>
              </Card>

              {tableros?.riesgo ? (
                <Card title="Riesgo">
                  <div className="dashboards18-page__metrics">
                    <p>Cobertura: {Number(tableros?.riesgo?.cobertura_pct || 0).toFixed(2)}%</p>
                    <p>Meta cobertura: {Number(tableros?.riesgo?.meta_cobertura_pct || 0).toFixed(2)}%</p>
                    <p>Provisiones: ${Number(tableros?.riesgo?.provisiones_estimadas || 0).toFixed(2)}</p>
                    {'castigos_estimados' in (tableros?.riesgo || {}) ? (
                      <p>Castigos: ${Number(tableros?.riesgo?.castigos_estimados || 0).toFixed(2)}</p>
                    ) : null}
                    <p className="dashboards18-page__trend">
                      Tendencia mensual: {formatTrendItems(tableros?.tendencias?.mensual?.riesgo_cobertura_pct)}
                    </p>
                    <p className="dashboards18-page__trend">
                      Tendencia trimestral: {formatTrendItems(tableros?.tendencias?.trimestral?.riesgo_cobertura_pct)}
                    </p>
                  </div>
                </Card>
              ) : null}

              <Card title="Sucursales">
                <div className="ui-table-wrap">
                  <table className="ui-table">
                    <thead>
                      <tr>
                        <th>Ranking</th>
                        <th>Sucursal</th>
                        <th>Colocación 30d</th>
                        <th>Alertas mora</th>
                        {acceso?.drilldown_habilitado ? <th>Drill-down</th> : null}
                      </tr>
                    </thead>
                    <tbody>
                      {(tableros?.sucursales || []).map((row) => (
                        <tr key={row.sucursal}>
                          <td>{row.ranking}</td>
                          <td>{row.sucursal}</td>
                          <td>${Number(row.colocacion_30d || 0).toFixed(2)}</td>
                          <td>{row.alertas_mora}</td>
                          {acceso?.drilldown_habilitado ? (
                            <td>
                              <button
                                type="button"
                                className="ui-button ui-button--ghost"
                                onClick={() => cargarDrilldownSucursal(row.sucursal)}
                              >
                                Ver detalle
                              </button>
                            </td>
                          ) : null}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {acceso?.drilldown_habilitado && (drilldownLoading || drilldown || drilldownError) && (
                <Card title={`Detalle operativo - ${sucursalSeleccionada || 'Sucursal'}`}>
                  {drilldownLoading ? <p className="dashboards18-page__status">Cargando detalle...</p> : null}
                  {drilldownError ? <p className="dashboards18-page__status dashboards18-page__status--error">{drilldownError}</p> : null}
                  {!drilldownLoading && !drilldownError && drilldown ? (
                    <div className="dashboards18-page__drilldown">
                      <p>Socios en sucursal: {drilldown.total_socios || 0}</p>

                      <h3>Créditos recientes</h3>
                      <div className="ui-table-wrap">
                        <table className="ui-table">
                          <thead>
                            <tr>
                              <th>Crédito</th>
                              <th>Socio</th>
                              <th>Monto</th>
                              <th>Estado</th>
                              <th>Fecha</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(drilldown.creditos_recientes || []).length === 0 ? (
                              <tr>
                                <td colSpan={5} className="ui-table__empty">
                                  Sin créditos recientes.
                                </td>
                              </tr>
                            ) : (
                              (drilldown.creditos_recientes || []).map((row) => (
                                <tr key={`cred-${row.credito_id}`}>
                                  <td>{row.credito_id}</td>
                                  <td>{row.socio_nombre}</td>
                                  <td>${Number(row.monto || 0).toFixed(2)}</td>
                                  <td>{row.estado}</td>
                                  <td>{formatDate(row.fecha_creacion)}</td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>

                      <h3>Alertas de mora</h3>
                      <div className="ui-table-wrap">
                        <table className="ui-table">
                          <thead>
                            <tr>
                              <th>Crédito</th>
                              <th>Socio</th>
                              <th>Alerta</th>
                              <th>Prob. mora 90d</th>
                              <th>Fecha</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(drilldown.alertas_mora || []).length === 0 ? (
                              <tr>
                                <td colSpan={5} className="ui-table__empty">
                                  Sin alertas de mora.
                                </td>
                              </tr>
                            ) : (
                              (drilldown.alertas_mora || []).map((row) => (
                                <tr key={`alt-${row.credito_id}-${row.socio_id}`}>
                                  <td>{row.credito_id}</td>
                                  <td>{row.socio_nombre}</td>
                                  <td>{row.alerta}</td>
                                  <td>{Number(row.prob_mora_90d || 0).toFixed(4)}</td>
                                  <td>{formatDate(row.fecha_creacion)}</td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : null}
                </Card>
              )}

              {tableros?.eficiencia_cobranza ? (
                <Card title="Eficiencia de cobranza">
                  <div className="dashboards18-page__metrics">
                    <p>Gestiones: {tableros?.eficiencia_cobranza?.gestiones_total || 0}</p>
                    <p>Con recuperación: {tableros?.eficiencia_cobranza?.gestiones_con_recuperacion || 0}</p>
                    <p>Eficiencia: {Number(tableros?.eficiencia_cobranza?.eficiencia_cobranza_pct || 0).toFixed(2)}%</p>
                    <p>Meta eficiencia: {Number(tableros?.eficiencia_cobranza?.meta_eficiencia_cobranza_pct || 0).toFixed(2)}%</p>
                    <p>Recuperación/gestión: ${Number(tableros?.eficiencia_cobranza?.recuperacion_por_gestion || 0).toFixed(2)}</p>
                    <p className="dashboards18-page__trend">
                      Tendencia mensual: {formatTrendItems(tableros?.tendencias?.mensual?.cobranza_eficiencia_pct)}
                    </p>
                    <p className="dashboards18-page__trend">
                      Tendencia trimestral: {formatTrendItems(tableros?.tendencias?.trimestral?.cobranza_eficiencia_pct)}
                    </p>
                  </div>
                </Card>
              ) : null}
            </div>
          ) : null}

          <Card title="Filtros operativos">
            <div className="dashboards18-page__filters">
              <label>
                Semaforo
                <select value={filtroSemaforo} onChange={(e) => setFiltroSemaforo(e.target.value)}>
                  <option value="">Todos</option>
                  <option value="Rojo">Rojo</option>
                  <option value="Amarillo">Amarillo</option>
                  <option value="Verde">Verde</option>
                </select>
              </label>

              <label>
                Ambito
                <select value={filtroAmbito} onChange={(e) => setFiltroAmbito(e.target.value)}>
                  <option value="">Todos</option>
                  <option value="riesgo">Riesgo</option>
                  <option value="cobranza">Cobranza</option>
                  <option value="captacion">Captacion</option>
                  <option value="colocacion">Colocacion</option>
                  <option value="cartera">Cartera</option>
                </select>
              </label>

              <label>
                Buscar
                <input
                  value={filtroTexto}
                  onChange={(e) => setFiltroTexto(e.target.value)}
                  placeholder="metrica o componente"
                />
              </label>
            </div>
            <div className="dashboards18-page__actions">
              <button type="button" className="ui-button ui-button--secondary" onClick={descargarCsv} disabled={exporting}>
                {exporting ? 'Exportando...' : 'Exportar CSV'}
              </button>
            </div>
          </Card>

          <div className="dashboards18-page__kpis">
            <Card title="Total semaforos">
              <div className="kpi-value">{resumen.total}</div>
            </Card>
            <Card title="Rojo">
              <div className="kpi-value dashboards18-page__kpi dashboards18-page__kpi--rojo">{resumen.rojo}</div>
            </Card>
            <Card title="Amarillo">
              <div className="kpi-value dashboards18-page__kpi dashboards18-page__kpi--amarillo">
                {resumen.amarillo}
              </div>
            </Card>
            <Card title="Verde">
              <div className="kpi-value dashboards18-page__kpi dashboards18-page__kpi--verde">{resumen.verde}</div>
            </Card>
          </div>

          <Card title="Detalle de semaforos">
            <div className="ui-table-wrap">
              <table className="ui-table">
                <thead>
                  <tr>
                    <th>Componente</th>
                    <th>Ambito</th>
                    <th>Semaforo</th>
                    <th>Estado</th>
                    <th>Valor</th>
                    <th>Umbral</th>
                    <th>Fecha evento</th>
                  </tr>
                </thead>
                <tbody>
                  {semaforos.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="ui-table__empty">
                        Sin alertas activas.
                      </td>
                    </tr>
                  ) : (
                    semaforos.map((row) => (
                      <tr key={row.componente}>
                        <td>{row.componente}</td>
                        <td>{row.ambito || '-'}</td>
                        <td>
                          <span className={semaforoClassName(row.semaforo)}>{row.semaforo}</span>
                        </td>
                        <td>{row.estado || '-'}</td>
                        <td>{row?.detalle?.valor ?? '-'}</td>
                        <td>{row?.detalle?.umbral ?? '-'}</td>
                        <td>{formatDate(row?.detalle?.fecha_evento)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      ) : null}
    </section>
  )
}
