import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import Button from '../components/Button'
import Card from '../components/Card'
import Table from '../components/Table'
import { djangoApi } from '../services/api_django'

const initialForm = {
  nombre: '',
  tipo: '',
  fecha_inicio: '',
  fecha_fin: '',
  estado: 'borrador'
}

function mapEstado(estado) {
  if (estado === 'activa') return 'Activa'
  if (estado === 'finalizada') return 'Finalizada'
  return 'Borrador'
}

export default function CampaniasList() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  const columns = useMemo(
    () => [
      { key: 'nombre', label: 'Nombre' },
      { key: 'tipo', label: 'Tipo' },
      { key: 'inicio', label: 'Inicio' },
      { key: 'fin', label: 'Fin' },
      { key: 'estado', label: 'Estado' }
    ],
    []
  )

  const fetchCampanias = () => {
    setLoading(true)
    setError('')
    djangoApi
      .get('/campanas/')
      .then((response) => {
        const mapped = (response.data || []).map((campania) => ({
          id: campania.id,
          nombre: campania.nombre,
          tipo: campania.tipo,
          inicio: campania.fecha_inicio,
          fin: campania.fecha_fin,
          estado: mapEstado(campania.estado)
        }))
        setRows(mapped)
      })
      .catch(() => {
        setError('No se pudo cargar la lista de campañas.')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchCampanias()
  }, [])

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    setSaving(true)
    setFormError('')

    djangoApi
      .post('/campanas/', form)
      .then(() => {
        setForm(initialForm)
        fetchCampanias()
      })
      .catch((apiError) => {
        const responseError = apiError?.response?.data
        if (responseError && typeof responseError === 'object') {
          const firstKey = Object.keys(responseError)[0]
          const message = Array.isArray(responseError[firstKey]) ? responseError[firstKey][0] : responseError[firstKey]
          setFormError(String(message))
          return
        }
        setFormError('No se pudo crear la campaña.')
      })
      .finally(() => setSaving(false))
  }

  return (
    <section className="campanias-page">
      <h1>Campañas</h1>
      <p>Gestión de campañas de captación y reactivación.</p>
      <p className="campanias-page__link-row">
        <Link to="/web/prospectos">Ver prospectos potenciales</Link>
      </p>
      <p className="campanias-page__link-row">
        <Link to="/web/socios-inactivos">Ver socios inactivos por zona</Link>
      </p>

      <Card title="Nueva campaña">
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="nombre">Nombre</label>
          <input id="nombre" name="nombre" value={form.nombre} onChange={handleChange} required />

          <label htmlFor="tipo">Tipo</label>
          <input id="tipo" name="tipo" value={form.tipo} onChange={handleChange} required />

          <label htmlFor="fecha_inicio">Fecha inicio</label>
          <input id="fecha_inicio" name="fecha_inicio" type="date" value={form.fecha_inicio} onChange={handleChange} required />

          <label htmlFor="fecha_fin">Fecha fin</label>
          <input id="fecha_fin" name="fecha_fin" type="date" value={form.fecha_fin} onChange={handleChange} required />

          <label htmlFor="estado">Estado</label>
          <select id="estado" name="estado" value={form.estado} onChange={handleChange}>
            <option value="borrador">Borrador</option>
            <option value="activa">Activa</option>
            <option value="finalizada">Finalizada</option>
          </select>

          {formError ? <p className="campanias-page__status campanias-page__status--error">{formError}</p> : null}
          <div className="auth-actions">
            <Button type="submit" variant="primary" disabled={saving}>
              {saving ? 'Guardando...' : 'Crear campaña'}
            </Button>
          </div>
        </form>
      </Card>

      {loading ? <p className="campanias-page__status">Cargando...</p> : null}
      {error ? <p className="campanias-page__status campanias-page__status--error">{error}</p> : null}
      {!loading && !error ? <Table columns={columns} rows={rows} /> : null}
    </section>
  )
}
