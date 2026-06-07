import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import ServiceReports from '../../components/reports/ServiceReports';
import api from '../../services/api';
import {
  UsersIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

export default function SocialHarvester() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = username.trim();
    if (!trimmed) { setError('Entrez un pseudo'); return; }
    setError('');
    setLoading(true);
    setResult(null);
    try {
      const data = await api.post('/investigate/global', { username: trimmed });
      const socData = data?.data?.results?.social_harvester || {};
      setResult({
        reportId: data.report_id,
        target: trimmed,
        success: socData.success,
        data: socData.data,
        summary: socData.summary,
        error: socData.error,
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
        <div className="p-2 rounded-lg bg-violet-500/10 border border-violet-500/20">
          <UsersIcon className="w-6 h-6 text-violet-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Social Harvester</h1>
          <p className="text-sm text-gray-500">Recherchez un pseudo sur les réseaux sociaux et plateformes publiques</p>
        </div>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
              Pseudo / Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => { setUsername(e.target.value); setError(''); }}
              className="input-soc text-base"
              placeholder="johndoe"
              autoFocus
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <Button type="submit" size="lg" loading={loading} className="w-full sm:w-auto">
            {loading ? 'Recherche...' : 'Rechercher sur les réseaux'}
          </Button>
        </form>
      </Card>

      {result && (
        <>
          <Card>
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Résultat</h3>
            {result.success ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-emerald-400">
                  <CheckCircleIcon className="w-5 h-5" />
                  <span className="font-medium">Recherche terminée</span>
                </div>
                {result.summary && <p className="text-sm text-gray-400">{result.summary}</p>}
                {result.data && (
                  <pre className="text-xs text-emerald-400/80 bg-gray-950 p-4 rounded-lg overflow-x-auto max-h-80">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
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
            <Button variant="ghost" onClick={() => { setResult(null); setUsername(''); }}>
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

      {/* Rapports récents pour ce service */}
      <ServiceReports serviceName="social_harvester" />
    </div>
  );
}
