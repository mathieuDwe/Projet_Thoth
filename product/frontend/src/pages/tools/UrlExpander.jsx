import { useState } from 'react';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import api from '../../services/api';
import {
  LinkIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline';

export default function UrlExpander() {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) { setError('Entrez une URL'); return; }
    setError('');
    setLoading(true);
    setResult(null);
    try {
      const data = await api.post('/url-expander/preview', { domain: trimmed });
      setResult({
        success: data.success,
        data: data.data,
        summary: data.summary,
        error: data.error,
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
        <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20">
          <LinkIcon className="w-6 h-6 text-rose-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">URL Expander</h1>
          <p className="text-sm text-gray-500">Déroulez les URLs raccourcies et prévisualisez la destination finale</p>
        </div>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
              URL à analyser
            </label>
            <input
              type="url"
              value={url}
              onChange={(e) => { setUrl(e.target.value); setError(''); }}
              className="input-soc text-base"
              placeholder="https://bit.ly/xxx ou https://t.co/xxx"
              autoFocus
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <Button type="submit" size="lg" loading={loading} className="w-full sm:w-auto">
            {loading ? 'Analyse...' : 'Dérouler'}
          </Button>
        </form>
      </Card>

      {result && result.success && result.data && (
        <div className="space-y-4">
          <Card>
            <div className="flex items-center gap-2 mb-4">
              {result.data.is_shortened && (
                <span className="px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  URL raccourcie
                </span>
              )}
              <span className="text-xs text-gray-500">{result.data.redirect_count} redirection(s)</span>
            </div>

            {result.data.preview && (
              <div className="p-4 rounded-lg bg-gray-800/50 border border-gray-700/50 mb-4">
                {result.data.preview.title && (
                  <p className="text-sm font-medium text-gray-200">{result.data.preview.title}</p>
                )}
                {result.data.preview.description && (
                  <p className="text-xs text-gray-400 mt-1">{result.data.preview.description}</p>
                )}
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-[10px] text-gray-600">{result.data.preview.domain}</span>
                  {result.data.preview.status_code && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-500">
                      HTTP {result.data.preview.status_code}
                    </span>
                  )}
                </div>
              </div>
            )}

            {result.data.chain?.length > 1 && (
              <div>
                <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
                  <ArrowPathIcon className="w-4 h-4 text-rose-400" />
                  Chaîne de redirection ({result.data.chain.length} étapes)
                </h4>
                <div className="space-y-1">
                  {result.data.chain.map((r, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-gray-800/30 border border-gray-700/30">
                      <span className="text-xs text-gray-600 w-5">{i + 1}.</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${r.status_code < 300 ? 'text-emerald-400 bg-emerald-500/10' : r.status_code === 0 ? 'text-red-400 bg-red-500/10' : 'text-amber-400 bg-amber-500/10'}`}>
                        {r.status_code || 'ERR'}
                      </span>
                      <span className="text-xs text-gray-400 truncate flex-1">{r.url}</span>
                      {i < result.data.chain.length - 1 && (
                        <ArrowPathIcon className="w-3 h-3 text-gray-600 flex-shrink-0" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.data.final_url && (
              <a
                href={result.data.final_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 mt-4 px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-sm text-rose-400 hover:bg-rose-500/20 transition-all w-fit"
              >
                Ouvrir la destination finale
                <ArrowTopRightOnSquareIcon className="w-4 h-4" />
              </a>
            )}
          </Card>
        </div>
      )}

      {result && !result.success && (
        <Card><p className="text-sm text-red-400">{result.error || 'Erreur'}</p></Card>
      )}
    </div>
  );
}
