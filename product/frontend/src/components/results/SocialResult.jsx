import { UsersIcon, CheckCircleIcon, XCircleIcon, ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline';

const platformColors = {
  github: 'bg-gray-700 text-gray-200 border-gray-600',
  reddit: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  twitter: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
  instagram: 'bg-pink-500/10 text-pink-400 border-pink-500/20',
  telegram: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  default: 'bg-gray-800 text-gray-300 border-gray-700',
};

export default function SocialResult({ data }) {
  if (!data) return null;

  const platforms = data.platforms || [];
  const found = platforms.filter(p => p.exists);
  const notFound = platforms.filter(p => !p.exists);

  return (
    <div className="space-y-4">
      {/* Résumé */}
      <div className="flex items-center gap-2">
        <UsersIcon className="w-5 h-5 text-violet-400" />
        <span className="text-sm font-medium text-gray-200">
          <span className="text-emerald-400">{found.length}</span>/{platforms.length} plateformes
        </span>
      </div>

      {/* Trouvés */}
      {found.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Comptes trouvés</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {found.map((p, i) => {
              const colors = platformColors[p.platform] || platformColors.default;
              return (
                <a
                  key={i}
                  href={p.url}
                  target="_blank"
                  rel="noreferrer"
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border ${colors} hover:opacity-80 transition-opacity`}
                >
                  <CheckCircleIcon className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium block truncate capitalize">{p.platform}</span>
                    <span className="text-[10px] text-gray-400 truncate block">{p.url}</span>
                  </div>
                  <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                </a>
              );
            })}
          </div>
        </div>
      )}

      {/* Non trouvés */}
      {notFound.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Non trouvé</h4>
          <div className="flex flex-wrap gap-1.5">
            {notFound.map((p, i) => (
              <span key={i} className="inline-flex items-center gap-1 px-2 py-1 text-xs text-gray-500 bg-gray-800/50 rounded border border-gray-800">
                <XCircleIcon className="w-3 h-3" />
                {p.platform}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
