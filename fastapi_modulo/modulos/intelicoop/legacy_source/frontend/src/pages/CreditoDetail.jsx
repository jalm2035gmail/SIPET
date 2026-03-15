import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import Card from '../components/Card'
import Table from '../components/Table'
import { djangoApi } from '../services/api_django'

function formatMoney(value) {
  return `$${Number(value || 0).toFixed(2)}`
}

export default function CreditoDetail() {
  const navigate = useNavigate()
  const { id } = useParams()
  const [credito, setCredito] = useState(null)
  const [pagos, setPagos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [paymentForm, setPaymentForm] = useState({ fecha: '', monto: '' })
  const [savingPayment, setSavingPayment] = useState(false)
  const [paymentError, setPaymentError] = useState('')
  const [paymentMessage, setPaymentMessage] = useState('')
  const [estadoForm, setEstadoForm] = useState('solicitado')
  const [savingEstado, setSavingEstado] = useState(false)
  const [estadoError, setEstadoError] = useState('')
  const [estadoMessage, setEstadoMessage] = useState('')
  const [deletingCredito, setDeletingCredito] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  const paymentColumns = useMemo(
    () => [
      { key: 'fecha', label: 'Fecha' },
      { key: 'monto', label: 'Monto' }
    ],
    []
  )

  useEffect(() => {
    let mounted = true

    Promise.all([djangoApi.get(`/creditos/${id}/`), djangoApi.get('/creditos/pagos/')])
      .then(([creditoResponse, pagosResponse]) => {
        if (!mounted) return
        setCredito(creditoResponse.data)
        const filtered = (pagosResponse.data || [])
          .filter((pago) => Number(pago.credito) === Number(id))
          .map((pago) => ({
            id: pago.id,
            fecha: pago.fecha,
            monto: formatMoney(pago.monto)
          }))
        setPagos(filtered)
        setEstadoForm(creditoResponse.data.estado || 'solicitado')
      })
      .catch(() => {
        if (!mounted) return
        setError('No se pudo cargar el detalle del crédito.')
      })
      .finally(() => {
        if (!mounted) return
        setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [id])

  const handlePaymentChange = (event) => {
    const { name, value } = event.target
    setPaymentForm((prev) => ({ ...prev, [name]: value }))
  }

  const handlePaymentSubmit = (event) => {
    event.preventDefault()
    setSavingPayment(true)
    setPaymentError('')
    setPaymentMessage('')

    djangoApi
      .post('/creditos/pagos/', {
        credito: Number(id),
        fecha: paymentForm.fecha,
        monto: Number(paymentForm.monto)
      })
      .then((response) => {
        const newPago = response.data
        setPagos((prev) => [
          {
            id: newPago.id,
            fecha: newPago.fecha,
            monto: formatMoney(newPago.monto)
          },
          ...prev
        ])
        setPaymentForm({ fecha: '', monto: '' })
        setPaymentMessage('Pago registrado correctamente.')
      })
      .catch((apiError) => {
        const responseError = apiError?.response?.data
        if (responseError && typeof responseError === 'object') {
          const firstKey = Object.keys(responseError)[0]
          const message = Array.isArray(responseError[firstKey])
            ? responseError[firstKey][0]
            : responseError[firstKey]
          setPaymentError(String(message))
          return
        }
        setPaymentError('No se pudo registrar el pago.')
      })
      .finally(() => setSavingPayment(false))
  }

  const handleEstadoSubmit = (event) => {
    event.preventDefault()
    setSavingEstado(true)
    setEstadoError('')
    setEstadoMessage('')

    djangoApi
      .patch(`/creditos/${id}/`, { estado: estadoForm })
      .then((response) => {
        setCredito(response.data)
        setEstadoMessage('Estado actualizado correctamente.')
      })
      .catch((apiError) => {
        const responseError = apiError?.response?.data
        if (responseError && typeof responseError === 'object') {
          const firstKey = Object.keys(responseError)[0]
          const message = Array.isArray(responseError[firstKey])
            ? responseError[firstKey][0]
            : responseError[firstKey]
          setEstadoError(String(message))
          return
        }
        setEstadoError('No se pudo actualizar el estado.')
      })
      .finally(() => setSavingEstado(false))
  }

  const handleDeleteCredito = () => {
    const confirmed = window.confirm('Esta acción eliminará la solicitud de crédito. ¿Deseas continuar?')
    if (!confirmed) return

    setDeletingCredito(true)
    setDeleteError('')

    djangoApi
      .delete(`/creditos/${id}/`)
      .then(() => {
        navigate('/backend/creditos')
      })
      .catch(() => {
        setDeleteError('No se pudo eliminar la solicitud.')
      })
      .finally(() => setDeletingCredito(false))
  }

  return (
    <section className="credito-detail-page">
      <h1>Detalle de crédito #{id}</h1>
      <p>Consulta de solicitud e historial de pagos.</p>

      {loading ? <p className="credito-detail-page__status">Cargando...</p> : null}
      {error ? <p className="credito-detail-page__status credito-detail-page__status--error">{error}</p> : null}

      {!loading && !error && credito ? (
        <>
          <Card title="Datos de la solicitud">
            <div className="credito-detail-page__grid">
              <div>
                <strong>Socio:</strong> {credito.socio_nombre || `#${credito.socio}`}
              </div>
              <div>
                <strong>Monto:</strong> {formatMoney(credito.monto)}
              </div>
              <div>
                <strong>Plazo:</strong> {credito.plazo} meses
              </div>
              <div>
                <strong>Estado:</strong> {credito.estado}
              </div>
              <div>
                <strong>Ingreso mensual:</strong> {formatMoney(credito.ingreso_mensual)}
              </div>
              <div>
                <strong>Deuda actual:</strong> {formatMoney(credito.deuda_actual)}
              </div>
            </div>
          </Card>

          <Card title="Historial de pagos">
            <Table columns={paymentColumns} rows={pagos} />
          </Card>

          <Card title="Actualizar estado">
            <form className="auth-form" onSubmit={handleEstadoSubmit}>
              <label htmlFor="estado">Estado</label>
              <select id="estado" name="estado" value={estadoForm} onChange={(e) => setEstadoForm(e.target.value)}>
                <option value="solicitado">Solicitado</option>
                <option value="aprobado">Aprobado</option>
                <option value="rechazado">Rechazado</option>
              </select>

              {estadoError ? <p className="credito-detail-page__status credito-detail-page__status--error">{estadoError}</p> : null}
              {estadoMessage ? <p className="credito-detail-page__status credito-detail-page__status--ok">{estadoMessage}</p> : null}

              <div className="auth-actions">
                <button type="submit" className="ui-button ui-button--secondary" disabled={savingEstado}>
                  {savingEstado ? 'Guardando...' : 'Actualizar estado'}
                </button>
              </div>
            </form>
          </Card>

          <Card title="Registrar pago">
            <form className="auth-form" onSubmit={handlePaymentSubmit}>
              <label htmlFor="fecha">Fecha</label>
              <input
                id="fecha"
                name="fecha"
                type="date"
                value={paymentForm.fecha}
                onChange={handlePaymentChange}
                required
              />

              <label htmlFor="monto">Monto</label>
              <input
                id="monto"
                name="monto"
                type="number"
                min="0.01"
                step="0.01"
                value={paymentForm.monto}
                onChange={handlePaymentChange}
                required
              />

              {paymentError ? <p className="credito-detail-page__status credito-detail-page__status--error">{paymentError}</p> : null}
              {paymentMessage ? <p className="credito-detail-page__status credito-detail-page__status--ok">{paymentMessage}</p> : null}

              <div className="auth-actions">
                <button type="submit" className="ui-button ui-button--primary" disabled={savingPayment}>
                  {savingPayment ? 'Guardando...' : 'Registrar pago'}
                </button>
              </div>
            </form>
          </Card>

          <div className="credito-detail-page__actions">
            {deleteError ? <p className="credito-detail-page__status credito-detail-page__status--error">{deleteError}</p> : null}
            <button
              type="button"
              className="ui-button ui-button--danger"
              onClick={handleDeleteCredito}
              disabled={deletingCredito}
            >
              {deletingCredito ? 'Eliminando...' : 'Eliminar solicitud'}
            </button>
            <Link to="/backend/creditos">Volver al listado</Link>
          </div>
        </>
      ) : null}
    </section>
  )
}
