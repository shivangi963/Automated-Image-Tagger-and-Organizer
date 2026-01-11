import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box, Button, Grid, Card, CardMedia, CardContent, Typography,
  Chip, CircularProgress, Alert, Container, Paper, InputBase, IconButton,
  Tooltip
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import ImageSearchIcon from '@mui/icons-material/ImageSearch';
import api from '../api/axiosClient.js';
import getErrorMessage from '../utils/getErrorMessage.js';
import AppLayout from '../components/AppLayout.jsx';

async function searchImages(query) {
  if (!query || !query.trim()) {
    return { images: [], total: 0 };
  }
  try {
    const res = await api.get('/search', { params: { query: query.trim() } });
    const images = res.data.images || [];
    
    // Enrich images with URLs
    const enrichedImages = await Promise.all(
      images.map(async (img) => {
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
      images: enrichedImages, 
      total: res.data.total || enrichedImages.length 
    };
  } catch (error) {
    console.error('Search error:', error);
    throw error;
  }
}

export default function Search() {
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['search', search],
    queryFn: () => searchImages(search),
    enabled: search.length > 0,
  });

  const handleSearch = (e) => {
    e?.preventDefault();
    if (searchInput.trim()) {
      setSearch(searchInput.trim());
    }
  };

  const handleClear = () => {
    setSearchInput('');
    setSearch('');
  };

  const images = data?.images || [];
  const total = data?.total || 0;

  const getTags = (img) => {
    if (!img.tags) return [];
    return img.tags.map(tag => {
      if (typeof tag === 'string') return tag;
      return tag.tag_name || tag.name || tag.label || '';
    }).filter(Boolean);
  };

  return (
    <AppLayout title="Search">
      <Container maxWidth="xl" sx={{ py: 3 }}>
        {/* Search Bar */}
        <Paper
          component="form"
          onSubmit={handleSearch}
          sx={{
            p: 2,
            mb: 4,
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            boxShadow: 3
          }}
        >
          <SearchIcon sx={{ fontSize: 32, color: 'primary.main' }} />
          <InputBase
            placeholder="Search by tags, objects, colors, or metadata..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            sx={{ flex: 1, fontSize: '1.1rem' }}
            autoFocus
          />
          {searchInput && (
            <IconButton onClick={handleClear}>
              <ClearIcon />
            </IconButton>
          )}
          <Button
            type="submit"
            variant="contained"
            size="large"
            startIcon={<SearchIcon />}
            disabled={!searchInput.trim()}
          >
            Search
          </Button>
        </Paper>

        {/* Search Tips */}
        {!search && (
          <Paper sx={{ p: 3, mb: 4, bgcolor: 'info.lighter' }}>
            <Typography variant="h6" gutterBottom>
              Search Tips
            </Typography>
            <Typography variant="body2" paragraph>
              • Search for objects: <strong>person</strong>, <strong>car</strong>, <strong>dog</strong>
            </Typography>
            <Typography variant="body2" paragraph>
              • Search for places: <strong>indoor</strong>, <strong>outdoor</strong>, <strong>beach</strong>
            </Typography>
            <Typography variant="body2">
              • Combine terms: <strong>person outdoor</strong>, <strong>car street</strong>
            </Typography>
          </Paper>
        )}

        {/* Results Info */}
        {search && !isLoading && (
          <Paper sx={{ p: 2, mb: 3, bgcolor: total > 0 ? 'success.lighter' : 'warning.lighter' }}>
            <Typography variant="body1">
              {total > 0 ? (
                <>Found <strong>{total}</strong> result{total !== 1 ? 's' : ''} for "<strong>{search}</strong>"</>
              ) : (
                <>No results found for "<strong>{search}</strong>". Try different keywords.</>
              )}
            </Typography>
          </Paper>
        )}

        {isLoading && (
          <Box display="flex" flexDirection="column" alignItems="center" py={8}>
            <CircularProgress size={60} />
            <Typography variant="body1" color="textSecondary" sx={{ mt: 2 }}>
              Searching...
            </Typography>
          </Box>
        )}

        {isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {getErrorMessage(error)}
          </Alert>
        )}

        {/* Empty State */}
        {!search && !isLoading && (
          <Box display="flex" flexDirection="column" alignItems="center" py={8}>
            <ImageSearchIcon sx={{ fontSize: 120, color: 'grey.300', mb: 2 }} />
            <Typography variant="h5" color="textSecondary" gutterBottom>
              Start Searching
            </Typography>
            <Typography variant="body1" color="textSecondary" align="center">
              Enter keywords to find images by their AI-detected tags
            </Typography>
          </Box>
        )}

        {/* No Results */}
        {search && !isLoading && images.length === 0 && (
          <Box display="flex" flexDirection="column" alignItems="center" py={8}>
            <ImageSearchIcon sx={{ fontSize: 120, color: 'grey.300', mb: 2 }} />
            <Typography variant="h5" color="textSecondary" gutterBottom>
              No Images Found
            </Typography>
            <Typography variant="body1" color="textSecondary" align="center" sx={{ mb: 2 }}>
              Try different keywords or check your spelling
            </Typography>
            <Button variant="outlined" onClick={handleClear}>
              Clear Search
            </Button>
          </Box>
        )}

        {/* Results Grid */}
        <Grid container spacing={3}>
          {images.map((img) => {
            const tags = getTags(img);
            return (
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
                    image={img.url || img.thumbnailUrl || 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjE4IiBmaWxsPSIjYWFhIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+TG9hZGluZy4uLjwvdGV4dD48L3N2Zz4='}
                    alt={img.filename || img.original_filename || img.name}
                    sx={{ objectFit: 'cover' }}
                  />
                  <CardContent>
                    <Tooltip title={img.filename || img.original_filename || img.name}>
                      <Typography variant="subtitle2" noWrap gutterBottom>
                        {img.filename || img.original_filename || img.name}
                      </Typography>
                    </Tooltip>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {tags.map((tagName, idx) => {
                        const isMatch = search && tagName.toLowerCase().includes(search.toLowerCase());
                        return (
                          <Chip
                            key={idx}
                            label={tagName}
                            size="small"
                            variant={isMatch ? 'filled' : 'outlined'}
                            color={isMatch ? 'primary' : 'default'}
                          />
                        );
                      })}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      </Container>
    </AppLayout>
  );
}