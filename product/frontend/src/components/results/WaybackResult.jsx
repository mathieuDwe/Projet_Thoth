import { ClockIcon } from '@heroicons/react/24/outline';

export default function WaybackResult({ data }) {
  if (!data) return null;
  const snapshots = data.snapshots || [];
  return (
    <div className="space-y-2">
      <p className="text-sm text-gray-400">{data.total} snapshot(s)</p>
      {snapshots.slice(0, 5).map((s, i) => (
        <a key={i} href={s.archive_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 p-2 rounded bg-gray-800/50 border border-gray-700/50 hover:border-purple-500/30 transition-all text-xs">
          <ClockIcon className="w-3 h-3 text-purple-400" />
          <span className="text-gray-300">{s.date || s.timestamp}</span>
          <span className="text-gray-500">HTTP {s.status_code}</span>
        </a>
      ))}
    </div>
  );
}
