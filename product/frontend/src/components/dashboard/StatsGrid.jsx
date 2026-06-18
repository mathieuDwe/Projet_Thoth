import Card from '../common/Card';
import { ArrowTrendingUpIcon, CheckCircleIcon, ServerStackIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import Spinner from '../common/Spinner';

const statCards = [
  {
    key: 'totalRequests',
    label: 'Requêtes totales',
    icon: ArrowTrendingUpIcon,
    iconColor: 'text-cyan-400',
    iconBg: 'bg-cyan-500/10',
    format: (v) => (v ?? 0).toLocaleString(),
  },
  {
    key: 'successRate',
    label: 'Taux de succès',
    icon: CheckCircleIcon,
    iconColor: 'text-emerald-400',
    iconBg: 'bg-emerald-500/10',
    format: (v) => `${(v ?? 0).toFixed(1)}%`,
  },
  {
    key: 'activeServices',
    label: 'Services actifs',
    icon: ServerStackIcon,
    iconColor: 'text-emerald-400',
    iconBg: 'bg-emerald-500/10',
    format: (v) => `${v ?? 0}/6`,
  },
  {
    key: 'alerts',
    label: 'Alertes',
    icon: ExclamationTriangleIcon,
    iconColor: 'text-amber-400',
    iconBg: 'bg-amber-500/10',
    format: (v) => (v ?? 0).toString(),
  },
];

export default function StatsGrid({ stats, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <div className="animate-pulse space-y-3">
              <div className="h-4 w-24 bg-gray-800 rounded" />
              <div className="h-8 w-16 bg-gray-800 rounded" />
            </div>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {statCards.map((card) => {
        const Icon = card.icon;
        const value = stats?.[card.key] ?? 0;

        return (
          <Card key={card.key}>
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {card.label}
                </span>
                <div className="text-2xl font-bold text-gray-100 font-mono">
                  {card.format(value)}
                </div>
              </div>
              <div className={`p-2 rounded-lg ${card.iconBg}`}>
                <Icon className={`w-5 h-5 ${card.iconColor}`} />
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
