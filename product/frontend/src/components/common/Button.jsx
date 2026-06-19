import { forwardRef } from 'react';

const variants = {
  primary:
    'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm shadow-emerald-600/20 hover:shadow-emerald-500/30',
  secondary:
    'bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 hover:border-gray-600',
  danger:
    'bg-red-600/10 hover:bg-red-600/20 text-red-400 border border-red-500/30 hover:border-red-400/50',
  ghost:
    'bg-transparent hover:bg-gray-800/50 text-gray-400 hover:text-gray-200',
};

const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
};

const Button = forwardRef(function Button(
  {
    variant = 'primary',
    size = 'md',
    className = '',
    disabled = false,
    loading = false,
    children,
    icon: Icon,
    ...props
  },
  ref
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center gap-2 rounded-lg font-medium
        transition-all duration-200 ease-in-out
        focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:ring-offset-1 focus:ring-offset-gray-900
        disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100
        ${variants[variant] || variants.primary}
        ${sizes[size] || sizes.md}
        ${!disabled && !loading ? 'hover:scale-[1.02] active:scale-[0.98]' : ''}
        ${className}
      `}
      {...props}
    >
      {loading ? (
        <svg
          className="animate-spin h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      ) : Icon ? (
        <Icon className="w-4 h-4" />
      ) : null}
      {children}
    </button>
  );
});

export default Button;
