import api from './api';

export async function getStats() {
  return api.get('/dashboard/stats');
}

export async function getServices() {
  return api.get('/dashboard/services');
}

export async function getActivityFeed() {
  return api.get('/dashboard/activity');
}

export async function getRecentScans() {
  return api.get('/dashboard/recent-scans');
}
