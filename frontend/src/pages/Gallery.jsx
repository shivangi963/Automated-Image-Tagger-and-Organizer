import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box, Button, Grid, Card, CardMedia, CardContent, Typography,
  Chip, CircularProgress, Alert, LinearProgress, Container, Paper, 
  InputBase, Stack, Fade, CardActions, Dialog, DialogTitle, 
  DialogContent, DialogActions, Tooltip, IconButton
} from '@mui/material';
import UploadIcon from '@mui/icons-material/Upload';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import ImageIcon from '@mui/icons-material/Image';
import DeleteIcon from '@mui/icons-material/Delete';
import api from '../api/axiosClient.js';
import getErrorMessage from '../utils/getErrorMessage.js';
import AppLayout from '../components/AppLayout.jsx';

export default function Gallery() {
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedImage, setSelectedImage] = useState(null);
  const fileRef = useRef(null);

  // Fetch images with proper URL generation
  const fetchImages = async (search) => {
    try {
      if (search && search.trim()) {
        const res = await api.get('/search', { params: { query: search } });
        const images = res.data.images || [];
        return await Promise.all(images.map(img => enrichImageWithUrl(img)));
      }
      const res = await api.get('/images/');
      const images = Array.isArray(res.data) ? res.data : (res.data.images || []);
      return await Promise.all(images.map(img => enrichImageWithUrl(img)));
    } catch (error) {
      console.error('Error fetching images:', error);
      return [];
    }
  };

  // Enrich image with proper URL
  const enrichImageWithUrl = async (img) => {
    try {
      // Get presigned URL for the image
      const urlRes = await api.get(`/images/${img._id || img.id}/url`);
      return {
        ...img,
        url: urlRes.data.url,
        thumbnailUrl: urlRes.data.url
      };
    } catch (error) {
      console.error('Error getting image URL:', error);
      return img;
    }
  };

  const { data: imagesData = [], isLoading, isError, error: queryError } = useQuery({
    queryKey: ['images', search],
    queryFn: () => fetchImages(search),
    refetchInterval: 5000,
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
          if (!uploadRes.ok) throw new Error(`Upload failed: ${uploadRes.statusText}`);

          setUploadProgress(Math.round(((i + 1) / files.length) * 60));

          await ingestImage({
            filename: file.name,
            mime_type: file.type,
            storage_key: presign.storageKey || presign.key,
          });
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
  });

  const deleteMutation = useMutation({
    mutationFn: async (imageId) => {
      await api.delete(`/images/${imageId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['images'] });
      setSelectedImage(null);
    },
  });

  const onFilesSelected = (ev) => {
    const files = Array.from(ev.target.files || []);
    if (files.length) uploadMutation.mutate(files);
    if (fileRef.current) fileRef.current.value = '';
  };

  const handleSearch = () => {
    setSearch(searchInput);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setSearch('');
  };

  const getTags = (img) => {
    if (!img.tags) return [];
    return img.tags.map(tag => {
      if (typeof tag === 'string') return tag;
      return tag.tag_name || tag.name || tag.label || '';
    }).filter(Boolean);
  };

  return (
    <AppLayout title="Gallery">
      <Container maxWidth="xl" sx={{ py: 3 }}>
        {/* Action Bar */}
        <Paper sx={{ p: 2, mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
          <InputBase
            placeholder="Search by tags or content..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
            sx={{ flex: 1, px: 2 }}
          />
          {searchInput && (
            <IconButton size="small" onClick={handleClearSearch}>
              <ClearIcon />
            </IconButton>
          )}
          <Button
            variant="contained"
            startIcon={<SearchIcon />}
            onClick={handleSearch}
          >
            Search
          </Button>
          <input
            ref={fileRef}
            type="file"
            multiple
            accept="image/*"
            style={{ display: 'none' }}
            onChange={onFilesSelected}
          />
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            color="secondary"
          >
            Upload
          </Button>
        </Paper>

        {uploading && (
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="body2" gutterBottom>
              Uploading... {uploadProgress}%
            </Typography>
            <LinearProgress variant="determinate" value={uploadProgress} />
          </Paper>
        )}

        {search && !isLoading && (
          <Alert severity="info" sx={{ mb: 3 }}>
            Found <strong>{imagesData.length}</strong> result{imagesData.length !== 1 ? 's' : ''} for "{search}"
          </Alert>
        )}

        {isLoading && (
          <Box display="flex" justifyContent="center" my={8}>
            <CircularProgress size={60} />
          </Box>
        )}

        {isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {getErrorMessage(queryError)}
          </Alert>
        )}

        {!isLoading && imagesData.length === 0 && (
          <Box display="flex" flexDirection="column" alignItems="center" py={8}>
            <ImageIcon sx={{ fontSize: 120, color: 'grey.300', mb: 2 }} />
            <Typography variant="h5" color="textSecondary" gutterBottom>
              {search ? 'No images found' : 'No images yet'}
            </Typography>
            <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>
              {search ? 'Try a different search' : 'Upload your first image'}
            </Typography>
            {!search && (
              <Button
                variant="contained"
                startIcon={<UploadIcon />}
                onClick={() => fileRef.current?.click()}
                size="large"
              >
                Upload Images
              </Button>
            )}
          </Box>
        )}

        {/* Image Grid */}
        <Grid container spacing={3}>
          {imagesData.map((img) => {
            const tags = getTags(img);
            return (
              <Grid item xs={12} sm={6} md={4} lg={3} key={img._id || img.id}>
                <Fade in timeout={300}>
                  <Card
                    sx={{
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      transition: 'all 0.3s',
                      '&:hover': { transform: 'translateY(-4px)', boxShadow: 4 }
                    }}
                  >
                    <Box sx={{ position: 'relative' }}>
                      <CardMedia
                        component="img"
                        height="200"
                        image={img.url || img.thumbnailUrl || 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjE4IiBmaWxsPSIjYWFhIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+TG9hZGluZy4uLjwvdGV4dD48L3N2Zz4='}
                        alt={img.filename || img.original_filename || img.name}
                        sx={{ objectFit: 'cover', cursor: 'pointer', bgcolor: 'grey.200' }}
                        onClick={() => setSelectedImage(img)}
                        onError={(e) => {
                          e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjE4IiBmaWxsPSIjYWFhIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+SW1hZ2U8L3RleHQ+PC9zdmc+';
                        }}
                      />
                      {img.status === 'pending' && (
                        <Chip
                          label="Processing..."
                          size="small"
                          color="warning"
                          sx={{ position: 'absolute', top: 8, right: 8 }}
                        />
                      )}
                      {img.status === 'completed' && tags.length > 0 && (
                        <Chip
                          label={`${tags.length} tags`}
                          size="small"
                          color="success"
                          sx={{ position: 'absolute', top: 8, right: 8 }}
                        />
                      )}
                    </Box>

                    <CardContent sx={{ flexGrow: 1, pb: 1 }}>
                      <Tooltip title={img.filename || img.original_filename || img.name}>
                        <Typography variant="subtitle2" noWrap sx={{ mb: 1, fontWeight: 500 }}>
                          {img.filename || img.original_filename || img.name}
                        </Typography>
                      </Tooltip>

                      {/* ALL TAGS DISPLAYED */}
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {tags.map((tag, idx) => (
                          <Chip
                            key={idx}
                            label={tag}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.7rem' }}
                          />
                        ))}
                        {tags.length === 0 && img.status === 'completed' && (
                          <Typography variant="caption" color="textSecondary">
                            No tags detected
                          </Typography>
                        )}
                      </Box>
                    </CardContent>

                    <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
                      <Button
                        size="small"
                        onClick={() => setSelectedImage(img)}
                      >
                        View
                      </Button>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => {
                          if (window.confirm('Delete this image?')) {
                            deleteMutation.mutate(img._id || img.id);
                          }
                        }}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </CardActions>
                  </Card>
                </Fade>
              </Grid>
            );
          })}
        </Grid>
      </Container>

      {/* Image Detail Dialog */}
      <Dialog open={Boolean(selectedImage)} onClose={() => setSelectedImage(null)} maxWidth="md" fullWidth>
        {selectedImage && (
          <>
            <DialogTitle>{selectedImage.filename || selectedImage.original_filename || selectedImage.name}</DialogTitle>
            <DialogContent>
              <img
                src={selectedImage.url || selectedImage.thumbnailUrl}
                alt={selectedImage.filename}
                style={{ width: '100%', borderRadius: 8 }}
                onError={(e) => {
                  e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNjAwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjI0IiBmaWxsPSIjYWFhIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+SW1hZ2UgVW5hdmFpbGFibGU8L3RleHQ+PC9zdmc+';
                }}
              />
              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                All Tags ({getTags(selectedImage).length}):
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {getTags(selectedImage).map((tag, idx) => (
                  <Chip
                    key={idx}
                    label={tag}
                    color="primary"
                    variant="outlined"
                  />
                ))}
              </Stack>
              <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
                Status: {selectedImage.status || 'unknown'}
              </Typography>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedImage(null)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </AppLayout>
  );
}