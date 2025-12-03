import React, { createContext, useState, useEffect, useCallback } from 'react';

export const TokenContext = createContext();

export function TokenProvider({ children }) {
  const [token, setTokenState] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('jwt');
    if (storedToken) {
      setTokenState(storedToken);
    }
    setIsLoading(false);
  }, []);

  // Set token - both in memory and localStorage
  const setToken = useCallback((newToken) => {
    if (newToken) {
      localStorage.setItem('jwt', newToken);
      setTokenState(newToken);
    } else {
      localStorage.removeItem('jwt');
      setTokenState(null);
    }
  }, []);

  // Get token - always from state (which syncs with localStorage)
  const getToken = useCallback(() => token, [token]);

  // Clear token (for logout)
  const clearToken = useCallback(() => {
    setToken(null);
  }, [setToken]);

  const value = {
    token,
    setToken,
    getToken,
    clearToken,
    isLoading,
  };

  return (
    <TokenContext.Provider value={value}>
      {children}
    </TokenContext.Provider>
  );
}