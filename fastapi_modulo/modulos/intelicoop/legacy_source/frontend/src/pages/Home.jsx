import { useEffect, useState } from 'react'

import Button from '../components/Button'
import Card from '../components/Card'
import Chart from '../components/Chart'
import Modal from '../components/Modal'
import Table from '../components/Table'
import { djangoApi } from '../services/api_django'

export default function Home() {
  const [apiStatus, setApiStatus] = useState('Verificando...')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const kpis = [
    { id: 'socios', label: 'Total socios', value: 248 },
    { id: 'creditos', label: 'Créditos activos', value: 61 },
    { id: 'ahorros', label: 'Total ahorros', value: '$1,240,000' }
  ]
  const movementColumns = [
    { key: 'fecha', label: 'Fecha' },
    { key: 'socio', label: 'Socio' },
    { key: 'tipo', label: 'Tipo' },
    { key: 'monto', label: 'Monto' }
  ]
  const movementRows = [
    { id: 1, fecha: '2026-02-17', socio: 'Ana Pérez', tipo: 'Depósito', monto: '$250.00' },
    { id: 2, fecha: '2026-02-17', socio: 'Luis Gómez', tipo: 'Pago crédito', monto: '$180.00' },
    { id: 3, fecha: '2026-02-16', socio: 'María Díaz', tipo: 'Retiro', monto: '$90.00' },
    { id: 4, fecha: '2026-02-16', socio: 'Carlos Ruiz', tipo: 'Depósito', monto: '$420.00' }
  ]

  useEffect(() => {
    djangoApi
      .get('/health/')
      .then(() => setApiStatus('Conectado'))
      .catch(() => setApiStatus('Sin conexión'))
  }, [])

  return (
    <section className="home-page">
      <h1>Home</h1>
      <p>MAIN inicial del frontend en entorno local.</p>
      <div className="kpi-grid">
        {kpis.map((kpi) => (
          <Card key={kpi.id} title={kpi.label}>
            <div className="kpi-value">{kpi.value}</div>
          </Card>
        ))}
      </div>
      <Card title="Estado del sistema" footer="Fase 1 en progreso">
        <p>Estado API Django: {apiStatus}</p>
        <div className="home-actions">
          <Button variant="primary">Botón primario</Button>
          <Button variant="secondary">Botón secundario</Button>
          <Button variant="ghost" onClick={() => setIsModalOpen(true)}>
            Abrir modal
          </Button>
        </div>
        <div className="home-table">
          <h3 className="home-section-title">Últimos movimientos</h3>
          <Table columns={movementColumns} rows={movementRows} />
        </div>
        <div className="home-chart">
          <h3 className="home-section-title">Tendencia mensual</h3>
          <Chart data={[8, 11, 10, 13, 15, 14, 18]} />
        </div>
      </Card>

      <Modal open={isModalOpen} title="Modal de prueba" onClose={() => setIsModalOpen(false)}>
        <p>Componente modal listo para reutilizar en formularios y confirmaciones.</p>
      </Modal>
    </section>
  )
}
