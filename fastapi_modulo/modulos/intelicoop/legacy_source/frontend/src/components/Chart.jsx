export default function Chart({ data = [] }) {
  const safeData = data.length ? data : [10, 12, 9, 15, 14, 18]
  const max = Math.max(...safeData, 1)
  const width = 420
  const height = 160
  const step = safeData.length > 1 ? width / (safeData.length - 1) : width

  const points = safeData
    .map((value, index) => {
      const x = Math.round(index * step)
      const y = Math.round(height - (value / max) * height)
      return `${x},${y}`
    })
    .join(' ')

  return (
    <div className="ui-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Grafico de tendencia">
        <polyline points={points} className="ui-chart__line" />
        {safeData.map((value, index) => {
          const x = Math.round(index * step)
          const y = Math.round(height - (value / max) * height)
          return <circle key={`${index}-${value}`} cx={x} cy={y} r="3" className="ui-chart__dot" />
        })}
      </svg>
    </div>
  )
}
