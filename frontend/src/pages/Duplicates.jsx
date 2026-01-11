import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box, Card, CardMedia, CardContent, Typography, CircularProgress,
  Alert, Grid, Container, Accordion, AccordionSummary, AccordionDetails,
  Chip, IconButton, Button, Tooltip
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import api from '../api/axiosClient.js';
import getErrorMessage from '../utils/getErrorMessage.js';
import AppLayout from '../components/AppLayout.jsx';

async function fetchDuplicates() {
  try {
    const res = await api.get('/search/duplicates');
    const groups = res.data || [];
    
    // Enrich each image in each group with URLs
    const enrichedGroups = await Promise.all(
      groups.map(async (group) => {
        const enrichedImages = await Promise.all(
          (group.images || []).map(async (img) => {
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
          })
        );
        return {
          ...group,
          images: enrichedImages
        };
      })
    );
    
    return enrichedGroups;
  } catch (error) {
    console.error('Error fetching duplicates:', error);
    throw error;
  }
}

async function deleteImage(imageId) {
  await api.delete(`/images/${imageId}`);
}

export default function Duplicates() {
  const queryClient = useQueryClient();

  const { data = [], isLoading, isError, error } = useQuery({
    queryKey: ['duplicates'],
    queryFn: fetchDuplicates,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteImage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['duplicates'] });
      queryClient.invalidateQueries({ queryKey: ['images'] });
    },
  });

  const handleDeleteDuplicates = async (group, keepImageId) => {
    const imagesToDelete = group.images
      .filter(img => (img._id || img.id) !== keepImageId)
      .map(img => img._id || img.id);

    if (window.confirm(`Delete ${imagesToDelete.length} duplicate image(s)?`)) {
      for (const id of imagesToDelete) {
        await deleteMutation.mutateAsync(id);
      }
    }
  };

  return (
    <AppLayout title="Duplicates">
      <Container maxWidth="xl" sx={{ py: 3 }}>
        {isLoading && (
          <Box display="flex" flexDirection="column" alignItems="center" py={8}>
            <CircularProgress size={60} />
            <Typography variant="body1" color="textSecondary" sx={{ mt: 2 }}>
              Analyzing images for duplicates...
            </Typography>
          </Box>
        )}

        {isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {getErrorMessage(error)}
          </Alert>
        )}

        {/* Empty State - No Duplicates */}
        {!isLoading && data.length === 0 && (
          <Box display="flex" flexDirection="column" alignItems="center" py={8}>
            <CheckCircleIcon sx={{ fontSize: 120, color: 'success.main', mb: 2 }} />
            <Typography variant="h5" color="textSecondary" gutterBottom>
              No Duplicates Found!
            </Typography>
            <Typography variant="body1" color="textSecondary" align="center">
              All your images are unique. Great job organizing!
            </Typography>
          </Box>
        )}

        {/* Summary */}
        {!isLoading && data.length > 0 && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            Found <strong>{data.length}</strong> group{data.length !== 1 ? 's' : ''} of similar images. 
            Review and delete duplicates to free up space.
          </Alert>
        )}

        {/* Duplicate Groups */}
        {data.map((group, groupIdx) => {
          const similarityPercent = Math.round((group.similarity_score || 0) * 100);
          return (
            <Accordion key={groupIdx} sx={{ mb: 2 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                  <ContentCopyIcon color="warning" />
                  <Typography sx={{ flexGrow: 1 }}>
                    Similar Images Group {groupIdx + 1}
                  </Typography>
                  <Chip
                    label={`${group.images?.length || 0} images`}
                    color="warning"
                    size="small"
                  />
                  <Chip
                    label={`${similarityPercent}% similar`}
                    color="info"
                    size="small"
                  />
                </Box>
              </AccordionSummary>

              <AccordionDetails>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="textSecondary" gutterBottom>
                    These images are very similar. Keep one and delete the rest to save space.
                  </Typography>
                </Box>

                <Grid container spacing={2}>
                  {group.images?.map((img, imgIdx) => (
                    <Grid item xs={12} sm={6} md={4} lg={3} key={imgIdx}>
                      <Card
                        sx={{
                          height: '100%',
                          display: 'flex',
                          flexDirection: 'column',
                          position: 'relative'
                        }}
                      >
                        {imgIdx === 0 && (
                          <Chip
                            label="Original"
                            color="success"
                            size="small"
                            sx={{ position: 'absolute', top: 8, left: 8, zIndex: 1 }}
                          />
                        )}
                        
                        <CardMedia
                          component="img"
                          height="200"
                          image={img.url || img.thumbnailUrl || 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjE4IiBmaWxsPSIjYWFhIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+TG9hZGluZy4uLjwvdGV4dD48L3N2Zz4='}
                          alt={img.filename || img.original_filename || img.name}
                          sx={{ objectFit: 'cover' }}
                        />

                        <CardContent sx={{ flexGrow: 1, pb: 1 }}>
                          <Tooltip title={img.filename || img.original_filename || img.name}>
                            <Typography variant="body2" noWrap gutterBottom>
                              {img.filename || img.original_filename || img.name}
                            </Typography>
                          </Tooltip>
                          
                          {img.metadata && img.metadata.size_bytes && (
                            <Typography variant="caption" color="textSecondary" display="block">
                              Size: {Math.round((img.metadata.size_bytes || 0) / 1024)} KB
                            </Typography>
                          )}
                          
                          {img.created_at && (
                            <Typography variant="caption" color="textSecondary" display="block">
                              {new Date(img.created_at).toLocaleDateString()}
                            </Typography>
                          )}
                        </CardContent>

                        <Box sx={{ p: 2, pt: 0, display: 'flex', gap: 1 }}>
                          <Button
                            size="small"
                            variant="outlined"
                            color="success"
                            fullWidth
                            onClick={() => handleDeleteDuplicates(group, img._id || img.id)}
                          >
                            Keep This
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
                    </Grid>
                  ))}
                </Grid>
              </AccordionDetails>
            </Accordion>
          );
        })}
      </Container>
    </AppLayout>
  );
}