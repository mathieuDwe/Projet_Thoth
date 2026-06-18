import useDashboard from '../../hooks/useDashboard';
import StatsGrid from './StatsGrid';
import ServiceStatus from './ServiceStatus';
import QuickScan from './QuickScan';
import ActivityFeed from './ActivityFeed';
import Spinner from '../common/Spinner';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

export default function Dashboard() {
  const { stats, services, activities, loading, error, refresh } = useDashboard();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Vue d'ensemble des investigations OSINT
          </p>
        </div>
        <button
          onClick={refresh}
          className="p-2 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-all"
          title="Rafraîchir"
        >
          <ArrowPathIcon className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Stats Grid */}
      <section>
        <StatsGrid stats={stats} loading={loading} />
      </section>

      {/* Main Grid: QuickScan + Services */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <QuickScan />
        <ServiceStatus services={services} loading={loading} />
      </div>

      {/* Activity Feed */}
      <section>
        <ActivityFeed activities={activities} loading={loading} />
      </section>
    </div>
  );
}
