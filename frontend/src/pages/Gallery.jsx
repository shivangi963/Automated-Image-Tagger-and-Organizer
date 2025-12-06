import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box, Button, Grid, Card, CardMedia, CardContent, Typography,
  Chip, CircularProgress, Alert, Input, AppBar, Toolbar, IconButton, LinearProgress
} from '@mui/material';
import UploadIcon from '@mui/icons-material/Upload';
import LogoutIcon from '@mui/icons-material/Logout';
import api from '../api/axiosClient.js';
import { useToken } from '../hooks/useToken.js';
import getErrorMessage from '../utils/getErrorMessage.js';

export default function Gallery() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { token, setToken } = useToken();
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileRef = useRef(null);

  // fetch images
  const fetchImages = async (search) => {
    if (search && search.trim()) {
      const res = await api.get('/search', { params: { query: search } });
      return res.data.images || [];
    }
    const res = await api.get('/images/');
    return Array.isArray(res.data) ? res.data : (res.data.images || []);
  };

  const { data: imagesData = [], isLoading, isError, error: queryError } = useQuery({
    queryKey: ['images', search],
    queryFn: () => fetchImages(search),
  });

  const presignUpload = async (file) => {
    const res = await api.post('/images/presign', {
      filename: file.name,
      mime: file.type,
    });
    return res.data;
  };

  const ingestImage = async (payload) => {
    const res = await api.post('/images/ingest', payload);
    return res.data;
  };

  const uploadMutation = useMutation({
    mutationFn: async (files) => {
      setUploading(true);
      setUploadProgress(0);
      try {
        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          
          const presign = await presignUpload(file);
          if (!presign?.url) throw new Error('No presign url returned');

          const uploadRes = await fetch(presign.url, {
            method: 'PUT',
            headers: { 'Content-Type': file.type },
            body: file,
          });
          if (!uploadRes.ok) {
            throw new Error(`Upload failed: ${uploadRes.statusText}`);
          }

          setUploadProgress(Math.round(((i + 1) / files.length) * 60));

          const ingestPayload = {
            filename: file.name,
            mime_type: file.type,
            storage_key: presign.storageKey || presign.key,
          };
          
          await ingestImage(ingestPayload);
          setUploadProgress(Math.round(((i + 1) / files.length) * 100));
        }
      } finally {
        setUploading(false);
        setUploadProgress(0);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['images'] });
    },
    onError: (err) => {
      console.error('Upload failed:', err);
    },
  });

  const onFilesSelected = (ev) => {
    const files = Array.from(ev.target.files || []);
    if (files.length) uploadMutation.mutate(files);
    if (fileRef.current) fileRef.current.value = '';
  };

  const handleLogout = () => {
    setToken(null);
    navigate('/login');
  };

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Gallery
          </Typography>
          <input
            ref={fileRef}
            id="file-upload"
            type="file"
            multiple
            accept="image/*"
            style={{ display: 'none' }}
            onChange={onFilesSelected}
          />
          <label htmlFor="file-upload">
            <Button
              color="inherit"
              component="span"
              startIcon={<UploadIcon />}
              disabled={uploading}
            >
              Upload
            </Button>
          </label>
          <IconButton color="inherit" onClick={handleLogout}>
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Box sx={{ p: 3 }}>
        <Box display="flex" gap={1} mb={2}>
          <Input
            placeholder="Search tags or metadata"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') setSearch(searchInput); }}
            sx={{ flex: 1 }}
          />
          <Button variant="contained" onClick={() => setSearch(searchInput)}>Search</Button>
        </Box>

        {uploading && (
          <Box mb={2}>
            <Typography variant="body2">Uploading & processing... {uploadProgress}%</Typography>
            <LinearProgress variant="determinate" value={uploadProgress} />
          </Box>
        )}

        {isLoading && <Box display="flex" justifyContent="center"><CircularProgress /></Box>}
        {isError && <Alert severity="error">{getErrorMessage(queryError)}</Alert>}

        {/* ✅ Use Grid v1 - remove item prop, use spacing */}
        <Grid container spacing={2}>
          {imagesData && imagesData.length > 0 ? (
            imagesData.map((img) => (
              <Grid key={img._id || img.id} xs={12} sm={6} md={4} lg={3}>
                <Card>
                  <CardMedia
                    component="img"
                    height="200"
                    image={img.thumbnailUrl || img.url || img.original_url || '/placeholder.png'}
                    alt={img.filename || img.name}
                    sx={{ objectFit: 'cover' }}
                  />
                  <CardContent>
                    <Typography variant="body2" noWrap>{img.filename || img.name}</Typography>
                    <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {(img.tags || []).slice(0, 5).map((tag, idx) => (
                        <Chip
                          key={idx}
                          label={typeof tag === 'string' ? tag : (tag.name || tag.label || JSON.stringify(tag))}
                          size="small"
                          variant="outlined"
                        />
                      ))}
                    </Box>
                    <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                      Status: {img.status || 'unknown'}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))
          ) : (
            <Grid xs={12}>
              <Typography align="center" color="textSecondary">
                No images yet. Upload one to get started!
              </Typography>
            </Grid>
          )}
        </Grid>
      </Box>
    </>
  );
}
