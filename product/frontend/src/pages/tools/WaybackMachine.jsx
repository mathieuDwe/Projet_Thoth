import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import ServiceReports from '../../components/reports/ServiceReports';
import api from '../../services/api';
import {
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon,
  ArrowTopRightOnSquareIcon,
  ArchiveBoxIcon,
} from '@heroicons/react/24/outline';

export default function WaybackMachine() {
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
      const data = await api.post('/wayback-machine/snapshots', { domain: trimmed });
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

  const formatDate = (ts) => {
    if (!ts) return '';
    return `${ts.slice(0, 4)}-${ts.slice(4, 6)}-${ts.slice(6, 8)} ${ts.slice(8, 10)}:${ts.slice(10, 12)}`;
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20">
          <ClockIcon className="w-6 h-6 text-purple-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Wayback Machine</h1>
          <p className="text-sm text-gray-500">Consultez l'historique d'un site web via les archives Internet Archive</p>
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
              placeholder="example.com"
              autoFocus
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <Button type="submit" size="lg" loading={loading} className="w-full sm:w-auto">
            {loading ? 'Recherche...' : 'Chercher dans les archives'}
          </Button>
        </form>
      </Card>

      {result && result.success && result.data && (
        <div className="space-y-4">
          <Card>
            <div className="flex items-center gap-2 text-emerald-400 mb-2">
              <ArchiveBoxIcon className="w-5 h-5" />
              <span className="font-medium">{result.data.total} snapshot(s) trouvé(s)</span>
            </div>
            {result.summary && <p className="text-xs text-gray-500">{result.summary}</p>}
          </Card>

          {result.data.snapshots?.length > 0 && (
            <Card>
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Snapshots</h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {result.data.snapshots.map((snap, i) => (
                  <a
                    key={i}
                    href={snap.archive_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50 border border-gray-700/50 hover:border-purple-500/30 transition-all group"
                  >
                    <div className="flex items-center gap-3">
                      <ClockIcon className="w-4 h-4 text-purple-400 flex-shrink-0" />
                      <div>
                        <p className="text-sm text-gray-200 group-hover:text-purple-400 transition-colors">
                          {formatDate(snap.timestamp)}
                        </p>
                        <p className="text-xs text-gray-500">
                          HTTP {snap.status_code} · {snap.mime_type}
                        </p>
                      </div>
                    </div>
                    <ArrowTopRightOnSquareIcon className="w-4 h-4 text-gray-600 group-hover:text-purple-400" />
                  </a>
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

      <ServiceReports serviceName="wayback_machine" />
    </div>
  );
}
