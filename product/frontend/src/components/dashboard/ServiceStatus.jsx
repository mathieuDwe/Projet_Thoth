import Card from '../common/Card';
import Badge from '../common/Badge';
import Spinner from '../common/Spinner';

const statusMap = {
  online: { severity: 'success', label: 'Connecté' },
  offline: { severity: 'error', label: 'Hors ligne' },
  degraded: { severity: 'warning', label: 'Dégradé' },
};

const defaultServices = [
  { name: 'API Gateway', type: 'Core', status: 'online', uptime: '99.9%', latency: '12ms' },
  { name: 'DNS Resolver', type: 'Recon', status: 'online', uptime: '99.8%', latency: '24ms' },
  { name: 'WHOIS Lookup', type: 'Recon', status: 'online', uptime: '99.5%', latency: '340ms' },
  { name: 'Shodan', type: 'Threat Intel', status: 'online', uptime: '98.2%', latency: '890ms' },
  { name: 'VirusTotal', type: 'Threat Intel', status: 'degraded', uptime: '95.1%', latency: '2.1s' },
  { name: 'Certificate Search', type: 'Recon', status: 'offline', uptime: '0%', latency: '—' },
];

export default function ServiceStatus({ services: propServices, loading }) {
  const services = propServices && propServices.length > 0 ? propServices : defaultServices;

  if (loading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-8">
          <Spinner text="Analyse des services..." />
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Statut des microservices
        </h3>
        <span className="text-xs text-gray-500 font-mono">
          {services.filter((s) => s.status === 'online').length}/{services.length} opérationnels
        </span>
      </div>

      <div className="space-y-2">
        {services.map((service) => {
          const statusInfo = statusMap[service.status] || statusMap.offline;

          return (
            <div
              key={service.name}
              className="flex items-center justify-between px-3 py-2.5 rounded-lg bg-gray-800/30 border border-gray-800/50 hover:bg-gray-800/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span
                  className={`w-2 h-2 rounded-full ${
                    service.status === 'online'
                      ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50'
                      : service.status === 'degraded'
                      ? 'bg-amber-500 animate-pulse'
                      : 'bg-red-500'
                  }`}
                />
                <div>
                  <span className="text-sm font-medium text-gray-200">{service.name}</span>
                  <span className="text-xs text-gray-500 ml-2">({service.type})</span>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <span className="text-xs text-gray-500 font-mono">{service.latency}</span>
                <span className="text-xs text-gray-500 font-mono">{service.uptime}</span>
                <Badge severity={statusInfo.severity} dot size="sm">
                  {statusInfo.label}
                </Badge>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
