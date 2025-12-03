import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Grid,
  Card,
  CardMedia,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  AppBar,
  Toolbar,
  IconButton,
  Button,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import LogoutIcon from '@mui/icons-material/Logout';
import { api, setToken } from '../store/auth.js';

async function fetchAlbumDetail(albumId) {
  const client = api();
  const res = await client.get(`/albums/${albumId}`);
  return res.data;
}

export default function AlbumDetailPage() {
  const { albumId } = useParams();
  const navigate = useNavigate();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['album', albumId],
    queryFn: () => fetchAlbumDetail(albumId),
  });

  const handleLogout = () => {
    setToken(null);
    navigate('/login');
  };

  const album = data || {};
  const images = album.images || [];

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <IconButton color="inherit" onClick={() => navigate('/albums')}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 1, ml: 2 }}>
            {album.name}
          </Typography>
          <IconButton color="inherit" onClick={handleLogout}>
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Box sx={{ p: 3 }}>
        {album.description && (
          <Typography variant="body1" sx={{ mb: 3 }}>
            {album.description}
          </Typography>
        )}

        {isLoading && (
          <Box display="flex" justifyContent="center">
            <CircularProgress />
          </Box>
        )}

        {isError && (
          <Alert severity="error">
            {error?.response?.data?.detail || 'Failed to load album'}
          </Alert>
        )}

        {images.length === 0 && !isLoading && (
          <Alert severity="info">No images in this album yet</Alert>
        )}

        <Grid container spacing={2}>
          {images.map((img) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={img._id}>
              <Card>
                <CardMedia
                  component="img"
                  height="200"
                  image={img.thumbnailUrl || '/placeholder.png'}
                  alt={img.filename}
                  sx={{ objectFit: 'cover' }}
                />
                <CardContent>
                  <Typography variant="body2" noWrap>
                    {img.filename}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </>
  );
}