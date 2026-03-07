import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import AhorrosDashboard from '../AhorrosDashboard'

vi.mock('../../services/api_django', () => {
  return {
    djangoApi: {
      get: vi.fn((url) => {
        if (url === '/ahorros/cuentas/') {
          return Promise.resolve({
            data: [{ id: 1, saldo: '100.00' }, { id: 2, saldo: '300.00' }]
          })
        }
        if (url === '/ahorros/movimientos/') {
          return Promise.resolve({
            data: [{ id: 1 }, { id: 2 }, { id: 3 }]
          })
        }
        if (url === '/socios/') {
          return Promise.resolve({
            data: [
              { id: 1, segmento: 'hormiga' },
              { id: 2, segmento: 'gran_ahorrador' },
              { id: 3, segmento: 'inactivo' }
            ]
          })
        }
        return Promise.resolve({ data: [] })
      })
    }
  }
})

describe('AhorrosDashboard', () => {
  it('muestra KPIs y grafico de torta con datos cargados', async () => {
    render(<AhorrosDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Ahorros y Segmentación')).toBeInTheDocument()
      expect(screen.getByText('Cuentas de ahorro')).toBeInTheDocument()
      expect(screen.getByText('Movimientos')).toBeInTheDocument()
      expect(screen.getByText('Captación total')).toBeInTheDocument()
      expect(screen.getByLabelText('Grafico de torta de segmentos')).toBeInTheDocument()
    })
  })
})
