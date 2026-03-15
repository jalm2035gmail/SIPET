import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import Dashboards18 from '../Dashboards18'

const { getMock } = vi.hoisted(() => ({
  getMock: vi.fn((url, config) => {
    if (url === '/analitica/ml/dashboard/ejecutivos-operativos/') {
      if (config?.params?.detalle === 1 && config?.params?.sucursal) {
        return Promise.resolve({
          data: {
            drilldown: {
              sucursal: config.params.sucursal,
              total_socios: 4,
              creditos_recientes: [
                {
                  credito_id: 101,
                  socio_id: 10,
                  socio_nombre: 'Socio Yuriria',
                  monto: 1200,
                  estado: 'aprobado',
                  fecha_creacion: '2026-02-18T10:00:00Z'
                }
              ],
              alertas_mora: [
                {
                  credito_id: 101,
                  socio_id: 10,
                  socio_nombre: 'Socio Yuriria',
                  alerta: 'media',
                  prob_mora_90d: 0.45,
                  fecha_creacion: '2026-02-18T11:00:00Z'
                }
              ]
            }
          }
        })
      }
      return Promise.resolve({
        data: {
          salud_cartera: {
            cartera_total: 2000,
            cartera_vigente: 1500,
            cartera_vencida_estimada: 500,
            imor_pct: 25
          },
          colocacion: {
            meta_colocacion_30d: 100000,
            colocacion_real_30d: 15000,
            cumplimiento_meta_pct: 15,
            embudo_solicitados: 10,
            embudo_aprobados: 6,
            embudo_rechazados: 4,
            tiempo_respuesta_promedio_h: 4.3
          },
          captacion: {
            depositos_30d: 8000,
            retiros_30d: 2200,
            crecimiento_neto_30d: 5800,
            estabilidad_ahorro_pct: 76
          },
          riesgo: {
            cobertura_pct: 58,
            provisiones_estimadas: 300,
            castigos_estimados: 120
          },
          sucursales: [
            { ranking: 1, sucursal: 'Yuriria', colocacion_30d: 9000, alertas_mora: 2 }
          ],
          eficiencia_cobranza: {
            gestiones_total: 8,
            gestiones_con_recuperacion: 3,
            eficiencia_cobranza_pct: 37.5,
            recuperacion_por_gestion: 55
          },
          tendencias: {
            mensual: {
              salud_cartera_imor_pct: [{ periodo: '2026-01', valor: 22.5 }],
              colocacion_monto: [{ periodo: '2026-01', valor: 12000 }],
              captacion_neto: [{ periodo: '2026-01', valor: 6000 }],
              riesgo_cobertura_pct: [{ periodo: '2026-01', valor: 58 }],
              cobranza_eficiencia_pct: [{ periodo: '2026-01', valor: 37.5 }],
              sucursales_colocacion: [{ periodo: '2026-01', yuriria: 9000, cuitzeo: 2000, santa_ana_maya: 1000 }]
            },
            trimestral: {
              salud_cartera_imor_pct: [{ periodo: '2026-Q1', valor: 23.1 }],
              colocacion_monto: [{ periodo: '2026-Q1', valor: 11000 }],
              captacion_neto: [{ periodo: '2026-Q1', valor: 5800 }],
              riesgo_cobertura_pct: [{ periodo: '2026-Q1', valor: 55 }],
              cobranza_eficiencia_pct: [{ periodo: '2026-Q1', valor: 35 }]
            }
          },
          actualizacion: {
            ultima_actualizacion_utc: '2026-02-18T12:00:00Z',
            fuente: 'archivo_estado'
          }
        }
      })
    }
    const semaforo = config?.params?.semaforo
    const MAINRow = {
      componente: 'cartera:imor',
      ambito: 'riesgo',
      semaforo: 'Rojo',
      estado: 'En revision',
      detalle: { valor: 21.4, umbral: 15.0, fecha_evento: '2026-02-18T10:00:00Z' }
    }
    const rows = semaforo === 'Verde' ? [] : [MAINRow]
    return Promise.resolve({
      data: {
        resumen: {
          total: rows.length,
          rojo: rows.length,
          amarillo: 0,
          verde: 0
        },
        semaforos: rows,
        actualizacion: {
          ultima_actualizacion_utc: '2026-02-18T12:00:00Z',
          fuente: 'archivo_estado'
        }
      }
    })
  })
}))

vi.mock('../../services/api_django', () => {
  return {
    djangoApi: {
      get: getMock
    }
  }
})

describe('Dashboards18', () => {
  it('muestra resumen y tabla de semaforos', async () => {
    render(<Dashboards18 />)

    await waitFor(() => {
      expect(screen.getByText('Dashboards Ejecutivos y Operativos (1.8)')).toBeInTheDocument()
      expect(screen.getByText('Salud de cartera')).toBeInTheDocument()
      expect(screen.getByText('Total semaforos')).toBeInTheDocument()
      expect(screen.getByText(/Ultima actualizacion:/)).toBeInTheDocument()
      expect(screen.getAllByText(/Tendencia mensual:/).length).toBeGreaterThan(0)
      expect(screen.getByText('cartera:imor')).toBeInTheDocument()
      expect(screen.getByText('riesgo')).toBeInTheDocument()
      expect(screen.getByText('En revision')).toBeInTheDocument()
    })
  })

  it('aplica filtro de semaforo y recarga la consulta', async () => {
    render(<Dashboards18 />)
    await waitFor(() => expect(screen.getByText('cartera:imor')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Semaforo'), { target: { value: 'Verde' } })

    await waitFor(() => {
      expect(screen.getByText('Sin alertas activas.')).toBeInTheDocument()
      expect(getMock).toHaveBeenLastCalledWith('/analitica/ml/dashboard/semaforos/', {
        params: { semaforo: 'Verde' }
      })
    })
  })

  it('exporta CSV con filtros activos', async () => {
    const createObjectUrlMock = vi.fn(() => 'blob:mock-url')
    const revokeObjectUrlMock = vi.fn()
    global.URL.createObjectURL = createObjectUrlMock
    global.URL.revokeObjectURL = revokeObjectUrlMock

    render(<Dashboards18 />)
    await waitFor(() => expect(screen.getByText('cartera:imor')).toBeInTheDocument())
    await waitFor(() => expect(screen.getByRole('button', { name: 'Exportar CSV' })).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Semaforo'), { target: { value: 'Rojo' } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Exportar CSV' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }))

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/analitica/ml/dashboard/semaforos/', {
        params: { export: 'csv', semaforo: 'Rojo' },
        responseType: 'blob'
      })
      expect(createObjectUrlMock).toHaveBeenCalled()
      expect(revokeObjectUrlMock).toHaveBeenCalledWith('blob:mock-url')
    })
  })

  it('carga drill-down por sucursal', async () => {
    render(<Dashboards18 />)
    await waitFor(() => expect(screen.getByText('Yuriria')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: 'Ver detalle' }))

    await waitFor(() => {
      expect(screen.getByText('Detalle operativo - Yuriria')).toBeInTheDocument()
      expect(screen.getByText('Créditos recientes')).toBeInTheDocument()
      expect(screen.getByText('Alertas de mora')).toBeInTheDocument()
      expect(screen.getAllByText('Socio Yuriria').length).toBeGreaterThan(0)
      expect(getMock).toHaveBeenCalledWith('/analitica/ml/dashboard/ejecutivos-operativos/', {
        params: { sucursal: 'Yuriria', detalle: 1 }
      })
    })
  })
})
