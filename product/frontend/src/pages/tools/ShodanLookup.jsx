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
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

const MODE_OPTIONS = [
  { value: 'ip', label: 'IP Lookup', placeholder: '8.8.8.8' },
  { value: 'domain', label: 'Domain Lookup', placeholder: 'example.com' },
  { value: 'query', label: 'Search', placeholder: 'port:22 country:FR' },
];

export default function ShodanLookup() {
  const navigate = useNavigate();
  const [mode, setMode] = useState('ip');
  const [input, setInput] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const currentMode = MODE_OPTIONS.find(m => m.value === mode) || MODE_OPTIONS[0];

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) { setError('Entrez une valeur'); return; }
    setError('');
    setLoading(true);
    setResult(null);
    try {
      const endpoints = {
        ip: '/shodan-lookup/ip',
        domain: '/shodan-lookup/domain',
        query: '/shodan-lookup/query',
      };
      const payloads = {
        ip: { ip: trimmed },
        domain: { domain: trimmed },
        query: { username: trimmed },
      };
      const body = await api.post(endpoints[mode], payloads[mode]);
      setResult({
        success: body?.success,
        data: body?.data,
        summary: body?.summary,
        error: body?.error,
      });
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20">
          <GlobeAltIcon className="w-6 h-6 text-red-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Shodan Lookup</h1>
          <p className="text-sm text-gray-500">
            Moteur de recherche des appareils connectés : ports ouverts, services, vulnérabilités
          </p>
        </div>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex gap-2">
            {MODE_OPTIONS.map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => { setMode(opt.value); setError(''); setResult(null); }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  mode === opt.value
                    ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                    : 'bg-gray-800 text-gray-500 hover:text-gray-300 border border-transparent'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
              {currentMode.label}
            </label>
            <input
              type="text"
              value={input}
              onChange={(e) => { setInput(e.target.value); setError(''); }}
              className="input-soc text-base"
              placeholder={currentMode.placeholder}
              autoFocus
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <Button type="submit" size="lg" loading={loading} className="w-full sm:w-auto">
            {loading ? 'Recherche...' : 'Lancer la recherche'}
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
                  <pre className="text-xs text-emerald-400/80 bg-gray-950 p-4 rounded-lg overflow-x-auto max-h-96">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-red-400">
                {result.error?.includes('SHODAN_API_KEY') ? (
                  <>
                    <ExclamationTriangleIcon className="w-5 h-5 flex-shrink-0" />
                    <span>Clé API Shodan non configurée. Ajoutez-la dans <button onClick={() => navigate('/settings')} className="underline hover:text-red-300">Paramètres &gt; Clés API</button></span>
                  </>
                ) : (
                  <>
                    <XCircleIcon className="w-5 h-5 flex-shrink-0" />
                    <span>{result.error || 'Service indisponible'}</span>
                  </>
                )}
              </div>
            )}
          </Card>

          <div className="flex items-center justify-between">
            <Button variant="ghost" onClick={() => { setResult(null); setInput(''); }}>
              Nouvelle recherche
            </Button>
          </div>
        </>
      )}

      <ServiceReports serviceName="shodan_lookup" />
    </div>
  );
}
