export default function Card({
  children,
  className = '',
  padding = true,
  hover = true,
  glow = false,
  onClick,
}) {
  return (
    <div
      onClick={onClick}
      className={`
        bg-gray-900 border border-gray-800 rounded-xl
        ${padding ? 'p-4 md:p-6' : ''}
        ${hover ? 'card-hover hover:border-emerald-500/30 hover:shadow-lg hover:shadow-emerald-500/5' : ''}
        ${glow ? 'shadow-sm shadow-emerald-500/5' : ''}
        ${onClick ? 'cursor-pointer' : ''}
        transition-all duration-200 ease-in-out
        ${className}
      `}
    >
      {children}
    </div>
  );
}
