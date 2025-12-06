import React from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000'; // change if backend URL is different

export const getToken = () => localStorage.getItem('jwt');

export const setToken = (newToken) => {
  if (newToken) localStorage.setItem('jwt', newToken);
  else localStorage.removeItem('jwt');
};

export const api = (token) => {
  const t = token || getToken();
  const instance = axios.create({ baseURL: API_BASE });

  if (t) {
    instance.defaults.headers.common.Authorization = `Bearer ${t}`;
  }

  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        setToken(null);
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  );

  return instance;
};
