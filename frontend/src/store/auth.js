import React from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000'; // change if backend URL is different

let token = localStorage.getItem('jwt') || null;

export const getToken = () => token;

export const setToken = newToken => {
  token = newToken;
  if (newToken) localStorage.setItem('jwt', newToken);
  else localStorage.removeItem('jwt');
};

export const api = (token) => {
  const instance = axios.create({ baseURL: API_BASE });
  
  if (token) {
    instance.defaults.headers.common.Authorization = `Bearer ${token}`;
  }

  // Add response interceptor to handle 401 errors
  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        // Token expired - clear it and redirect to login
        localStorage.removeItem('jwt');
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  );

  return instance;
};
