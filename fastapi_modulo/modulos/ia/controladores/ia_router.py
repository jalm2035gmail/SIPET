"""Router IA activo para SIPET.

Expone la ruta de UI (/ia) y los endpoints funcionales de sugerencias
(/api/ia/*) definidos en el módulo operativo.
"""

from fastsipet_modulo.modulos.ia.ia import router as ia_router
