import {
  PhotoIcon,
  NewspaperIcon,
  DocumentTextIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline';

export default function PersonResult({ data }) {
  if (!data) return null;

  const images = data.images?.results || [];
  const articles = data.articles?.results || [];
  const wikipedia = data.wikipedia?.results || [];

  return (
    <div className="space-y-6">
      {/* Images */}
      {images.length > 0 && (
        <div>
          <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
            <PhotoIcon className="w-4 h-4 text-amber-400" />
            Images ({data.images.count || images.length})
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {images.slice(0, 9).map((img, i) => (
              <a
                key={i}
                href={img.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group relative aspect-square rounded-lg overflow-hidden bg-gray-800 border border-gray-700 hover:border-amber-500/50 transition-all"
              >
                <img
                  src={img.thumbnail}
                  alt={img.alt}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
                  <ArrowTopRightOnSquareIcon className="w-5 h-5 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Articles */}
      {articles.length > 0 && (
        <div>
          <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
            <NewspaperIcon className="w-4 h-4 text-blue-400" />
            Articles ({data.articles.count || articles.length})
          </h4>
          <div className="space-y-2">
            {articles.slice(0, 10).map((article, i) => (
              <a
                key={i}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-3 rounded-lg bg-gray-800/50 border border-gray-700/50 hover:border-gray-600 transition-all group"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-gray-200 group-hover:text-amber-400 transition-colors">
                    {article.title}
                  </p>
                  <ArrowTopRightOnSquareIcon className="w-4 h-4 text-gray-600 group-hover:text-amber-400 flex-shrink-0 mt-0.5" />
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] text-gray-600 uppercase tracking-wider">{article.source}</span>
                  {article.snippet && (
                    <span className="text-xs text-gray-500 truncate">{article.snippet.slice(0, 100)}</span>
                  )}
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Wikipedia */}
      {wikipedia.length > 0 && (
        <div>
          <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
            <DocumentTextIcon className="w-4 h-4 text-emerald-400" />
            Wikipedia ({data.wikipedia.count || wikipedia.length})
          </h4>
          <div className="space-y-2">
            {wikipedia.map((article, i) => (
              <a
                key={i}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-3 rounded-lg bg-gray-800/50 border border-gray-700/50 hover:border-emerald-500/30 transition-all group"
              >
                <p className="text-sm font-medium text-gray-200 group-hover:text-emerald-400 transition-colors">
                  {article.title}
                </p>
                {article.snippet && (
                  <p className="text-xs text-gray-500 mt-1">{article.snippet}...</p>
                )}
              </a>
            ))}
          </div>
        </div>
      )}

      {!images.length && !articles.length && (
        <p className="text-sm text-gray-500">Aucun résultat trouvé</p>
      )}
    </div>
  );
}
