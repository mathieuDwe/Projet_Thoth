import { useState } from 'react';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import api from '../../services/api';
import {
  PhoneIcon,
  GlobeEuropeAfricaIcon,
  HashtagIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline';

export default function PhoneAnalyzer() {
  const [phone, setPhone] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = phone.trim();
    if (!trimmed) { setError('Entrez un numéro'); return; }
    setError('');
    setLoading(true);
    setResult(null);
    try {
      const data = await api.post('/phone-analyzer/analyze', { username: trimmed });
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
        <div className="p-2 rounded-lg bg-orange-500/10 border border-orange-500/20">
          <PhoneIcon className="w-6 h-6 text-orange-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Phone Analyzer</h1>
          <p className="text-sm text-gray-500">Analyse d'un numéro de téléphone : pays, format, indicatif</p>
        </div>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
              Numéro de téléphone
            </label>
            <input
              type="text"
              value={phone}
              onChange={(e) => { setPhone(e.target.value); setError(''); }}
              className="input-soc text-base"
              placeholder="+33612345678 ou 0612345678"
              autoFocus
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <Button type="submit" size="lg" loading={loading} className="w-full sm:w-auto">
            {loading ? 'Analyse...' : 'Analyser'}
          </Button>
        </form>
      </Card>

      {result && result.success && result.data && (
        <div className="space-y-4">
          <Card>
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">Informations</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                <p className="flex items-center gap-1 text-xs text-gray-500 uppercase tracking-wider">
                  <GlobeEuropeAfricaIcon className="w-3 h-3" /> Pays
                </p>
                <p className="text-sm font-medium text-gray-200 mt-1">
                  {result.data.country ? `${result.data.country.name} (${result.data.country.code})` : 'Non détecté'}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                <p className="flex items-center gap-1 text-xs text-gray-500 uppercase tracking-wider">
                  <HashtagIcon className="w-3 h-3" /> International
                </p>
                <p className="text-sm font-medium text-gray-200 mt-1">{result.data.international_format}</p>
              </div>
              {result.data.national_format && (
                <div className="p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                  <p className="text-xs text-gray-500 uppercase tracking-wider">National</p>
                  <p className="text-sm font-medium text-gray-200 mt-1">{result.data.national_format}</p>
                </div>
              )}
              <div className="p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                <p className="text-xs text-gray-500 uppercase tracking-wider">Longueur</p>
                <p className="text-sm font-medium text-gray-200 mt-1">{result.data.length} chiffres</p>
              </div>
            </div>
          </Card>

          {result.data.online_search_links?.length > 0 && (
            <Card>
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Recherches en ligne</h3>
              <div className="space-y-2">
                {result.data.online_search_links.map((link, i) => (
                  <a
                    key={i}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-2 rounded-lg bg-gray-800/30 border border-gray-700/30 hover:border-orange-500/30 transition-all group"
                  >
                    <span className="text-sm text-gray-400">{link.source}</span>
                    <ArrowTopRightOnSquareIcon className="w-4 h-4 text-gray-600 group-hover:text-orange-400" />
                  </a>
                ))}
              </div>
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
