import api from './api';

export async function getReports(params = {}) {
  return api.get('/reports', { params });
}

export async function getReport(id) {
  return api.get(`/reports/${id}`);
}

export async function deleteReport(id) {
  return api.delete(`/reports/${id}`);
}

export async function exportReport(id, format = 'json') {
  return api.get(`/reports/${id}/export`, {
    params: { format },
    responseType: format === 'pdf' ? 'blob' : 'json',
  });
}
