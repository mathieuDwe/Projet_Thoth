import api from './api';

export async function investigateGlobal(params) {
  return api.post('/investigate/global', params);
}
