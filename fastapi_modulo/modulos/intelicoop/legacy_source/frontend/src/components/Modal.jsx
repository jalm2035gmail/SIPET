import { useEffect } from 'react'

export default function Modal({ open = false, title, children, onClose }) {
  useEffect(() => {
    if (!open) return

    const handleEsc = (event) => {
      if (event.key === 'Escape') onClose?.()
    }

    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="ui-modal-overlay" onClick={onClose}>
      <div className="ui-modal" onClick={(event) => event.stopPropagation()}>
        <header className="ui-modal__header">
          <h3>{title || 'Modal'}</h3>
          <button type="button" className="ui-modal__close" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </header>
        <div className="ui-modal__body">{children}</div>
      </div>
    </div>
  )
}
