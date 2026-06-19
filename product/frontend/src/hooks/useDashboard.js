import { useState, useEffect, useCallback, useRef } from 'react';
import { getStats, getServices, getActivityFeed } from '../services/dashboard';

const POLL_INTERVAL = 10000; // 10 secondes

const defaultStats = {
  totalRequests: 0,
  successRate: 0,
  activeServices: 0,
  alerts: 0,
};

const defaultServices = [];
const defaultActivities = [];

export default function useDashboard() {
  const [stats, setStats] = useState(defaultStats);
  const [services, setServices] = useState(defaultServices);
  const [activities, setActivities] = useState(defaultActivities);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const fetchAll = useCallback(async () => {
    try {
      const [statsData, servicesData, activityData] = await Promise.allSettled([
        getStats(),
        getServices(),
        getActivityFeed(),
      ]);

      if (statsData.status === 'fulfilled') setStats(statsData.value || defaultStats);
      if (servicesData.status === 'fulfilled') setServices(servicesData.value || defaultServices);
      if (activityData.status === 'fulfilled') setActivities(activityData.value || defaultActivities);

      setError(null);
    } catch (err) {
      setError('Impossible de récupérer les données du dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  // Polling setup
  useEffect(() => {
    fetchAll();

    intervalRef.current = setInterval(fetchAll, POLL_INTERVAL);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchAll]);

  return {
    stats,
    services,
    activities,
    loading,
    error,
    refresh: fetchAll,
  };
}
