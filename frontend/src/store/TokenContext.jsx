import React, { createContext, useState, useEffect } from 'react';

export const TokenContext = createContext();

export function TokenProvider({ children }) {
  const [token, setTokenState] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // ✅ Initialize from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('jwt');
    setTokenState(savedToken);
    setIsLoading(false);
  }, []);

  const setToken = (newToken) => {
    if (newToken) {
      localStorage.setItem('jwt', newToken);
      setTokenState(newToken);
    } else {
      localStorage.removeItem('jwt'); 
      setTokenState(null);
    }
  };

  return (
    <TokenContext.Provider value={{ token, setToken, isLoading }}>
      {children}
    </TokenContext.Provider>
  );
}