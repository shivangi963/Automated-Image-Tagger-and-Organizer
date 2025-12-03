import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Container, CircularProgress, Box } from '@mui/material';
import { useToken } from './hooks/useToken.js';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import Gallery from './pages/Gallery.jsx';
import SearchPage from './pages/SearchPage.jsx';
import DuplicatesPage from './pages/DuplicatesPage.jsx';
import AlbumsPage from './pages/AlbumsPage.jsx';
import AlbumDetailPage from './pages/AlbumDetailPage.jsx';

function ProtectedRoute({ children }) {
  const { token, isLoading } = useToken();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default function App() {
  const { isLoading } = useToken();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Gallery />
            </ProtectedRoute>
          }
        />
        <Route
          path="/search"
          element={
            <ProtectedRoute>
              <SearchPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/duplicates"
          element={
            <ProtectedRoute>
              <DuplicatesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/albums"
          element={
            <ProtectedRoute>
              <AlbumsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/albums/:albumId"
          element={
            <ProtectedRoute>
              <AlbumDetailPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Container>
  );
}
