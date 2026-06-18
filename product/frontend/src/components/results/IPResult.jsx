import { MapPinIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';

function InfoRow({ label, value, color = 'text-gray-200' }) {
  if (!value) return null;
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-gray-800/50 last:border-0">
      <span className="text-xs text-gray-500">{label}</span>
      <span className={`text-xs font-mono ${color}`}>{value}</span>
    </div>
  );
}

export default function IPResult({ data }) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <MapPinIcon className="w-5 h-5" />
        <span className="text-sm">Aucune donnée de géolocalisation disponible</span>
      </div>
    );
  }

  const ip = data.ip || data.query || data.target || '—';
  const isVPN = data.vpn || data.proxy || data.threat || false;
  const isMobile = data.mobile || false;

  return (
    <div className="space-y-4">
      {/* Résumé */}
      <div className="flex items-center gap-2">
        <MapPinIcon className="w-5 h-5 text-amber-400" />
        <span className="text-sm font-medium text-gray-200">
          Géolocalisation de <span className="text-amber-400 font-mono">{ip}</span>
        </span>
      </div>

      {/* Carte info */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-gray-900/30 border border-gray-800 rounded-lg p-3 space-y-1">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Localisation</h4>
          <InfoRow label="Ville" value={data.city} />
          <InfoRow label="Région" value={data.region || data.regionName} />
          <InfoRow label="Pays" value={data.country || data.countryName} color="text-emerald-400" />
          <InfoRow label="Code postal" value={data.zip || data.postal} />
          {data.lat && data.lon && (
            <InfoRow label="Coordonnées" value={`${data.lat}, ${data.lon}`} color="text-cyan-400" />
          )}
        </div>

        <div className="bg-gray-900/30 border border-gray-800 rounded-lg p-3 space-y-1">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Réseau</h4>
          <InfoRow label="FAI" value={data.isp || data.org} />
          <InfoRow label="ASN" value={data.as || data.asn} />
          <InfoRow label="Organisation" value={data.org} />
          <InfoRow label="Hostname" value={data.hostname || data.reverse} color="text-cyan-400" />
        </div>
      </div>

      {/* Statuts de sécurité */}
      <div className="flex flex-wrap gap-2">
        {isVPN ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-red-500/10 border border-red-500/20 text-red-400">
            <XCircleIcon className="w-4 h-4" /> VPN / Proxy détecté
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <CheckCircleIcon className="w-4 h-4" /> Aucun VPN détecté
          </span>
        )}
        {isMobile && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 border border-amber-500/20 text-amber-400">
            Connexion mobile
          </span>
        )}
      </div>
    </div>
  );
}
