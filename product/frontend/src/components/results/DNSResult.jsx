import { GlobeAltIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

function RecordTable({ title, records, type }) {
  if (!records || records.length === 0) return null;

  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1.5 flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
        {title}
        <span className="text-[10px] text-gray-600 font-mono">({records.length})</span>
      </h4>
      <div className="space-y-1">
        {records.map((r, i) => {
          let display = r;
          let sub = null;
          if (typeof r === 'object' && r !== null) {
            if (r.exchange) display = `${r.exchange} (priorité ${r.preference})`;
            else if (r.mname) {
              display = r.mname;
              sub = `Admin: ${r.rname} | Série: ${r.serial}`;
            }
            else display = JSON.stringify(r);
          }
          return (
            <div key={i} className="flex items-center gap-2 text-xs font-mono text-gray-300 bg-gray-900/50 rounded px-2.5 py-1.5 border border-gray-800/50">
              <span className="text-cyan-400 w-6 flex-shrink-0">{type || '?'}</span>
              <span className="truncate">{display}</span>
              {sub && <span className="text-[10px] text-gray-500 truncate ml-auto hidden sm:block">{sub}</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function DNSResult({ data }) {
  if (!data) return null;

  const records = data.dns_records || {};
  const whois = data.whois || {};
  const emailSec = data.email_security || {};

  const hasRecords = Object.values(records).some(r => r && r.length > 0);

  return (
    <div className="space-y-4">
      {/* Résumé */}
      <div className="flex items-center gap-2">
        <GlobeAltIcon className="w-5 h-5 text-cyan-400" />
        <span className="text-sm font-medium text-gray-200">
          Analyse DNS de <span className="text-cyan-400 font-mono">{data.target}</span>
        </span>
      </div>

      {/* Enregistrements DNS */}
      {hasRecords && (
        <div className="space-y-3">
          <RecordTable title="Enregistrements A (IPv4)" records={records.A} type="A" />
          <RecordTable title="Enregistrements AAAA (IPv6)" records={records.AAAA} type="AAAA" />
          <RecordTable title="Serveurs MX (Mail)" records={records.MX} type="MX" />
          <RecordTable title="Serveurs NS" records={records.NS} type="NS" />
          <RecordTable title="Enregistrements TXT" records={records.TXT} type="TXT" />
          <RecordTable title="CNAME" records={records.CNAME} type="CNAME" />
          <RecordTable title="SOA (Start of Authority)" records={records.SOA} type="SOA" />
        </div>
      )}

      {/* Sécurité email */}
      {Object.keys(emailSec).length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Sécurité Email</h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {Object.entries(emailSec).map(([key, val]) => (
              <div key={key} className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-800 bg-gray-900/30">
                <CheckCircleIcon className={`w-4 h-4 ${val ? 'text-emerald-400' : 'text-red-400'}`} />
                <span className="text-xs text-gray-300 uppercase">{key}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* WHOIS */}
      {Object.keys(whois).length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">WHOIS</h4>
          <div className="grid grid-cols-2 gap-1.5 text-xs">
            {Object.entries(whois).slice(0, 8).map(([k, v]) => (
              <div key={k} className="text-gray-400">
                <span className="text-gray-500">{k}: </span>
                <span className="text-gray-200">{String(v).slice(0, 40)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sous-domaines */}
      {data.subdomains && data.subdomains.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Sous-domaines découverts ({data.subdomains.length})
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {data.subdomains.map((sd, i) => (
              <span key={i} className="px-2 py-1 text-[10px] font-mono text-gray-400 bg-gray-900/50 rounded border border-gray-800">
                {sd}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
