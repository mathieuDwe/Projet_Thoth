import { useState, useEffect } from 'react';

const DEFAULT_SERVICES = [
  { name: 'API Gateway', status: 'online' },
  { name: 'DNS Resolver', status: 'online' },
  { name: 'WHOIS Lookup', status: 'online' },
  { name: 'Shodan', status: 'online' },
  { name: 'VirusTotal', status: 'degraded' },
];

const statusConfig = {
  online: { dot: 'bg-emerald-500', pulse: 'shadow-sm shadow-emerald-500/50', label: 'Connecté' },
  offline: { dot: 'bg-red-500', pulse: '', label: 'Déconnecté' },
  degraded: { dot: 'bg-amber-500', pulse: 'animate-pulse', label: 'Dégradé' },
};

export default function StatusBar({ services: propServices } ) {
  const [services] = useState(propServices || DEFAULT_SERVICES);

  // Si la prop est fournie (via le dashboard), on se synchronise
  useEffect(() => {
    if (propServices) {
      // In a real app, we'd sync
    }
  }, [propServices]);

  const onlineCount = services.filter((s) => s.status === 'online').length;
  const totalCount = services.length;

  return (
    <div className="h-9 px-4 bg-gray-900/80 backdrop-blur-sm border-b border-gray-800 flex items-center gap-4 overflow-x-auto">
      <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">
        Microservices
      </span>
      <div className="flex items-center gap-3 flex-1">
        {services.map((service) => {
          const config = statusConfig[service.status] || statusConfig.offline;
          return (
            <div
              key={service.name}
              className="flex items-center gap-1.5 whitespace-nowrap"
              title={`${service.name}: ${config.label}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${config.dot} ${config.pulse}`} />
              <span className="text-[11px] text-gray-400">{service.name}</span>
            </div>
          );
        })}
      </div>
      <span className="text-[11px] text-gray-500 whitespace-nowrap font-mono">
        {onlineCount}/{totalCount} online
      </span>
    </div>
  );
}
