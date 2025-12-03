import { useContext } from 'react';
import { TokenContext } from '../store/TokenContext';

export function useToken() {
  const context = useContext(TokenContext);
  if (!context) {
    throw new Error('useToken must be used within TokenProvider');
  }
  return context;
}