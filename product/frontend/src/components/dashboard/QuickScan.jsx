import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../common/Card';
import Button from '../common/Button';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

export default function QuickScan() {
  const navigate = useNavigate();
  const [target, setTarget] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = target.trim();

    if (!trimmed) {
      setError('Veuillez entrer une cible (domaine, IP, email, URL)');
      return;
    }

    // Validation simple
    if (trimmed.length < 3) {
      setError('La cible doit contenir au moins 3 caractères');
      return;
    }

    setError('');
    navigate(`/scan?target=${encodeURIComponent(trimmed)}`);
  };

  return (
    <Card>
      <div className="flex items-center gap-2 mb-4">
        <MagnifyingGlassIcon className="w-4 h-4 text-emerald-400" />
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Lancement rapide
        </h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <div className="relative">
            <input
              type="text"
              value={target}
              onChange={(e) => {
                setTarget(e.target.value);
                if (error) setError('');
              }}
              placeholder="Cible : domaine, IP, email ou URL..."
              className="input-soc pr-24"
              autoComplete="off"
              spellCheck={false}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-gray-600 font-mono">
              OSINT
            </span>
          </div>
          {error && (
            <p className="mt-1.5 text-xs text-red-400">{error}</p>
          )}
        </div>

        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">
            Domaines, IPv4, emails, URLs
          </span>
          <Button type="submit" size="md">
            Lancer l'enquête
          </Button>
        </div>
      </form>
    </Card>
  );
}
