import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import ServiceReports from '../../components/reports/ServiceReports';
import api from '../../services/api';
import {
  UserGroupIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon,
  PhotoIcon,
  NewspaperIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline';

export default function PersonFinder() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) { setError('Entrez un nom'); return; }
    setError('');
    setLoading(true);
    setResult(null);
    try {
      const data = await api.post('/investigate/global', { username: trimmed });
      const pfData = data?.data?.results?.person_finder || {};
      setResult({
        reportId: data.report_id,
        target: trimmed,
        success: pfData.success,
        data: pfData.data,
        summary: pfData.summary,
        error: pfData.error,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
          <UserGroupIcon className="w-6 h-6 text-amber-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Person Finder</h1>
          <p className="text-sm text-gray-500">
            Recherchez des images et articles sur une personne dans tout le web
          </p>
        </div>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
              Nom / Pseudo
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => { setName(e.target.value); setError(''); }}
              className="input-soc text-base"
              placeholder="Jean Dupont, johndoe..."
              autoFocus
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <Button type="submit" size="lg" loading={loading} className="w-full sm:w-auto">
            {loading ? 'Recherche...' : 'Rechercher la personne'}
          </Button>
        </form>
      </Card>

      {result && (
        <>
          <Card>
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Résultat</h3>
            {result.success && result.data ? (
              <div className="space-y-6">
                <div className="flex items-center gap-2 text-emerald-400">
                  <CheckCircleIcon className="w-5 h-5" />
                  <span className="font-medium">Recherche terminée</span>
                </div>
                {result.summary && <p className="text-sm text-gray-400">{result.summary}</p>}

                {/* Images */}
                {result.data.images?.results?.length > 0 && (
                  <div>
                    <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
                      <PhotoIcon className="w-4 h-4 text-amber-400" />
                      Images ({result.data.images.count})
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {result.data.images.results.slice(0, 9).map((img, i) => (
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
                            onError={(e) => { e.target.src = ''; e.target.className = 'hidden'; }}
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
                {result.data.articles?.results?.length > 0 && (
                  <div>
                    <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
                      <NewspaperIcon className="w-4 h-4 text-blue-400" />
                      Articles ({result.data.articles.count})
                    </h4>
                    <div className="space-y-2">
                      {result.data.articles.results.slice(0, 10).map((article, i) => (
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
                            <span className="text-[10px] text-gray-600 uppercase tracking-wider">
                              {article.source}
                            </span>
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
                {result.data.wikipedia?.results?.length > 0 && (
                  <div>
                    <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
                      <DocumentTextIcon className="w-4 h-4 text-emerald-400" />
                      Wikipedia ({result.data.wikipedia.count})
                    </h4>
                    <div className="space-y-2">
                      {result.data.wikipedia.results.map((article, i) => (
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

                {!result.data.images?.results?.length && !result.data.articles?.results?.length && (
                  <p className="text-sm text-gray-500">Aucun résultat trouvé pour cette personne</p>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-red-400">
                <XCircleIcon className="w-5 h-5" />
                <span>{result.error || 'Service indisponible'}</span>
              </div>
            )}
          </Card>

          <div className="flex items-center justify-between">
            <Button variant="ghost" onClick={() => { setResult(null); setName(''); }}>
              Nouvelle recherche
            </Button>
            {result.reportId && (
              <Button
                variant="primary"
                size="lg"
                onClick={() => navigate(`/reports/${result.reportId}`)}
                icon={DocumentTextIcon}
              >
                Voir le rapport complet
              </Button>
            )}
          </div>
        </>
      )}

      <ServiceReports serviceName="person_finder" />
    </div>
  );
}
