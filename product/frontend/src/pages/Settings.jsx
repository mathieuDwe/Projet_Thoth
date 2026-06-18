import { useState, useEffect } from 'react';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Spinner from '../components/common/Spinner';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import {
  Cog6ToothIcon,
  ServerIcon,
  ShieldCheckIcon,
  KeyIcon,
  LockClosedIcon,
} from '@heroicons/react/24/outline';

export default function Settings() {
  const { user, isAuthenticated } = useAuth();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Changer mot de passe
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [pwdMsg, setPwdMsg] = useState(null);
  const [pwdLoading, setPwdLoading] = useState(false);

  useEffect(() => {
    async function fetchSettings() {
      try {
        const data = await api.get('/settings');
        setSettings(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchSettings();
  }, []);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (!currentPwd || !newPwd) {
      setPwdMsg({ type: 'error', text: 'Remplissez tous les champs' });
      return;
    }
    setPwdLoading(true);
    setPwdMsg(null);
    try {
      const res = await api.patch('/settings/password', {
        current_password: currentPwd,
        new_password: newPwd,
      });
      setPwdMsg({ type: 'success', text: res.message || 'Mot de passe modifié' });
      setCurrentPwd('');
      setNewPwd('');
    } catch (err) {
      setPwdMsg({ type: 'error', text: err.message });
    } finally {
      setPwdLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" text="Chargement des paramètres..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-12">
        <Card>
          <p className="text-red-400 text-center">{error}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Paramètres</h1>
        <p className="text-sm text-gray-500 mt-1">
          Configuration de la plateforme OSINT Thoth
        </p>
      </div>

      {/* Informations générales */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Cog6ToothIcon className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Informations générales
          </h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          <div className="px-4 py-3 rounded-lg bg-gray-800/30 border border-gray-800/50">
            <span className="block text-xs text-gray-500 uppercase tracking-wider mb-1">Version</span>
            <span className="text-gray-200 font-mono">{settings?.version || '—'}</span>
          </div>
          <div className="px-4 py-3 rounded-lg bg-gray-800/30 border border-gray-800/50">
            <span className="block text-xs text-gray-500 uppercase tracking-wider mb-1">Environnement</span>
            <Badge severity={settings?.environment === 'production' ? 'success' : 'warning'} size="sm" dot>
              {settings?.environment || '—'}
            </Badge>
          </div>
          <div className="px-4 py-3 rounded-lg bg-gray-800/30 border border-gray-800/50">
            <span className="block text-xs text-gray-500 uppercase tracking-wider mb-1">Base de données</span>
            <span className="text-gray-200 font-mono text-xs">
              {settings?.database?.type || '—'} ({settings?.database?.driver || '—'})
            </span>
          </div>
          <div className="px-4 py-3 rounded-lg bg-gray-800/30 border border-gray-800/50">
            <span className="block text-xs text-gray-500 uppercase tracking-wider mb-1">Authentification</span>
            <span className="text-gray-200 font-mono text-xs">{settings?.auth?.method || '—'}</span>
          </div>
        </div>
      </Card>

      {/* Microservices */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <ServerIcon className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Microservices
          </h3>
        </div>
        <div className="space-y-2">
          {settings?.services?.length > 0 ? settings.services.map((svc) => (
            <div
              key={svc.name}
              className="flex items-center justify-between px-4 py-3 rounded-lg bg-gray-800/30 border border-gray-800/50"
            >
              <div className="flex items-center gap-3">
                <span className={`w-2 h-2 rounded-full ${
                  svc.status === 'online' ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50' :
                  svc.status === 'degraded' ? 'bg-amber-500' : 'bg-gray-600'
                }`} />
                <div>
                  <span className="text-sm font-medium text-gray-200">{svc.name}</span>
                  <span className="text-xs text-gray-500 ml-2 font-mono">:{svc.port}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500 font-mono">v{svc.version || '—'}</span>
                <Badge severity={svc.status === 'online' ? 'success' : svc.status === 'degraded' ? 'warning' : 'default'} size="sm">
                  {svc.status === 'online' ? 'Actif' : svc.status === 'degraded' ? 'Dégradé' : 'Inactif'}
                </Badge>
              </div>
            </div>
          )) : (
            <p className="text-sm text-gray-500 text-center py-4">Aucun service disponible</p>
          )}
        </div>
      </Card>

      {/* Sécurité */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheckIcon className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Sécurité
          </h3>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between px-4 py-3 rounded-lg bg-gray-800/30 border border-gray-800/50">
            <span className="text-gray-300">Chiffrement des mots de passe</span>
            <Badge severity="success" size="sm">bcrypt</Badge>
          </div>
          <div className="flex items-center justify-between px-4 py-3 rounded-lg bg-gray-800/30 border border-gray-800/50">
            <span className="text-gray-300">Type de token</span>
            <Badge severity="info" size="sm">JWT (HS256)</Badge>
          </div>
          <div className="flex items-center justify-between px-4 py-3 rounded-lg bg-gray-800/30 border border-gray-800/50">
            <span className="text-gray-300">Expiration du token</span>
            <Badge severity="info" size="sm">{settings?.auth?.token_expiry || '24 heures'}</Badge>
          </div>
          <div className="flex items-center justify-between px-4 py-3 rounded-lg bg-gray-800/30 border border-gray-800/50">
            <span className="text-gray-300">Utilisateurs enregistrés</span>
            <Badge severity="info" size="sm">{settings?.auth?.users_count || 0}</Badge>
          </div>
        </div>
      </Card>

      {/* Clés API */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <KeyIcon className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Clés API configurées
          </h3>
        </div>
        <div className="space-y-2 text-sm">
          {settings?.api_keys_configured && Object.entries(settings.api_keys_configured).map(([key, configured]) => (
            <div key={key} className="flex items-center justify-between px-4 py-3 rounded-lg bg-gray-800/30 border border-gray-800/50">
              <span className="text-gray-300 capitalize">{key}</span>
              <Badge severity={configured ? 'success' : 'default'} size="sm">
                {configured ? 'Configurée' : 'Non configurée'}
              </Badge>
            </div>
          ))}
        </div>
      </Card>

      {/* Changer le mot de passe */}
      {isAuthenticated && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <LockClosedIcon className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              Changer le mot de passe
            </h3>
          </div>
          <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                Mot de passe actuel
              </label>
              <input
                type="password"
                value={currentPwd}
                onChange={(e) => setCurrentPwd(e.target.value)}
                className="input-soc text-sm"
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                Nouveau mot de passe
              </label>
              <input
                type="password"
                value={newPwd}
                onChange={(e) => setNewPwd(e.target.value)}
                className="input-soc text-sm"
                placeholder="Au moins 6 caractères"
                autoComplete="new-password"
              />
            </div>

            {pwdMsg && (
              <div className={`px-3 py-2 rounded-lg text-xs ${
                pwdMsg.type === 'success'
                  ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                  : 'bg-red-500/10 border border-red-500/20 text-red-400'
              }`}>
                {pwdMsg.text}
              </div>
            )}

            <Button type="submit" loading={pwdLoading} size="md">
              {pwdLoading ? 'Modification...' : 'Modifier le mot de passe'}
            </Button>
          </form>
        </Card>
      )}
    </div>
  );
}
