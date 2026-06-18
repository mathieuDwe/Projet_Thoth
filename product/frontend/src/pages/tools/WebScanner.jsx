import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import ServiceReports from '../../components/reports/ServiceReports';
import api from '../../services/api';
import {
  GlobeAltIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon,
  ShieldCheckIcon,
  CodeBracketIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

export default function WebScanner() {
  const navigate = useNavigate();
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
      const data = await api.post('/web-scanner/scan', { domain: trimmed });
      setResult({
        reportId: null,
        target: trimmed,
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
        <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
          <GlobeAltIcon className="w-6 h-6 text-blue-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Web Scanner</h1>
          <p className="text-sm text-gray-500">Analysez un site web : en-têtes, technologies, sécurité et redirections</p>
        </div>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
              URL du site
            </label>
            <input
              type="text"
              value={url}
              onChange={(e) => { setUrl(e.target.value); setError(''); }}
              className="input-soc text-base"
              placeholder="example.com ou https://example.com"
              autoFocus
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <Button type="submit" size="lg" loading={loading} className="w-full sm:w-auto">
            {loading ? 'Analyse...' : 'Scanner'}
          </Button>
        </form>
      </Card>

      {result && result.success && result.data && (
        <div className="space-y-4">
          <Card>
            <div className="flex items-center gap-2 text-emerald-400 mb-4">
              <CheckCircleIcon className="w-5 h-5" />
              <span className="font-medium">HTTP {result.data.status_code}</span>
            </div>
            {result.data.title && (
              <p className="text-sm text-gray-300 mb-4">"{result.data.title}"</p>
            )}
            {result.data.summary && <p className="text-xs text-gray-500">{result.data.summary}</p>}
          </Card>

          {result.data.technologies?.length > 0 && (
            <Card>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
                <CodeBracketIcon className="w-4 h-4 text-blue-400" />
                Technologies ({result.data.technologies.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.data.technologies.map((tech, i) => (
                  <span key={i} className="px-2 py-1 rounded-md bg-gray-800 border border-gray-700 text-xs text-gray-300">
                    {tech.name}
                  </span>
                ))}
              </div>
            </Card>
          )}

          <Card>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
              <ShieldCheckIcon className="w-4 h-4 text-emerald-400" />
              En-têtes de sécurité ({result.data.security_headers_count}/{Object.keys(result.data.security_headers || {}).length})
            </h3>
            <div className="space-y-1">
              {result.data.security_headers && Object.entries(result.data.security_headers).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between p-2 rounded-lg bg-gray-800/30 border border-gray-700/30">
                  <span className="text-xs text-gray-300 font-mono">{key}</span>
                  <span className={`text-xs ${val !== 'missing' ? 'text-emerald-400' : 'text-red-400'}`}>
                    {val !== 'missing' ? 'Présent' : 'Manquant'}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {result.data.redirect_chain?.length > 1 && (
            <Card>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
                <ArrowPathIcon className="w-4 h-4 text-amber-400" />
                Chaîne de redirection ({result.data.redirect_chain.length} étapes)
              </h3>
              <div className="space-y-1">
                {result.data.redirect_chain.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-gray-800/30 border border-gray-700/30">
                    <span className="text-xs text-gray-500 w-6">{i + 1}.</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${r.status_code < 300 ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {r.status_code}
                    </span>
                    <span className="text-xs text-gray-400 truncate">{r.url}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {result && !result.success && (
        <Card>
          <div className="flex items-center gap-2 text-red-400">
            <XCircleIcon className="w-5 h-5" />
            <span>{result.error || 'Service indisponible'}</span>
          </div>
        </Card>
      )}

      <ServiceReports serviceName="web_scanner" />
    </div>
  );
}
