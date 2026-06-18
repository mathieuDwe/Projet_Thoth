import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

const TOKEN_KEY = 'thoth_token';
const USER_KEY = 'thoth_user';
// Rafraîchir le token 5 minutes avant expiration (24h = 1440 min)
const REFRESH_BEFORE_MS = 5 * 60 * 1000;

function decodeToken(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const refreshTimer = useRef(null);

  // Nettoyer le timer
  const clearRefreshTimer = () => {
    if (refreshTimer.current) {
      clearTimeout(refreshTimer.current);
      refreshTimer.current = null;
    }
  };

  // Vérifier le token au démarrage
  const verifySession = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }

    // Vérifier via /auth/me
    try {
      const userData = await api.get('/auth/me');
      setUser(userData);
      localStorage.setItem(USER_KEY, JSON.stringify(userData));
    } catch {
      // Token invalide → nettoyer
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    verifySession();
    return () => clearRefreshTimer();
  }, [verifySession]);

  // Planifier le refresh automatique du token
  const scheduleTokenRefresh = useCallback((token) => {
    clearRefreshTimer();
    const payload = decodeToken(token);
    if (!payload || !payload.exp) return;

    const expiresIn = payload.exp * 1000 - Date.now();
    if (expiresIn <= 0) {
      logout();
      return;
    }

    const delay = Math.max(expiresIn - REFRESH_BEFORE_MS, 5000);
    refreshTimer.current = setTimeout(async () => {
      try {
        const res = await api.post('/auth/refresh');
        const newToken = res.access_token;
        localStorage.setItem(TOKEN_KEY, newToken);
        localStorage.setItem(USER_KEY, JSON.stringify(res.user));
        setUser(res.user);
        scheduleTokenRefresh(newToken);
      } catch {
        logout();
      }
    }, delay);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await api.post('/auth/login', { email, password });
    const { access_token, user: userData } = data;
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(userData));
    setUser(userData);
    scheduleTokenRefresh(access_token);
    return userData;
  }, [scheduleTokenRefresh]);

  const register = useCallback(async (email, username, password) => {
    const data = await api.post('/auth/register', { email, username, password });
    const { access_token, user: userData } = data;
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(userData));
    setUser(userData);
    scheduleTokenRefresh(access_token);
    return userData;
  }, [scheduleTokenRefresh]);

  const logout = useCallback(() => {
    clearRefreshTimer();
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth doit être utilisé dans un AuthProvider');
  }
  return context;
}

export default AuthContext;
