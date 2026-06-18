import { ServerIcon, UserCircleIcon } from '@heroicons/react/24/outline';

export default function EmailResult({ data }) {
  if (!data) return null;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded bg-gray-800/50 border border-gray-700/50">
          <p className="text-xs text-gray-500">Domaine</p>
          <p className="text-sm font-medium text-gray-200">{data.domain}</p>
        </div>
        <div className="p-2 rounded bg-gray-800/50 border border-gray-700/50">
          <p className="text-xs text-gray-500">Fournisseur</p>
          <p className="text-sm font-medium text-gray-200">{data.provider || 'Inconnu'}</p>
        </div>
        <div className="p-2 rounded bg-gray-800/50 border border-gray-700/50">
          <p className="text-xs text-gray-500">Serveurs MX</p>
          <p className="text-sm font-medium text-gray-200">{data.has_mx_records ? `${data.mx_records?.length || 0}` : 'Non'}</p>
        </div>
        <div className="p-2 rounded bg-gray-800/50 border border-gray-700/50">
          <p className="text-xs text-gray-500">Gravatar</p>
          <p className="text-sm font-medium text-gray-200">{data.gravatar?.has_avatar ? 'Oui' : 'Non'}</p>
        </div>
      </div>
    </div>
  );
}
