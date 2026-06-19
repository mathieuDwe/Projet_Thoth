import { useState } from 'react';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import api from '../../services/api';
import {
  DocumentTextIcon,
  AtSymbolIcon,
  LinkIcon,
  GlobeAltIcon,
  PhoneIcon,
  ServerIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';

export default function TextAnalyzer() {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [deep, setDeep] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim()) { setError('Entrez un texte'); return; }
    if (text.length < 3) { setError('Texte trop court'); return; }
    setError('');
    setLoading(true);
    setResult(null);
    try {
      const endpoint = deep ? '/text-analyzer/deep' : '/text-analyzer/analyze';
      const data = await api.post(endpoint, { username: text });
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

  const copyToClipboard = (items) => {
    navigator.clipboard.writeText(items.join('\n'));
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-teal-500/10 border border-teal-500/20">
          <DocumentTextIcon className="w-6 h-6 text-teal-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Text Analyzer</h1>
          <p className="text-sm text-gray-500">Extraction d'emails, URLs, IPs, téléphones, crypto et domaines depuis un texte</p>
        </div>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
              Texte brut
            </label>
            <textarea
              value={text}
              onChange={(e) => { setText(e.target.value); setError(''); }}
              className="input-soc text-sm h-40 resize-y"
              placeholder="Collez un texte, un email, un document HTML... pour en extraire les informations..."
            />
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={deep}
                onChange={(e) => setDeep(e.target.checked)}
                className="rounded border-gray-600 bg-gray-800 text-teal-500 focus:ring-teal-500"
              />
              <span className="text-xs text-gray-500">Analyse approfondie (géolocalisation IP)</span>
            </label>
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <Button type="submit" size="lg" loading={loading} className="w-full sm:w-auto">
            {loading ? 'Analyse...' : 'Analyser le texte'}
          </Button>
        </form>
      </Card>

      {result && result.success && result.data && (
        <div className="space-y-4">
          <Card>
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
              Résultats
            </h3>
            <div className="flex flex-wrap gap-2 mb-4">
              {Object.entries(result.data.stats || {}).filter(([, v]) => v > 0).map(([key, val]) => (
                <span key={key} className="px-2 py-1 rounded-md bg-gray-800 border border-gray-700 text-xs text-gray-300">
                  {key}: {val}
                </span>
              ))}
            </div>
          </Card>

          {result.data.emails?.length > 0 && (
            <Card>
              <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-2">
                <AtSymbolIcon className="w-4 h-4 text-teal-400" /> Emails ({result.data.emails.length})
              </h4>
              <div className="space-y-1">
                {result.data.emails.map((e, i) => (
                  <div key={i} className="text-xs text-gray-400 font-mono bg-gray-800/30 px-2 py-1 rounded">{e}</div>
                ))}
              </div>
            </Card>
          )}

          {result.data.urls?.length > 0 && (
            <Card>
              <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-2">
                <LinkIcon className="w-4 h-4 text-teal-400" /> URLs ({result.data.urls.length})
              </h4>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {result.data.urls.map((u, i) => (
                  <a key={i} href={u.url} target="_blank" rel="noopener noreferrer" className="block text-xs text-blue-400 hover:text-blue-300 font-mono bg-gray-800/30 px-2 py-1 rounded truncate">
                    {u.url}
                  </a>
                ))}
              </div>
            </Card>
          )}

          {result.data.ips?.length > 0 && (
            <Card>
              <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-2">
                <ServerIcon className="w-4 h-4 text-teal-400" /> IPs ({result.data.ips.length})
              </h4>
              <div className="space-y-1">
                {result.data.ips.map((ip, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-xs text-gray-400 font-mono bg-gray-800/30 px-2 py-1 rounded">{ip}</span>
                    {result.data.ip_geolocation?.[ip] && (
                      <span className="text-[10px] text-gray-500">
                        {result.data.ip_geolocation[ip].country} · {result.data.ip_geolocation[ip].isp}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {result.data.phones?.length > 0 && (
            <Card>
              <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-2">
                <PhoneIcon className="w-4 h-4 text-teal-400" /> Téléphones ({result.data.phones.length})
              </h4>
              <div className="space-y-1">
                {result.data.phones.map((p, i) => (
                  <div key={i} className="text-xs text-gray-400 font-mono bg-gray-800/30 px-2 py-1 rounded">{p}</div>
                ))}
              </div>
            </Card>
          )}

          {result.data.domains?.length > 0 && (
            <Card>
              <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-2">
                <GlobeAltIcon className="w-4 h-4 text-teal-400" /> Domaines ({result.data.domains.length})
              </h4>
              <div className="flex flex-wrap gap-1">
                {result.data.domains.map((d, i) => (
                  <span key={i} className="text-xs text-gray-400 font-mono bg-gray-800/30 px-2 py-1 rounded">{d}</span>
                ))}
              </div>
            </Card>
          )}

          {result.data.crypto && Object.keys(result.data.crypto).length > 0 && (
            <Card>
              <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-2">
                <CurrencyDollarIcon className="w-4 h-4 text-teal-400" /> Crypto
              </h4>
              {result.data.crypto.bitcoin?.length > 0 && (
                <div className="mb-1">
                  <p className="text-[10px] text-gray-600 uppercase">Bitcoin</p>
                  {result.data.crypto.bitcoin.map((b, i) => (
                    <div key={i} className="text-xs text-gray-400 font-mono bg-gray-800/30 px-2 py-1 rounded">{b}</div>
                  ))}
                </div>
              )}
              {result.data.crypto.ethereum?.length > 0 && (
                <div>
                  <p className="text-[10px] text-gray-600 uppercase">Ethereum</p>
                  {result.data.crypto.ethereum.map((e, i) => (
                    <div key={i} className="text-xs text-gray-400 font-mono bg-gray-800/30 px-2 py-1 rounded">{e}</div>
                  ))}
                </div>
              )}
            </Card>
          )}
        </div>
      )}

      {result && !result.success && (
        <Card><p className="text-sm text-red-400">{result.error || 'Erreur'}</p></Card>
      )}
    </div>
  );
}
