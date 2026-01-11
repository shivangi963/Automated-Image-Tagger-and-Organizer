import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box, Grid, Card, CardMedia, CardContent, Typography, CircularProgress,
  Alert, Container, IconButton, Chip, Button, Dialog, DialogTitle,
  DialogContent, List, ListItem, ListItemText, Checkbox, DialogActions,
  Breadcrumbs, Link, Tooltip
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddPhotoAlternateIcon from '@mui/icons-material/AddPhotoAlternate';
import DeleteIcon from '@mui/icons-material/Delete';
import api from '../api/axiosClient.js';
import getErrorMessage from '../utils/getErrorMessage.js';
import AppLayout from '../components/AppLayout.jsx';

async function fetchAlbumDetail(albumId) {
  const res = await api.get(`/albums/${albumId}`);
  return res.data;
}

async function fetchAlbumImages(albumId) {
  const res = await api.get(`/albums/${albumId}/images`);
  return res.data;
}

async function fetchAllImages() {
  const res = await api.get('/images/');
  return Array.isArray(res.data) ? res.data : (res.data.images || []);
}

async function addImagesToAlbum(albumId, imageIds) {
  await api.post(`/albums/${albumId}/images`, { image_ids: imageIds });
}

async function removeImageFromAlbum(albumId, imageId) {
  await api.delete(`/albums/${albumId}/images/${imageId}`);
}

export default function AlbumDetail() {
  const { albumId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [selectedImages, setSelectedImages] = useState([]);

  const { data: album, isLoading: albumLoading } = useQuery({
    queryKey: ['album', albumId],
    queryFn: () => fetchAlbumDetail(albumId),
  });

  const { data: images = [], isLoading: imagesLoading, isError, error } = useQuery({
    queryKey: ['albumImages', albumId],
    queryFn: () => fetchAlbumImages(albumId),
  });

  const { data: allImages = [] } = useQuery({
    queryKey: ['allImages'],
    queryFn: fetchAllImages,
    enabled: openAddDialog,
  });

  const addMutation = useMutation({
    mutationFn: () => addImagesToAlbum(albumId, selectedImages),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['albumImages', albumId] });
      queryClient.invalidateQueries({ queryKey: ['album', albumId] });
      setSelectedImages([]);
      setOpenAddDialog(false);
    },
  });

  const removeMutation = useMutation({
    mutationFn: (imageId) => removeImageFromAlbum(albumId, imageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['albumImages', albumId] });
      queryClient.invalidateQueries({ queryKey: ['album', albumId] });
    },
  });

  const handleToggleImage = (imageId) => {
    setSelectedImages(prev =>
      prev.includes(imageId)
        ? prev.filter(id => id !== imageId)
        : [...prev, imageId]
    );
  };

  const isLoading = albumLoading || imagesLoading;

  return (
    <AppLayout title={album?.name || 'Album'}>
      <Container maxWidth="xl" sx={{ py: 3 }}>
        {/* Breadcrumbs */}
        <Breadcrumbs sx={{ mb: 3 }}>
          <Link
            component="button"
            variant="body1"
            onClick={() => navigate('/albums')}
            sx={{ textDecoration: 'none', cursor: 'pointer' }}
          >
            Albums
          </Link>
          <Typography color="text.primary">{album?.name || 'Loading...'}</Typography>
        </Breadcrumbs>

        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              {album?.name}
            </Typography>
            {album?.description && (
              <Typography variant="body1" color="textSecondary">
                {album.description}
              </Typography>
            )}
            <Typography variant="caption" color="textSecondary">
              {images.length} image{images.length !== 1 ? 's' : ''}
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddPhotoAlternateIcon />}
            onClick={() => setOpenAddDialog(true)}
          >
            Add Images
          </Button>
        </Box>

        {isLoading && (
          <Box display="flex" justifyContent="center" my={8}>
            <CircularProgress size={60} />
          </Box>
        )}

        {isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {getErrorMessage(error)}
          </Alert>
        )}

        {/* Empty State */}
        {!isLoading && images.length === 0 && (
          <Box display="flex" flexDirection="column" alignItems="center" py={8}>
            <AddPhotoAlternateIcon sx={{ fontSize: 120, color: 'grey.300', mb: 2 }} />
            <Typography variant="h5" color="textSecondary" gutterBottom>
              No images in this album
            </Typography>
            <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>
              Add images to get started
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddPhotoAlternateIcon />}
              onClick={() => setOpenAddDialog(true)}
              size="large"
            >
              Add Images
            </Button>
          </Box>
        )}

        {/* Images Grid */}
        <Grid container spacing={3}>
          {images.map((img) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={img._id || img.id}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  transition: 'all 0.3s',
                  '&:hover': { transform: 'translateY(-4px)', boxShadow: 4 }
                }}
              >
                <CardMedia
                  component="img"
                  height="200"
                  image={img.thumbnailUrl || img.url || '/placeholder.png'}
                  alt={img.filename || img.name}
                  sx={{ objectFit: 'cover' }}
                />
                <CardContent sx={{ flexGrow: 1 }}>
                  <Tooltip title={img.filename || img.name}>
                    <Typography variant="subtitle2" noWrap>
                      {img.filename || img.name}
                    </Typography>
                  </Tooltip>
                  <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {(img.tags || []).slice(0, 3).map((tag, idx) => (
                      <Chip
                        key={idx}
                        label={typeof tag === 'string' ? tag : (tag.name || tag.label || tag.tag_name)}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                  </Box>
                </CardContent>
                <Box sx={{ px: 2, pb: 2, display: 'flex', justifyContent: 'flex-end' }}>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => {
                      if (window.confirm('Remove from album?')) {
                        removeMutation.mutate(img._id || img.id);
                      }
                    }}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* Add Images Dialog */}
      <Dialog open={openAddDialog} onClose={() => setOpenAddDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add Images to Album</DialogTitle>
        <DialogContent>
          <List>
            {allImages
              .filter(img => !images.find(albumImg => (albumImg._id || albumImg.id) === (img._id || img.id)))
              .map((img) => (
                <ListItem
                  key={img._id || img.id}
                  button
                  onClick={() => handleToggleImage(img._id || img.id)}
                >
                  <Checkbox
                    checked={selectedImages.includes(img._id || img.id)}
                    tabIndex={-1}
                    disableRipple
                  />
                  <CardMedia
                    component="img"
                    sx={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 1, mr: 2 }}
                    image={img.thumbnailUrl || img.url || '/placeholder.png'}
                    alt={img.filename}
                  />
                  <ListItemText
                    primary={img.filename || img.name}
                    secondary={`${(img.tags || []).length} tags`}
                  />
                </ListItem>
              ))}
            {allImages.length === 0 && (
              <Typography variant="body2" color="textSecondary" align="center" sx={{ py: 4 }}>
                No images available to add
              </Typography>
            )}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAddDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => addMutation.mutate()}
            disabled={selectedImages.length === 0 || addMutation.isPending}
          >
            Add {selectedImages.length} Image{selectedImages.length !== 1 ? 's' : ''}
          </Button>
        </DialogActions>
      </Dialog>
    </AppLayout>
  );
}