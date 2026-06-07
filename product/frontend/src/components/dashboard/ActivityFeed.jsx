import Card from '../common/Card';
import Badge from '../common/Badge';
import Spinner from '../common/Spinner';

const defaultActivities = [
  {
    id: 1,
    action: 'Investigation terminée',
    target: 'example.com',
    service: 'DNS Resolver',
    timestamp: 'Il y a 2 min',
    status: 'success',
  },
  {
    id: 2,
    action: 'Nouvelle alerte',
    target: 'suspicious-domain.net',
    service: 'VirusTotal',
    timestamp: 'Il y a 5 min',
    status: 'warning',
  },
  {
    id: 3,
    action: 'Rapport généré',
    target: '192.168.1.1',
    service: 'Shodan',
    timestamp: 'Il y a 12 min',
    status: 'success',
  },
  {
    id: 4,
    action: 'Service indisponible',
    target: '—',
    service: 'Certificate Search',
    timestamp: 'Il y a 18 min',
    status: 'error',
  },
  {
    id: 5,
    action: 'Analyse en cours',
    target: 'test-company.io',
    service: 'WHOIS Lookup',
    timestamp: 'Il y a 23 min',
    status: 'info',
  },
];

const statusStyles = {
  success: { badge: 'success', dot: 'bg-emerald-500' },
  warning: { badge: 'warning', dot: 'bg-amber-500' },
  error: { badge: 'error', dot: 'bg-red-500' },
  info: { badge: 'info', dot: 'bg-cyan-500' },
};

export default function ActivityFeed({ activities: propActivities, loading }) {
  const activities = propActivities && propActivities.length > 0 ? propActivities : defaultActivities;

  if (loading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-8">
          <Spinner text="Chargement de l'activité..." />
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Activité récente
        </h3>
        <span className="text-[10px] text-gray-600 font-mono">Temps réel</span>
      </div>

      <div className="space-y-1">
        {activities.map((activity, index) => {
          const style = statusStyles[activity.status] || statusStyles.info;

          return (
            <div
              key={activity.id}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-800/30 transition-colors group"
            >
              {/* Timeline dot */}
              <div className="flex flex-col items-center">
                <span className={`w-2 h-2 rounded-full ${style.dot} flex-shrink-0`} />
                {index < activities.length - 1 && (
                  <span className="w-px h-full min-h-[1.5rem] bg-gray-800 mt-1" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-200 truncate">
                    {activity.action}
                  </span>
                  <Badge severity={style.badge} size="sm">
                    {activity.service}
                  </Badge>
                </div>
                <span className="text-xs text-gray-500 font-mono truncate block">
                  {activity.target}
                </span>
              </div>

              {/* Timestamp */}
              <span className="text-[11px] text-gray-600 whitespace-nowrap group-hover:text-gray-500 transition-colors">
                {activity.timestamp}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
