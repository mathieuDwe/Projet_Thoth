import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import ServiceReports from '../../components/reports/ServiceReports';
import api from '../../services/api';
import {
  EnvelopeIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon,
  ServerIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline';

export default function EmailInvestigator() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) { setError('Entrez un email'); return; }
    if (!trimmed.includes('@')) { setError('Email invalide'); return; }
    setError('');
    setLoading(true);
    setResult(null);
    try {
      const data = await api.post('/email-investigator/analyze', { email: trimmed });
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
        <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
          <EnvelopeIcon className="w-6 h-6 text-cyan-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Email Investigator</h1>
          <p className="text-sm text-gray-500">Analysez une adresse email : MX, Gravatar, fournisseur et sécurité</p>
        </div>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
              Adresse email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setError(''); }}
              className="input-soc text-base"
              placeholder="john@example.com"
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
                <p className="text-xs text-gray-500 uppercase tracking-wider">Domaine</p>
                <p className="text-sm font-medium text-gray-200 mt-1">{result.data.domain}</p>
              </div>
              <div className="p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                <p className="text-xs text-gray-500 uppercase tracking-wider">Fournisseur</p>
                <p className="text-sm font-medium text-gray-200 mt-1">{result.data.provider || 'Inconnu / Personnel'}</p>
              </div>
              <div className="p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                <p className="text-xs text-gray-500 uppercase tracking-wider">Serveurs MX</p>
                <p className="text-sm font-medium text-gray-200 mt-1">
                  {result.data.has_mx_records ? `${result.data.mx_records.length} serveur(s)` : 'Aucun'}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                <p className="text-xs text-gray-500 uppercase tracking-wider">Gravatar</p>
                <p className="text-sm font-medium text-gray-200 mt-1">
                  {result.data.gravatar?.has_avatar ? 'Existe' : 'Non trouvé'}
                </p>
              </div>
            </div>
          </Card>

          {result.data.mx_records?.length > 0 && (
            <Card>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
                <ServerIcon className="w-4 h-4 text-cyan-400" />
                Serveurs MX
              </h3>
              <div className="space-y-2">
                {result.data.mx_records.map((mx, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-gray-800/30 border border-gray-700/30">
                    <span className="text-sm text-gray-200">{mx.exchange}</span>
                    <span className="text-xs text-gray-500">Priorité {mx.preference}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {result.data.gravatar?.has_avatar && (
            <Card>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3">
                <UserCircleIcon className="w-4 h-4 text-cyan-400" />
                Gravatar
              </h3>
              <div className="flex items-center gap-4">
                <img
                  src={result.data.gravatar.avatar_url}
                  alt="Avatar"
                  className="w-16 h-16 rounded-full border-2 border-gray-700"
                />
                <div>
                  <p className="text-sm text-gray-200">Profil Gravatar trouvé</p>
                  <a
                    href={result.data.gravatar.profile_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-cyan-400 hover:text-cyan-300"
                  >
                    Voir le profil →
                  </a>
                </div>
              </div>
            </Card>
          )}

          {result.data.social_handles?.length > 0 && (
            <Card>
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Pistes de pseudos</h3>
              <div className="flex flex-wrap gap-2">
                {result.data.social_handles.map((h, i) => (
                  <span key={i} className="px-2 py-1 rounded-md bg-gray-800 border border-gray-700 text-xs text-gray-300">
                    {h.handle}
                  </span>
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

      <ServiceReports serviceName="email_investigator" />
    </div>
  );
}
