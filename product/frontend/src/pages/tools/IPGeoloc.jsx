import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import ServiceReports from '../../components/reports/ServiceReports';
import api from '../../services/api';
import {
  MapPinIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

export default function IPGeoloc() {
  const navigate = useNavigate();
  const [ip, setIp] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = ip.trim();
    if (!trimmed) { setError('Entrez une adresse IP'); return; }
    setError('');
    setLoading(true);
    setResult(null);
    try {
      const data = await api.post('/investigate/global', { ip: trimmed });
      const geoData = data?.data?.results?.ip_geolocation || {};
      setResult({
        reportId: data.report_id,
        target: trimmed,
        success: geoData.success,
        data: geoData.data,
        summary: geoData.summary,
        error: geoData.error,
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
          <MapPinIcon className="w-6 h-6 text-amber-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">IP Geolocation</h1>
          <p className="text-sm text-gray-500">Géolocalisation, FAI, détection VPN/proxy et informations WHOIS sur une adresse IP</p>
        </div>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
              Adresse IP
            </label>
            <input
              type="text"
              value={ip}
              onChange={(e) => { setIp(e.target.value); setError(''); }}
              className="input-soc text-base"
              placeholder="8.8.8.8"
              autoFocus
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <Button type="submit" size="lg" loading={loading} className="w-full sm:w-auto">
            {loading ? 'Analyse...' : 'Localiser l\'IP'}
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
                  <span className="font-medium">Analyse terminée</span>
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
            <Button variant="ghost" onClick={() => { setResult(null); setIp(''); }}>
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
      <ServiceReports serviceName="ip_geoloc" />
    </div>
  );
}
