import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { UserProfile } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authError: string | null;
  isLoginModalOpen: boolean;
  openLoginModal: () => void;
  closeLoginModal: () => void;
  login: (usernameOrEmail: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(() => {
    return typeof window !== 'undefined' ? localStorage.getItem('trading_ai_token') : null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState<boolean>(false);

  const refreshUser = useCallback(async () => {
    const storedToken = localStorage.getItem('trading_ai_token');
    if (!storedToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const profile = await api.getMe();
      setUser(profile);
      setAuthError(null);
    } catch (e: any) {
      console.warn('Session verification failed:', e.message);
      localStorage.removeItem('trading_ai_token');
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (usernameOrEmail: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const res = await api.login(usernameOrEmail, password);
      localStorage.setItem('trading_ai_token', res.access_token);
      setToken(res.access_token);
      setUser(res.user);
      setIsLoginModalOpen(false);
      return true;
    } catch (e: any) {
      setAuthError(e.message || 'Login failed. Please check your credentials.');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (e) {
      // ignore logout network errors
    } finally {
      localStorage.removeItem('trading_ai_token');
      setToken(null);
      setUser(null);
      setAuthError(null);
    }
  };

  const openLoginModal = () => {
    setAuthError(null);
    setIsLoginModalOpen(true);
  };

  const closeLoginModal = () => {
    setIsLoginModalOpen(false);
    setAuthError(null);
  };

  const clearError = () => setAuthError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        authError,
        isLoginModalOpen,
        openLoginModal,
        closeLoginModal,
        login,
        logout,
        refreshUser,
        clearError
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
