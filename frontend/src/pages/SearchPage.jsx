import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  TextField,
  Button,
  Grid,
  Card,
  CardMedia,
  CardContent,
  Typography,
  Chip,
  CircularProgress,
  Alert,
  AppBar,
  Toolbar,
  IconButton,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import LogoutIcon from '@mui/icons-material/Logout';
import { api, setToken } from '../store/auth.js';

async function searchImages(query) {
  if (!query.trim()) {
    return { images: [] };
  }
  const client = api();
  const res = await client.get('/search', { params: { query } });
  return res.data;
}

export default function SearchPage() {
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['search', search],
    queryFn: () => searchImages(search),
    enabled: search.length > 0,
  });

  const handleSearch = (e) => {
    e.preventDefault();
    setSearch(searchInput);
  };

  const handleLogout = () => {
    setToken(null);
    navigate('/login');
  };

  const images = data?.images || [];

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Search Images
          </Typography>
          <IconButton color="inherit" onClick={handleLogout}>
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Box sx={{ p: 3 }}>
        <Box component="form" onSubmit={handleSearch} sx={{ mb: 3 }}>
          <TextField
            label="Search by tags, objects, or metadata"
            fullWidth
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="e.g., cat, dog, indoor..."
            sx={{ mb: 2 }}
          />
          <Button
            type="submit"
            variant="contained"
            fullWidth
          >
            Search
          </Button>
        </Box>

        {isLoading && (
          <Box display="flex" justifyContent="center">
            <CircularProgress />
          </Box>
        )}

        {isError && (
          <Alert severity="error">
            {error?.response?.data?.detail || 'Search failed'}
          </Alert>
        )}

        {images.length === 0 && search && !isLoading && (
          <Alert severity="info">No images found for "{search}"</Alert>
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
                  <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {img.tags?.slice(0, 3).map((tag, idx) => (
                      <Chip
                        key={idx}
                        label={typeof tag === 'string' ? tag : tag.name}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                  </Box>
                  <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                    Status: {img.status}
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