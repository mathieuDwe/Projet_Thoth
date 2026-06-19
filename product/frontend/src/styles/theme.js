export const THEME = {
  colors: {
    background: {
      primary: 'bg-gray-950',
      secondary: 'bg-gray-900',
      card: 'bg-gray-900',
      hover: 'hover:bg-gray-800',
      active: 'bg-gray-800',
    },
    border: {
      default: 'border-gray-800',
      hover: 'hover:border-emerald-500/30',
      focus: 'focus:border-emerald-500',
    },
    text: {
      primary: 'text-gray-100',
      secondary: 'text-gray-400',
      muted: 'text-gray-500',
      accent: 'text-emerald-400',
      danger: 'text-red-400',
      warning: 'text-amber-400',
      info: 'text-cyan-400',
    },
    accent: {
      primary: 'emerald',
      secondary: 'cyan',
      warning: 'amber',
      danger: 'red',
    },
    severity: {
      critical: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
      high: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
      medium: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20' },
      low: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' },
      info: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20' },
    },
    status: {
      online: { dot: 'bg-emerald-500', pulse: 'animate-pulse', text: 'text-emerald-400' },
      offline: { dot: 'bg-red-500', pulse: '', text: 'text-red-400' },
      degraded: { dot: 'bg-amber-500', pulse: 'animate-pulse', text: 'text-amber-400' },
    },
  },
  spacing: {
    card: 'p-4 md:p-6',
    section: 'mb-8',
  },
  typography: {
    sectionTitle: 'text-lg font-semibold text-gray-100 uppercase tracking-wider',
    cardTitle: 'text-sm font-semibold text-gray-300 uppercase tracking-wider',
    technical: 'font-mono text-emerald-400 text-sm',
    label: 'text-xs font-medium text-gray-500 uppercase tracking-wider',
  },
  animation: {
    transition: 'transition-all duration-200 ease-in-out',
    hover: 'hover:scale-[1.02]',
  },
};
