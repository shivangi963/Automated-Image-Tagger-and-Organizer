import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box, Button, Grid, Card, CardMedia, CardContent, Typography,
  Chip, CircularProgress, Alert, LinearProgress, Container, Paper, 
  InputBase, IconButton, Dialog, DialogTitle, DialogContent, 
  DialogActions, Tooltip, Zoom, Skeleton
} from '@mui/material';
import UploadIcon from '@mui/icons-material/Upload';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import ImageIcon from '@mui/icons-material/Image';
import DeleteIcon from '@mui/icons-material/Delete';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
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
        {/* Modern Centered Action Bar with Gradient */}
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
          <Paper 
            elevation={0}
            sx={{ 
              p: 3,
              width: '100%',
              maxWidth: 900,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              borderRadius: 3,
              boxShadow: '0 8px 32px rgba(102, 126, 234, 0.25)'
            }}
          >
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap' }}>
              <Paper sx={{ flex: 1, display: 'flex', alignItems: 'center', borderRadius: 2, minWidth: 300, maxWidth: 500 }}>
                <SearchIcon sx={{ ml: 2, color: 'text.secondary' }} />
                <InputBase
                  placeholder="Search by AI tags (car, person, dog...)..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
                  sx={{ flex: 1, px: 2, py: 1.5 }}
                />
                {searchInput && (
                  <IconButton size="small" onClick={handleClearSearch} sx={{ mr: 1 }}>
                    <ClearIcon />
                  </IconButton>
                )}
              </Paper>
              
              <Button
                variant="contained"
                startIcon={<SearchIcon />}
                onClick={handleSearch}
                sx={{ 
                  bgcolor: 'white', 
                  color: 'primary.main',
                  '&:hover': { bgcolor: 'grey.100' },
                  fontWeight: 600,
                  px: 3
                }}
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
                startIcon={<CloudUploadIcon />}
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                sx={{ 
                  bgcolor: 'rgba(255,255,255,0.2)', 
                  backdropFilter: 'blur(10px)',
                  color: 'white',
                  fontWeight: 600,
                  px: 3,
                  border: '1px solid rgba(255,255,255,0.3)',
                  '&:hover': { 
                    bgcolor: 'rgba(255,255,255,0.3)',
                    transform: 'translateY(-2px)',
                    transition: 'all 0.2s'
                  }
                }}
              >
                Upload
              </Button>
            </Box>
          </Paper>
        </Box>

        {/* Upload Progress */}
        {uploading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
            <Paper sx={{ p: 3, borderRadius: 2, width: '100%', maxWidth: 600 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                <AutoAwesomeIcon color="primary" />
                <Typography variant="body1" sx={{ flex: 1 }}>
                  Uploading and AI processing... {uploadProgress}%
                </Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={uploadProgress}
                sx={{ 
                  height: 8, 
                  borderRadius: 4,
                  bgcolor: 'grey.200',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 4,
                    background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)'
                  }
                }}
              />
            </Paper>
          </Box>
        )}

        {/* Search Results Info */}
        {search && !isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
            <Alert 
              severity="info" 
              sx={{ borderRadius: 2, maxWidth: 600, width: '100%' }}
              icon={<SearchIcon />}
            >
              Found <strong>{imagesData.length}</strong> image{imagesData.length !== 1 ? 's' : ''} matching "{search}"
            </Alert>
          </Box>
        )}

        {/* Loading State */}
        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <Box sx={{ maxWidth: 1200, width: '100%' }}>
              <Grid container spacing={3}>
                {[1,2,3,4,5,6].map(n => (
                  <Grid item xs={12} sm={6} md={4} lg={3} key={n}>
                    <Card sx={{ borderRadius: 2 }}>
                      <Skeleton variant="rectangular" height={200} />
                      <CardContent>
                        <Skeleton width="80%" />
                        <Skeleton width="60%" />
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>
          </Box>
        )}

        {isError && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
            <Alert severity="error" sx={{ borderRadius: 2, maxWidth: 600, width: '100%' }}>
              {getErrorMessage(queryError)}
            </Alert>
          </Box>
        )}

        {/* Empty State */}
        {!isLoading && imagesData.length === 0 && (
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <Paper 
              sx={{ 
                py: 12,
                px: 4,
                textAlign: 'center',
                background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
                borderRadius: 3,
                maxWidth: 700,
                width: '100%'
              }}
            >
              <ImageIcon sx={{ fontSize: 120, color: 'primary.main', opacity: 0.5, mb: 3 }} />
              <Typography variant="h4" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
                {search ? 'No images found' : 'Your Gallery Awaits'}
              </Typography>
              <Typography variant="body1" color="textSecondary" sx={{ mb: 4, px: 4 }}>
                {search 
                  ? 'Try different keywords or upload more images to build your collection'
                  : 'Upload your first images and let AI automatically tag and organize them'}
              </Typography>
              {!search && (
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<CloudUploadIcon />}
                  onClick={() => fileRef.current?.click()}
                  sx={{ 
                    px: 4, 
                    py: 1.5,
                    fontSize: '1.1rem',
                    fontWeight: 600,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    boxShadow: '0 4px 20px rgba(102, 126, 234, 0.4)',
                    '&:hover': {
                      boxShadow: '0 6px 30px rgba(102, 126, 234, 0.6)',
                    }
                  }}
                >
                  Upload Images
                </Button>
              )}
            </Paper>
          </Box>
        )}

        {/* Images Grid - CENTERED */}
        {!isLoading && imagesData.length > 0 && (
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <Box sx={{ maxWidth: 1400, width: '100%' }}>
              <Grid container spacing={3} justifyContent="center">
                {imagesData.map((img, index) => {
                  const tags = getTags(img);
                  return (
                    <Grid item xs={12} sm={6} md={4} lg={3} key={img._id || img.id}>
                      <Zoom in timeout={200 + index * 50}>
                        <Card
                          sx={{
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            borderRadius: 2,
                            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                            '&:hover': { 
                              transform: 'translateY(-8px)', 
                              boxShadow: '0 12px 40px rgba(0,0,0,0.15)'
                            }
                          }}
                        >
                          <Box sx={{ position: 'relative', overflow: 'hidden' }}>
                            <CardMedia
                              component="img"
                              height="220"
                              image={img.url || img.thumbnailUrl || 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIyMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImciIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMTAwJSIgeTI9IjEwMCUiPjxzdG9wIG9mZnNldD0iMCUiIHN0b3AtY29sb3I9IiNmNWY3ZmEiLz48c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiNjM2NmZTIiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIyMCIgZmlsbD0idXJsKCNnKSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjE2IiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+TG9hZGluZy4uLjwvdGV4dD48L3N2Zz4='}
                              alt={img.filename || img.original_filename || img.name}
                              sx={{ 
                                objectFit: 'cover', 
                                cursor: 'pointer',
                                transition: 'transform 0.3s',
                                '&:hover': { transform: 'scale(1.05)' }
                              }}
                              onClick={() => setSelectedImage(img)}
                            />
                            
                            {/* Status Badge */}
                            {img.status === 'pending' && (
                              <Chip
                                label="AI Processing..."
                                size="small"
                                color="warning"
                                icon={<AutoAwesomeIcon />}
                                sx={{ 
                                  position: 'absolute', 
                                  top: 12, 
                                  right: 12,
                                  fontWeight: 600,
                                  backdropFilter: 'blur(10px)',
                                  bgcolor: 'rgba(255, 152, 0, 0.9)'
                                }}
                              />
                            )}
                            
                            {img.status === 'completed' && tags.length > 0 && (
                              <Chip
                                label={`${tags.length} AI tags`}
                                size="small"
                                color="success"
                                icon={<AutoAwesomeIcon />}
                                sx={{ 
                                  position: 'absolute', 
                                  top: 12, 
                                  right: 12,
                                  fontWeight: 600,
                                  backdropFilter: 'blur(10px)',
                                  bgcolor: 'rgba(76, 175, 80, 0.9)'
                                }}
                              />
                            )}
                          </Box>

                          <CardContent sx={{ flexGrow: 1, pb: 1 }}>
                            <Tooltip title={img.filename || img.original_filename || img.name}>
                              <Typography 
                                variant="subtitle2" 
                                noWrap 
                                sx={{ mb: 1.5, fontWeight: 600, color: 'text.primary' }}
                              >
                                {img.filename || img.original_filename || img.name}
                              </Typography>
                            </Tooltip>

                            {/* Tags Display */}
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, minHeight: 60 }}>
                              {tags.length > 0 ? (
                                <>
                                  {tags.slice(0, 6).map((tag, idx) => (
                                    <Chip
                                      key={idx}
                                      label={tag}
                                      size="small"
                                      sx={{ 
                                        fontSize: '0.7rem',
                                        height: 24,
                                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                        color: 'white',
                                        fontWeight: 500
                                      }}
                                    />
                                  ))}
                                  {tags.length > 6 && (
                                    <Chip
                                      label={`+${tags.length - 6}`}
                                      size="small"
                                      sx={{ fontSize: '0.7rem', height: 24 }}
                                    />
                                  )}
                                </>
                              ) : (
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  {img.status === 'pending' ? (
                                    <>
                                      <CircularProgress size={16} />
                                      <Typography variant="caption" color="warning.main" sx={{ fontStyle: 'italic' }}>
                                        AI tagging in progress...
                                      </Typography>
                                    </>
                                  ) : (
                                    <Typography variant="caption" color="textSecondary" sx={{ fontStyle: 'italic' }}>
                                      No tags detected
                                    </Typography>
                                  )}
                                </Box>
                              )}
                            </Box>
                          </CardContent>

                          <Box sx={{ px: 2, pb: 2, display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => setSelectedImage(img)}
                              sx={{ flex: 1 }}
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
                          </Box>
                        </Card>
                      </Zoom>
                    </Grid>
                  );
                })}
              </Grid>
            </Box>
          </Box>
        )}
      </Container>

      {/* Image Detail Dialog */}
      <Dialog 
        open={Boolean(selectedImage)} 
        onClose={() => setSelectedImage(null)} 
        maxWidth="md" 
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        {selectedImage && (
          <>
            <DialogTitle sx={{ pb: 1 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {selectedImage.filename || selectedImage.original_filename || selectedImage.name}
              </Typography>
            </DialogTitle>
            <DialogContent>
              <Box sx={{ borderRadius: 2, overflow: 'hidden', mb: 3 }}>
                <img
                  src={selectedImage.url || selectedImage.thumbnailUrl}
                  alt={selectedImage.filename}
                  style={{ width: '100%', display: 'block' }}
                />
              </Box>
              
              <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600, color: 'primary.main' }}>
                AI-Detected Tags ({getTags(selectedImage).length}):
              </Typography>
              
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {getTags(selectedImage).length > 0 ? (
                  getTags(selectedImage).map((tag, idx) => (
                    <Chip
                      key={idx}
                      label={tag}
                      sx={{
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white',
                        fontWeight: 500
                      }}
                    />
                  ))
                ) : (
                  <Typography variant="body2" color="textSecondary" sx={{ fontStyle: 'italic' }}>
                    {selectedImage.status === 'pending' 
                      ? 'AI tagging in progress... Please wait.'
                      : 'No tags detected for this image'}
                  </Typography>
                )}
              </Box>
              
              <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
                <Typography variant="caption" color="textSecondary" display="block">
                  <strong>Status:</strong> {selectedImage.status || 'unknown'}
                </Typography>
                {selectedImage.metadata && (
                  <>
                    <Typography variant="caption" color="textSecondary" display="block">
                      <strong>Size:</strong> {selectedImage.metadata.width} × {selectedImage.metadata.height}
                    </Typography>
                    <Typography variant="caption" color="textSecondary" display="block">
                      <strong>Format:</strong> {selectedImage.metadata.format}
                    </Typography>
                  </>
                )}
              </Box>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 3 }}>
              <Button onClick={() => setSelectedImage(null)} variant="outlined">
                Close
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </AppLayout>
  );
}