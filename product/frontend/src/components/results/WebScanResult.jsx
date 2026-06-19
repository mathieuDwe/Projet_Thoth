import { ShieldCheckIcon, CodeBracketIcon } from '@heroicons/react/24/outline';

export default function WebScanResult({ data }) {
  if (!data) return null;
  const techs = data.technologies || [];
  const security = data.security_headers || {};
  return (
    <div className="space-y-3">
      {data.title && <p className="text-sm text-gray-300">"{data.title}"</p>}
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <span className="px-2 py-0.5 rounded text-xs bg-gray-800 border border-gray-700">
          HTTP {data.status_code}
        </span>
      </div>
      {techs.length > 0 && (
        <div>
          <p className="flex items-center gap-1 text-xs text-gray-500 mb-1">
            <CodeBracketIcon className="w-3 h-3" /> Technologies
          </p>
          <div className="flex flex-wrap gap-1">
            {techs.slice(0, 5).map((t, i) => (
              <span key={i} className="px-1.5 py-0.5 rounded bg-gray-800 border border-gray-700 text-xs text-gray-300">{t.name}</span>
            ))}
          </div>
        </div>
      )}
      {Object.keys(security).length > 0 && (
        <div>
          <p className="flex items-center gap-1 text-xs text-gray-500 mb-1">
            <ShieldCheckIcon className="w-3 h-3" /> Sécurité
          </p>
          <div className="space-y-0.5">
            {Object.entries(security).slice(0, 5).map(([k, v]) => (
              <div key={k} className="flex justify-between text-xs">
                <span className="text-gray-500">{k}</span>
                <span className={v !== 'missing' ? 'text-emerald-400' : 'text-red-400'}>
                  {v !== 'missing' ? '✓' : '✗'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
