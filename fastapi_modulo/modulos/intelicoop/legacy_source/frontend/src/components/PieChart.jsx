function toRad(deg) {
  return (deg * Math.PI) / 180
}

function polarToCartesian(cx, cy, r, angleDeg) {
  const angle = toRad(angleDeg - 90)
  return {
    x: cx + r * Math.cos(angle),
    y: cy + r * Math.sin(angle)
  }
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end = polarToCartesian(cx, cy, r, startAngle)
  const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1'
  return `M ${cx} ${cy} L ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y} Z`
}

export default function PieChart({ slices = [] }) {
  const total = slices.reduce((acc, s) => acc + Number(s.value || 0), 0)
  const data = total > 0 ? slices : [{ label: 'Sin datos', value: 1, color: '#cbd5e1' }]
  const totalSafe = data.reduce((acc, s) => acc + Number(s.value || 0), 0)

  let startAngle = 0
  const arcs = data.map((slice, idx) => {
    const value = Number(slice.value || 0)
    const angle = (value / totalSafe) * 360
    const endAngle = startAngle + angle
    const path = describeArc(110, 110, 95, startAngle, endAngle)
    const percent = Math.round((value / totalSafe) * 100)
    const current = { ...slice, path, percent, key: `${slice.label}-${idx}` }
    startAngle = endAngle
    return current
  })

  return (
    <div className="ui-piechart">
      <svg viewBox="0 0 220 220" role="img" aria-label="Grafico de torta de segmentos">
        {arcs.map((arc) => (
          <path key={arc.key} d={arc.path} fill={arc.color} stroke="#ffffff" strokeWidth="2" />
        ))}
      </svg>
      <div className="ui-piechart__legend">
        {arcs.map((arc) => (
          <div key={`${arc.key}-legend`} className="ui-piechart__legend-item">
            <span className="ui-piechart__dot" style={{ background: arc.color }} />
            <span>
              {arc.label}: {arc.value} ({arc.percent}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
