import { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import { useToken } from '../hooks/useToken';
import { loginUser } from '../api/auth';
import getErrorMessage from '../utils/getErrorMessage';
import { 
  Box, TextField, Button, Alert, CircularProgress, Typography, 
  Container, Paper, Link, InputAdornment, IconButton
} from '@mui/material';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import ImageIcon from '@mui/icons-material/Image';

export default function Login() {
  const navigate = useNavigate();
  const { setToken } = useToken();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      console.log('Attempting login with:', email);
      const response = await loginUser({ email, password });
      console.log('Login response:', response);
      
      const token = response?.data?.access_token;
      
      if (!token) {
        throw new Error('No access_token in response');
      }

      console.log('✓ Token received:', token.substring(0, 20) + '...');
      
      localStorage.setItem('jwt', token);
      console.log('✓ Token saved to localStorage');
      
      setToken(token);
      console.log('✓ Token set in context');
      
      navigate('/gallery');
    } catch (err) {
      console.error('❌ Login error:', err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)',
        py: 4
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={24}
          sx={{
            p: 4,
            borderRadius: 3,
            backdropFilter: 'blur(10px)',
            bgcolor: 'rgba(255, 255, 255, 0.98)'
          }}
        >
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            {/* Logo/Icon */}
            <Box
              sx={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                bgcolor: 'primary.main',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: 4,
                mb: 2
              }}
            >
              <ImageIcon sx={{ fontSize: 48, color: 'white' }} />
            </Box>

            <Typography 
              variant="h4" 
              align="center" 
              gutterBottom 
              sx={{ fontWeight: 700, color: 'primary.main' }}
            >
              Smart Gallery
            </Typography>
            
            <Typography 
              variant="body1" 
              align="center" 
              color="textSecondary" 
              sx={{ mb: 4 }}
            >
              AI-Powered Image Organization
            </Typography>

            {error && (
              <Alert severity="error" sx={{ mb: 3, borderRadius: 2, width: '100%' }}>
                {error}
              </Alert>
            )}

            <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%' }}>
              <TextField
                fullWidth
                label="Email Address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                margin="normal"
                required
                autoComplete="email"
                autoFocus
                sx={{
                  '& .MuiOutlinedInput-root': {
                    borderRadius: 2
                  }
                }}
              />

              <TextField
                fullWidth
                label="Password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                margin="normal"
                required
                autoComplete="current-password"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  )
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    borderRadius: 2
                  }
                }}
              />

              <Button
                fullWidth
                type="submit"
                variant="contained"
                size="large"
                disabled={loading}
                sx={{ 
                  mt: 3, 
                  mb: 2,
                  py: 1.5,
                  borderRadius: 2,
                  textTransform: 'none',
                  fontSize: '1.1rem',
                  fontWeight: 600,
                  boxShadow: 4,
                  '&:hover': {
                    boxShadow: 8
                  }
                }}
              >
                {loading ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  'Sign In'
                )}
              </Button>

              <Box sx={{ textAlign: 'center', mt: 2 }}>
                <Typography variant="body2" color="textSecondary">
                  Don't have an account?{' '}
                  <Link
                    component={RouterLink}
                    to="/register"
                    sx={{
                      fontWeight: 600,
                      textDecoration: 'none',
                      '&:hover': { textDecoration: 'underline' }
                    }}
                  >
                    Sign Up
                  </Link>
                </Typography>
              </Box>
            </Box>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}