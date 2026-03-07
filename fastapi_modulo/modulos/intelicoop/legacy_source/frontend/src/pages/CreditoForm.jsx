import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import Button from '../components/Button'
import Card from '../components/Card'
import { djangoApi } from '../services/api_django'

const initialForm = {
  socio: '',
  monto: '',
  plazo: '',
  ingreso_mensual: '',
  deuda_actual: '',
  antiguedad_meses: '',
  estado: 'solicitado'
}

function getRiskBadge(riesgo) {
  if (riesgo === 'bajo') return { label: 'Bajo', tone: 'low' }
  if (riesgo === 'medio') return { label: 'Medio', tone: 'medium' }
  return { label: 'Alto', tone: 'high' }
}

export default function CreditoForm() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [socios, setSocios] = useState([])
  const [sociosLoading, setSociosLoading] = useState(true)
  const [sociosError, setSociosError] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [scoringLoading, setScoringLoading] = useState(false)
  const [scoringError, setScoringError] = useState('')
  const [scoring, setScoring] = useState(null)
  const preApproveSuggested = scoring && Number(scoring.score) > 0.8

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  useEffect(() => {
    djangoApi
      .get('/socios/')
      .then((response) => {
        setSocios(response.data || [])
      })
      .catch(() => {
        setSociosError('No se pudo cargar la lista de socios.')
      })
      .finally(() => setSociosLoading(false))
  }, [])

  useEffect(() => {
    const ingreso = Number(form.ingreso_mensual)
    const deuda = Number(form.deuda_actual)
    const antiguedad = Number(form.antiguedad_meses)
    const ready = ingreso > 0 && deuda >= 0 && antiguedad >= 0

    if (!ready) {
      setScoring(null)
      setScoringError('')
      setScoringLoading(false)
      return
    }

    const timer = setTimeout(() => {
      setScoringLoading(true)
      setScoringError('')

      djangoApi
        .post('/analitica/ml/scoring/evaluar/', {
          ingreso_mensual: ingreso,
          deuda_actual: deuda,
          antiguedad_meses: antiguedad
        })
        .then((response) => {
          setScoring(response.data)
        })
        .catch(() => {
          setScoring(null)
          setScoringError('No se pudo calcular el score en este momento.')
        })
        .finally(() => setScoringLoading(false))
    }, 350)

    return () => clearTimeout(timer)
  }, [form.ingreso_mensual, form.deuda_actual, form.antiguedad_meses])

  const handleSubmit = (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')

    const payload = {
      socio: Number(form.socio),
      monto: Number(form.monto),
      plazo: Number(form.plazo),
      ingreso_mensual: Number(form.ingreso_mensual),
      deuda_actual: Number(form.deuda_actual),
      antiguedad_meses: Number(form.antiguedad_meses),
      estado: form.estado
    }

    djangoApi
      .post('/creditos/', payload)
      .then((response) => {
        const creditoCreado = response?.data || {}
        const persistPromise = scoring
          ? djangoApi.post('/analitica/ml/scoring/evaluar/', {
              persist: true,
              solicitud_id: `credito_${creditoCreado.id || Date.now()}`,
              credito: creditoCreado.id || null,
              socio: payload.socio,
              ingreso_mensual: payload.ingreso_mensual,
              deuda_actual: payload.deuda_actual,
              antiguedad_meses: payload.antiguedad_meses,
              model_version: 'weighted_score_v1'
            })
          : Promise.resolve()

        persistPromise
          .catch(() => {
            // No bloquea la operación principal de crédito.
          })
          .finally(() => {
            navigate('/web/creditos')
          })
      })
      .catch((apiError) => {
        const responseError = apiError?.response?.data
        if (responseError && typeof responseError === 'object') {
          const firstKey = Object.keys(responseError)[0]
          const message = Array.isArray(responseError[firstKey])
            ? responseError[firstKey][0]
            : responseError[firstKey]
          setError(String(message))
          return
        }
        setError('No se pudo crear la solicitud de crédito.')
      })
      .finally(() => setLoading(false))
  }

  return (
    <section className="credito-form-page">
      <h1>Nueva solicitud de crédito</h1>
      <p>Completa los datos mínimos para registrar la solicitud.</p>

      <Card>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="socio">Socio</label>
          <select
            id="socio"
            name="socio"
            value={form.socio}
            onChange={handleChange}
            required
            disabled={sociosLoading || socios.length === 0}
          >
            <option value="">{sociosLoading ? 'Cargando socios...' : 'Selecciona un socio'}</option>
            {socios.map((socio) => (
              <option key={socio.id} value={socio.id}>
                {socio.nombre} ({socio.email})
              </option>
            ))}
          </select>
          {sociosError ? <p className="credito-form-page__error">{sociosError}</p> : null}

          <label htmlFor="monto">Monto</label>
          <input
            id="monto"
            name="monto"
            type="number"
            step="0.01"
            min="0.01"
            value={form.monto}
            onChange={handleChange}
            required
          />

          <label htmlFor="plazo">Plazo (meses)</label>
          <input
            id="plazo"
            name="plazo"
            type="number"
            min="1"
            value={form.plazo}
            onChange={handleChange}
            required
          />

          <label htmlFor="ingreso_mensual">Ingreso mensual</label>
          <input
            id="ingreso_mensual"
            name="ingreso_mensual"
            type="number"
            step="0.01"
            min="0.01"
            value={form.ingreso_mensual}
            onChange={handleChange}
            required
          />

          <label htmlFor="deuda_actual">Deuda actual</label>
          <input
            id="deuda_actual"
            name="deuda_actual"
            type="number"
            step="0.01"
            min="0"
            value={form.deuda_actual}
            onChange={handleChange}
            required
          />

          <label htmlFor="antiguedad_meses">Antigüedad (meses)</label>
          <input
            id="antiguedad_meses"
            name="antiguedad_meses"
            type="number"
            min="0"
            value={form.antiguedad_meses}
            onChange={handleChange}
            required
          />

          <div className="credito-form-page__scoring">
            <strong>Scoring</strong>
            {scoringLoading ? <p>Calculando score...</p> : null}
            {scoring ? (
              <div className="credito-form-page__scoring-result">
                <p>Score: {scoring.score}</p>
                <p>Recomendación: {scoring.recomendacion}</p>
                <p>
                  Riesgo:
                  <span className={`risk-badge risk-badge--${getRiskBadge(scoring.riesgo).tone}`}>
                    {getRiskBadge(scoring.riesgo).label}
                  </span>
                </p>
              </div>
            ) : null}
            {preApproveSuggested ? (
              <p className="credito-form-page__hint">
                Sugerencia: score alto detectado. Se recomienda preaprobación automática.
              </p>
            ) : null}
            {scoringError ? <p className="credito-form-page__error">{scoringError}</p> : null}
          </div>

          {error ? <p className="credito-form-page__error">{error}</p> : null}

          <div className="auth-actions">
            <Button type="submit" variant="primary" disabled={loading}>
              {loading ? 'Guardando...' : 'Guardar solicitud'}
            </Button>
            <Link to="/web/creditos">Cancelar</Link>
          </div>
        </form>
      </Card>
    </section>
  )
}
