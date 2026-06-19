import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur requête : ajoute le token si présent
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('thoth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercepteur réponse : gestion centralisée des erreurs
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response) {
      const { status, data } = error.response;

      if (status === 401) {
        localStorage.removeItem('thoth_token');
        localStorage.removeItem('thoth_user');
        // Uniquement rediriger si on n'est pas déjà sur login/register
        if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
          window.location.href = '/login';
        }
      }

      const message = data?.message || data?.error || 'Erreur serveur inconnue';
      return Promise.reject(new Error(message));
    }

    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('La requête a expiré'));
    }

    if (!error.response) {
      return Promise.reject(new Error('Impossible de contacter le serveur'));
    }

    return Promise.reject(error);
  }
);

export default api;
