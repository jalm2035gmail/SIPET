import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import SociosList from '../SociosList'

vi.mock('../../services/api_django', () => {
  return {
    djangoApi: {
      get: vi.fn(() =>
        Promise.resolve({
          data: [
            {
              id: 1,
              nombre: 'Ana',
              email: 'ana@mail.com',
              telefono: '555-0001',
              segmento: 'hormiga'
            },
            {
              id: 2,
              nombre: 'Luis',
              email: 'luis@mail.com',
              telefono: '555-0002',
              segmento: 'gran_ahorrador'
            }
          ]
        })
      )
    }
  }
})

describe('SociosList', () => {
  it('renderiza columna segmento y recomendaciones', async () => {
    render(
      <MemoryRouter>
        <SociosList />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Socios')).toBeInTheDocument()
      expect(screen.getByText('🐜 Ahorrador Hormiga')).toBeInTheDocument()
      expect(screen.getByText('🐘 Gran Ahorrador')).toBeInTheDocument()
      expect(screen.getAllByText('Ofrecer producto').length).toBeGreaterThan(0)
    })
  })
})
