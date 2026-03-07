const REGLAS_PRODUCTO = {
  hormiga: {
    nombre: "Ahorro Programado",
    descripcion: "Aporta montos pequeños automáticos para construir hábito de ahorro."
  },
  gran_ahorrador: {
    nombre: "Depósito a Plazo",
    descripcion: "Maximiza rendimiento con una tasa preferencial para saldos altos."
  },
  inactivo: {
    nombre: "Plan Reactivación",
    descripcion: "Incentivo de retorno con beneficios por retomar aportaciones."
  }
}

export default function ProductoRecomendado({ segmento }) {
  const producto = REGLAS_PRODUCTO[segmento] || REGLAS_PRODUCTO.inactivo

  return (
    <div className="producto-recomendado">
      <strong>{producto.nombre}</strong>
      <p>{producto.descripcion}</p>
      <button type="button" className="ui-button ui-button--secondary">
        Ofrecer producto
      </button>
    </div>
  )
}
