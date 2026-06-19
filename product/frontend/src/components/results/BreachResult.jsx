import { ShieldExclamationIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

function BreachItem({ breach }) {
  const fields = [
    { label: 'Source', value: breach.Name || breach.source, color: 'text-cyan-400' },
    { label: 'Date', value: breach.BreachDate || breach.date, color: 'text-gray-300' },
    { label: 'Données', value: breach.DataClasses?.join(', ') || breach.data, color: 'text-amber-300' },
  ];

  return (
    <div className="border border-red-500/20 bg-red-500/5 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <ExclamationTriangleIcon className="w-4 h-4 text-red-400" />
        <span className="text-sm font-semibold text-red-300">{breach.Title || breach.Name || breach.source || 'Breach'}</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5 text-xs">
        {fields.filter(f => f.value).map(f => (
          <div key={f.label}>
            <span className="text-gray-500">{f.label}: </span>
            <span className={f.color}>{f.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PasteItem({ paste }) {
  return (
    <div className="border border-amber-500/20 bg-amber-500/5 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1.5">
        <ExclamationTriangleIcon className="w-4 h-4 text-amber-400" />
        <span className="text-xs font-semibold text-amber-300">{paste.Source || paste.source || 'Paste'}</span>
      </div>
      <p className="text-xs text-gray-400 truncate">{paste.Title || paste.title || 'Sans titre'}</p>
      {paste.Id && (
        <a href={`https://pastebin.com/${paste.Id}`} target="_blank" rel="noreferrer"
           className="text-xs text-cyan-500 hover:text-cyan-400 mt-1 inline-block">
          Voir sur pastebin →
        </a>
      )}
    </div>
  );
}

export default function BreachResult({ data }) {
  if (!data) return null;

  const hibp = data.hibp || {};
  const breaches = hibp.breaches || [];
  const pastes = hibp.pastes || [];
  const leakcheck = data.leakcheck || {};
  const totalBreaches = breaches.length + (leakcheck.count || 0);
  const error = hibp.error_hibp || data.error;

  return (
    <div className="space-y-4">
      {/* Résumé */}
      <div className="flex items-center gap-2">
        {totalBreaches > 0 ? (
          <>
            <ExclamationTriangleIcon className="w-5 h-5 text-red-400" />
            <span className="text-sm font-medium text-red-300">
              {totalBreaches} fuite{totalBreaches > 1 ? 's' : ''} détectée{totalBreaches > 1 ? 's' : ''}
            </span>
          </>
        ) : error ? (
          <>
            <ExclamationTriangleIcon className="w-5 h-5 text-amber-400" />
            <span className="text-sm text-amber-300">API HIBP nécessite une clé — données partielles</span>
          </>
        ) : (
          <>
            <CheckCircleIcon className="w-5 h-5 text-emerald-400" />
            <span className="text-sm font-medium text-emerald-300">Aucune fuite détectée</span>
          </>
        )}
      </div>

      {/* Breaches */}
      {breaches.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Breaches connus</h4>
          <div className="space-y-2">
            {breaches.map((b, i) => <BreachItem key={i} breach={b} />)}
          </div>
        </div>
      )}

      {/* Pastes */}
      {pastes.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Pastes détectés</h4>
          <div className="space-y-2">
            {pastes.map((p, i) => <PasteItem key={i} paste={p} />)}
          </div>
        </div>
      )}

      {/* Leakcheck data */}
      {leakcheck.data && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Autres sources</h4>
          <pre className="text-xs text-gray-400 bg-gray-950 p-2 rounded max-h-32 overflow-auto">
            {JSON.stringify(leakcheck.data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
