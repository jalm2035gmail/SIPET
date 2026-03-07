export default function Button({
  children,
  type = 'button',
  variant = 'primary',
  disabled = false,
  onClick
}) {
  return (
    <button
      type={type}
      className={`ui-button ui-button--${variant}`}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  )
}
