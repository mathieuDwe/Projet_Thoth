import BreachResult from './BreachResult';
import SocialResult from './SocialResult';
import DNSResult from './DNSResult';
import IPResult from './IPResult';
import { ClockIcon } from '@heroicons/react/24/outline';

const serviceComponents = {
  breach_lookup: BreachResult,
  social_harvester: SocialResult,
  dns_investigator: DNSResult,
  ip_geolocation: IPResult,
  ip_geoloc: IPResult,
};

export default function ResultRenderer({ serviceName, data, success, summary, error }) {
  const Component = serviceComponents[serviceName];

  if (error) {
    return (
      <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/5 border border-red-500/10 rounded-lg px-4 py-3">
        <ClockIcon className="w-4 h-4" />
        <span>{error}</span>
      </div>
    );
  }

  if (!success || !data) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <ClockIcon className="w-4 h-4" />
        <span>Aucune donnée disponible</span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {summary && (
        <p className="text-sm text-gray-400 border-l-2 border-emerald-500/30 pl-3 italic">{summary}</p>
      )}
      {Component ? (
        <Component data={data} />
      ) : (
        <pre className="text-xs text-gray-400 bg-gray-950 p-3 rounded-lg overflow-x-auto max-h-60">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
