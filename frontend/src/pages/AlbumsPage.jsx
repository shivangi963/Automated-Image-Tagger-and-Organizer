import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Dialog,
  TextField,
  CircularProgress,
  Alert,
  Grid,
  AppBar,
  Toolbar,
  IconButton,
  CardActions,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import LogoutIcon from '@mui/icons-material/Logout';
import { useNavigate } from 'react-router-dom';
import { api, setToken } from '../store/auth.js';
import getErrorMessage from '../utils/getErrorMessage.js';

async function fetchAlbums() {
  const client = api();
  const res = await client.get('/albums');
  return res.data;
}

async function createAlbum(name, description) {
  const client = api();
  const res = await client.post('/albums', { name, description });
  return res.data;
}

async function deleteAlbum(albumId) {
  const client = api();
  await client.delete(`/albums/${albumId}`);
}

export default function AlbumsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [openDialog, setOpenDialog] = useState(false);
  const [albumName, setAlbumName] = useState('');
  const [albumDescription, setAlbumDescription] = useState('');

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['albums'],
    queryFn: fetchAlbums,
  });

  const createMutation = useMutation({
    mutationFn: () => createAlbum(albumName, albumDescription),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['albums'] });
      setAlbumName('');
      setAlbumDescription('');
      setOpenDialog(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAlbum,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['albums'] });
    },
  });

  const handleLogout = () => {
    setToken(null);
    navigate('/login');
  };

  const handleCreateAlbum = () => {
    if (albumName.trim()) {
      createMutation.mutate();
    }
  };

  const albums = data || [];

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Albums
          </Typography>
          <Button
            color="inherit"
            startIcon={<AddIcon />}
            onClick={() => setOpenDialog(true)}
          >
            New Album
          </Button>
          <IconButton color="inherit" onClick={handleLogout}>
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Box sx={{ p: 3 }}>
        {isLoading && (
          <Box display="flex" justifyContent="center">
            <CircularProgress />
          </Box>
        )}

        {isError && (
          <Alert severity="error">
            {getErrorMessage(error)}
          </Alert>
        )}

        <Grid container spacing={2}>
          {albums.map((album) => (
            <Grid item xs={12} sm={6} md={4} key={album._id}>
              <Card>
                <CardContent>
                  <Typography variant="h6">{album.name}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    {album.description}
                  </Typography>
                  <Typography variant="caption">
                    {album.image_count || 0} images
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button
                    size="small"
                    startIcon={<EditIcon />}
                    onClick={() => navigate(`/albums/${album._id}`)}
                  >
                    View
                  </Button>
                  <Button
                    size="small"
                    color="error"
                    startIcon={<DeleteIcon />}
                    onClick={() => deleteMutation.mutate(album._id)}
                  >
                    Delete
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <Box sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Create New Album
          </Typography>
          <TextField
            label="Album Name"
            fullWidth
            value={albumName}
            onChange={(e) => setAlbumName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            label="Description"
            fullWidth
            multiline
            rows={3}
            value={albumDescription}
            onChange={(e) => setAlbumDescription(e.target.value)}
            sx={{ mb: 2 }}
          />
          <Box display="flex" gap={1}>
            <Button variant="contained" onClick={handleCreateAlbum} disabled={createMutation.isPending}>
              Create
            </Button>
            <Button variant="outlined" onClick={() => setOpenDialog(false)}>
              Cancel
            </Button>
          </Box>
        </Box>
      </Dialog>
    </>
  );
}