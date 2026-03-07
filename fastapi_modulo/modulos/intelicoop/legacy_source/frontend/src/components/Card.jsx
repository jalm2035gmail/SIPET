export default function Card({ title, children, footer }) {
  return (
    <section className="ui-card">
      {title ? <header className="ui-card__header">{title}</header> : null}
      <div className="ui-card__body">{children}</div>
      {footer ? <footer className="ui-card__footer">{footer}</footer> : null}
    </section>
  )
}
