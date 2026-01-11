import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Box, Card, CardContent, Typography, Button, Dialog, TextField,
  CircularProgress, Alert, Grid, Container, CardActions, IconButton,
  DialogTitle, DialogContent, DialogActions, CardMedia, Fab
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import FolderIcon from '@mui/icons-material/Folder';
import api from '../api/axiosClient.js';
import getErrorMessage from '../utils/getErrorMessage.js';
import AppLayout from '../components/AppLayout.jsx';

async function fetchAlbums() {
  const res = await api.get('/albums');
  return res.data;
}

async function createAlbum(data) {
  const res = await api.post('/albums', data);
  return res.data;
}

async function deleteAlbum(albumId) {
  await api.delete(`/albums/${albumId}`);
}

export default function Albums() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [openDialog, setOpenDialog] = useState(false);
  const [albumName, setAlbumName] = useState('');
  const [albumDescription, setAlbumDescription] = useState('');

  const { data = [], isLoading, isError, error } = useQuery({
    queryKey: ['albums'],
    queryFn: fetchAlbums,
  });

  const createMutation = useMutation({
    mutationFn: () => createAlbum({ name: albumName, description: albumDescription }),
    onSuccess: () => {
      // Reset form
      setAlbumName('');
      setAlbumDescription('');
      
      // Close dialog FIRST
      setOpenDialog(false);
      
      // Then invalidate queries to refresh the list
      queryClient.invalidateQueries({ queryKey: ['albums'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAlbum,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['albums'] });
    },
  });

  const handleCreateAlbum = async (e) => {
    e.preventDefault();
    if (albumName.trim()) {
      await createMutation.mutateAsync();
    }
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setAlbumName('');
    setAlbumDescription('');
  };

  return (
    <AppLayout title="Albums">
      <Container maxWidth="xl" sx={{ py: 3 }}>
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
        {!isLoading && data.length === 0 && (
          <Box display="flex" flexDirection="column" alignItems="center" py={8}>
            <FolderIcon sx={{ fontSize: 120, color: 'grey.300', mb: 2 }} />
            <Typography variant="h5" color="textSecondary" gutterBottom>
              No albums yet
            </Typography>
            <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>
              Create your first album to organize your images
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setOpenDialog(true)}
              size="large"
            >
              Create Album
            </Button>
          </Box>
        )}

        <Grid container spacing={3}>
          {data.map((album) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={album._id || album.id}>
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
                  sx={{
                    height: 160,
                    bgcolor: 'primary.light',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer'
                  }}
                  onClick={() => navigate(`/albums/${album._id || album.id}`)}
                >
                  <FolderIcon sx={{ fontSize: 80, color: 'white', opacity: 0.8 }} />
                </CardMedia>

                <CardContent sx={{ flexGrow: 1 }}>
                  <Typography variant="h6" gutterBottom>
                    {album.name}
                  </Typography>
                  {album.description && (
                    <Typography variant="body2" color="textSecondary" sx={{ mb: 1 }}>
                      {album.description}
                    </Typography>
                  )}
                  <Typography variant="caption" color="textSecondary">
                    {album.image_count || 0} image{album.image_count !== 1 ? 's' : ''}
                  </Typography>
                </CardContent>

                <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
                  <Button
                    size="small"
                    startIcon={<EditIcon />}
                    onClick={() => navigate(`/albums/${album._id || album.id}`)}
                  >
                    Open
                  </Button>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => {
                      if (window.confirm(`Delete album "${album.name}"?`)) {
                        deleteMutation.mutate(album._id || album.id);
                      }
                    }}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Floating Action Button */}
        {data.length > 0 && (
          <Fab
            color="primary"
            sx={{ position: 'fixed', bottom: 24, right: 24 }}
            onClick={() => setOpenDialog(true)}
          >
            <AddIcon />
          </Fab>
        )}
      </Container>

      {/* Create Album Dialog */}
      <Dialog 
        open={openDialog} 
        onClose={handleCloseDialog}
        maxWidth="sm" 
        fullWidth
      >
        <DialogTitle>Create New Album</DialogTitle>
        <DialogContent>
          <Box component="form" onSubmit={handleCreateAlbum}>
            <TextField
              autoFocus
              label="Album Name"
              fullWidth
              value={albumName}
              onChange={(e) => setAlbumName(e.target.value)}
              margin="normal"
              required
            />
            <TextField
              label="Description (optional)"
              fullWidth
              multiline
              rows={3}
              value={albumDescription}
              onChange={(e) => setAlbumDescription(e.target.value)}
              margin="normal"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreateAlbum}
            disabled={!albumName.trim() || createMutation.isPending}
          >
            {createMutation.isPending ? <CircularProgress size={20} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </AppLayout>
  );
}