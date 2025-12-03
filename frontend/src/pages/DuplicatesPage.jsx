import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Card,
  CardMedia,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Grid,
  AppBar,
  Toolbar,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import LogoutIcon from '@mui/icons-material/Logout';
import { useNavigate } from 'react-router-dom';
import { api, setToken } from '../store/auth.js';

async function fetchDuplicates() {
  const client = api();
  const res = await client.get('/search/duplicates');
  return res.data;
}

export default function DuplicatesPage() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['duplicates'],
    queryFn: fetchDuplicates,
  });

  const handleLogout = () => {
    setToken(null);
    navigate('/login');
  };

  const duplicateGroups = data || [];

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Duplicate Images
          </Typography>
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
            {error?.response?.data?.detail || 'Failed to load duplicates'}
          </Alert>
        )}

        {duplicateGroups.length === 0 && !isLoading && (
          <Alert severity="success">No duplicate images found!</Alert>
        )}

        {duplicateGroups.map((group, groupIdx) => (
          <Accordion key={groupIdx} sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>
                Similar Images Group {groupIdx + 1}
                {group.images && ` (${group.images.length} images)`}
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                {group.images?.map((img, imgIdx) => (
                  <Grid item xs={12} sm={6} md={4} key={imgIdx}>
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
                        <Typography variant="caption">
                          Similarity: {group.similarity_score}%
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>
    </>
  );
}