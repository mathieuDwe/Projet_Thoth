import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import { UserCircleIcon, EnvelopeIcon, CalendarDaysIcon, ClockIcon } from '@heroicons/react/24/outline';

export default function Profile() {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  if (!isAuthenticated) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center">
        <Card>
          <p className="text-gray-400 mb-4">Vous n'êtes pas connecté</p>
          <Button onClick={() => navigate('/login')}>Se connecter</Button>
        </Card>
      </div>
    );
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Profil</h1>
        <p className="text-sm text-gray-500 mt-1">Vos informations de compte</p>
      </div>

      {/* User card */}
      <Card>
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
          {/* Avatar */}
          <div className="w-20 h-20 rounded-full bg-emerald-500/20 border-2 border-emerald-500/30 flex items-center justify-center flex-shrink-0">
            <span className="text-emerald-400 font-bold text-3xl uppercase">
              {user?.username?.charAt(0) || '?'}
            </span>
          </div>

          {/* Info */}
          <div className="flex-1 text-center sm:text-left space-y-3">
            <div>
              <h2 className="text-xl font-bold text-gray-100">{user?.username}</h2>
              <Badge severity="success" size="sm" dot>Compte actif</Badge>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-gray-400">
                <EnvelopeIcon className="w-4 h-4 text-gray-500" />
                <span>{user?.email}</span>
              </div>
              <div className="flex items-center gap-2 text-gray-400">
                <CalendarDaysIcon className="w-4 h-4 text-gray-500" />
                <span>Inscrit le {formatDate(user?.created_at)}</span>
              </div>
              {user?.last_login && (
                <div className="flex items-center gap-2 text-gray-400">
                  <ClockIcon className="w-4 h-4 text-gray-500" />
                  <span>Dernière connexion {formatDate(user?.last_login)}</span>
                </div>
              )}
            </div>

            <div className="pt-2">
              <Button
                variant="danger"
                size="sm"
                onClick={() => { logout(); navigate('/login'); }}
              >
                Déconnexion
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
