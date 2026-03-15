import { useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'

import Table from '../components/Table'
import { djangoApi } from '../services/api_django'

const ZONAS = [
  { zona: 'Centro', coords: [14.6349, -90.5069] },
  { zona: 'Norte', coords: [14.6902, -90.5009] },
  { zona: 'Sur', coords: [14.5623, -90.5238] },
  { zona: 'Este', coords: [14.6311, -90.437] },
  { zona: 'Oeste', coords: [14.6469, -90.5778] }
]

function buildHeatmap(rows) {
  const MAIN = ZONAS.map((item) => ({ ...item, total: 0 }))
  rows.forEach((_row, index) => {
    const zonaIndex = index % ZONAS.length
    MAIN[zonaIndex].total += 1
  })
  const max = Math.max(...MAIN.map((item) => item.total), 1)
  return MAIN.map((item) => ({
    ...item,
    intensidad: item.total / max
  }))
}

export default function SociosInactivos() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const mapContainerRef = useRef(null)
  const mapRef = useRef(null)
  const overlayRef = useRef(null)

  const columns = useMemo(
    () => [
      { key: 'nombre', label: 'Nombre' },
      { key: 'email', label: 'Email' },
      { key: 'telefono', label: 'Teléfono' },
      { key: 'direccion', label: 'Dirección' }
    ],
    []
  )

  useEffect(() => {
    djangoApi
      .get('/socios/')
      .then((response) => {
        const inactivos = (response.data || []).filter((socio) => socio.segmento === 'inactivo')
        const mapped = inactivos.map((socio) => ({
          id: socio.id,
          nombre: socio.nombre,
          email: socio.email,
          telefono: socio.telefono,
          direccion: socio.direccion
        }))
        setRows(mapped)
      })
      .catch(() => {
        setError('No se pudo cargar la lista de socios inactivos.')
      })
      .finally(() => setLoading(false))
  }, [])

  const heatmap = useMemo(() => buildHeatmap(rows), [rows])

  useEffect(() => {
    if (loading || error || !mapContainerRef.current) return

    if (!mapRef.current) {
      mapRef.current = L.map(mapContainerRef.current, {
        scrollWheelZoom: false
      }).setView([14.6349, -90.5069], 11)

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(mapRef.current)
    }

    if (!overlayRef.current) {
      overlayRef.current = L.layerGroup().addTo(mapRef.current)
    } else {
      overlayRef.current.clearLayers()
    }

    heatmap.forEach((item) => {
      L.circle(item.coords, {
        radius: 900 + item.total * 350,
        color: '#b91c1c',
        weight: 1.5,
        fillColor: '#ef4444',
        fillOpacity: Math.max(0.2, item.intensidad * 0.75)
      })
        .bindPopup(`${item.zona}: ${item.total} socios inactivos`)
        .addTo(overlayRef.current)
    })
  }, [loading, error, heatmap])

  useEffect(
    () => () => {
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    },
    []
  )

  return (
    <section className="inactivos-page">
      <h1>Socios Inactivos</h1>
      <p>MAIN para campañas de reactivación y priorización territorial.</p>

      {loading ? <p className="inactivos-page__status">Cargando...</p> : null}
      {error ? <p className="inactivos-page__status inactivos-page__status--error">{error}</p> : null}

      {!loading && !error ? (
        <>
          <div className="inactivos-page__map-wrap">
            <div ref={mapContainerRef} className="inactivos-page__map" />
          </div>
          <div className="inactivos-page__heatmap">
            {heatmap.map((zona) => (
              <article
                key={zona.zona}
                className="inactivos-page__heat-cell"
                style={{ '--intensidad': String(Math.max(zona.intensidad, 0.12)) }}
              >
                <h3>{zona.zona}</h3>
                <p>{zona.total} socios inactivos</p>
              </article>
            ))}
          </div>
          <Table columns={columns} rows={rows} />
        </>
      ) : null}
    </section>
  )
}
