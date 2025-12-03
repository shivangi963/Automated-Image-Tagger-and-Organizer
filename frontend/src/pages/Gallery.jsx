import React from 'react';
import { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardActionArea,
  CardMedia,
  CardContent,
  Chip,
  CircularProgress,
  TextField,
  IconButton,
  Toolbar,
  AppBar,
  Button,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import LogoutIcon from '@mui/icons-material/Logout';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api, setToken } from '../store/auth.js';

async function fetchImages(search) {
  const client = api();
  if (search) {
    const res = await client.get('/search', { params: { query: search } });
    return res.data.images;
  }
  const res = await client.get('/images');
  return res.data.images;
}

async function presignUpload(file) {
  const client = api();
  const res = await client.post('/uploads/presign', {
    filename: file.name,
    mime: file.type,
  });
  return res.data; // adjust fields to backend
}

async function ingestImage(payload) {
  const client = api();
  const res = await client.post('/images/ingest', payload);
  return res.data;
}

export default function Gallery() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['images', search],
    queryFn: () => fetchImages(search),
  });

  const uploadMutation = useMutation({
    mutationFn: async files => {
      for (const file of files) {
        const presign = await presignUpload(file);

        await fetch(presign.url, {
          method: 'PUT',
          headers: { 'Content-Type': file.type },
          body: file,
        });

        await ingestImage({
          filename: file.name,
          mime: file.type,
          storage_key: presign.storageKey, // adjust to backend
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['images'] });
    },
  });

  const handleLogout = () => {
    setToken(null);
    navigate('/login');
  };

  const handleSearch = () => setSearch(searchInput);

  const handleFileChange = e => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    uploadMutation.mutate(files);
  };

  return (
    <Box>
      <AppBar position="static" color="transparent" elevation={0} sx={{ mb: 2 }}>
        <Toolbar disableGutters sx={{ gap: 2 }}>
          <Typography variant="h5" sx={{ flexGrow: 1 }}>
            Image Tagger
          </Typography>
          <TextField
            size="small"
            placeholder="Search tags or text..."
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            InputProps={{
              endAdornment: (
                <IconButton onClick={handleSearch}>
                  <SearchIcon />
                </IconButton>
              ),
            }}
          />
          <Button startIcon={<LogoutIcon />} onClick={handleLogout} color="inherit">
            Logout
          </Button>
        </Toolbar>
      </AppBar>

      <Button variant="contained" component="label">
        Upload Images
        <input
          hidden
          multiple
          type="file"
          accept="image/*"
          onChange={handleFileChange}
        />
      </Button>

      <Box mt={3}>
        {isLoading && (
          <Box display="flex" justifyContent="center" mt={4}>
            <CircularProgress />
          </Box>
        )}
        {isError && (
          <Typography color="error" mt={2}>
            Failed to load images.
          </Typography>
        )}
        <Grid container spacing={2}>
          {data?.map(img => (
            <Grid item xs={12} sm={6} md={3} key={img.id}>
              <Card>
                <CardActionArea>
                  <CardMedia
                    component="img"
                    height="160"
                    image={img.thumbnailUrl}
                    alt="thumbnail"
                    loading="lazy"
                  />
                  <CardContent>
                    <Box display="flex" flexWrap="wrap" gap={0.5}>
                      {img.tags?.slice(0, 3).map(tag => (
                        <Chip key={tag} label={tag} size="small" />
                      ))}
                    </Box>
                    {img.status && (
                      <Typography variant="caption" color="text.secondary">
                        {img.status}
                      </Typography>
                    )}
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
}
