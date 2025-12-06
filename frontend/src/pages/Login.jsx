import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToken } from '../hooks/useToken';
import { loginUser } from '../api/auth';
import getErrorMessage from '../utils/getErrorMessage';
import { 
  Box, TextField, Button, Alert, CircularProgress, Typography, Container 
} from '@mui/material';

export default function Login() {
  const navigate = useNavigate();
  const { setToken } = useToken();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
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
      
      // ✅ Save to localStorage FIRST
      localStorage.setItem('jwt', token);
      console.log('✓ Token saved to localStorage');
      
      // ✅ Update context
      setToken(token);
      console.log('✓ Token set in context');
      
      // ✅ Navigate last
      navigate('/gallery');
    } catch (err) {
      console.error('❌ Login error:', err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography variant="h4" mb={3}>Login</Typography>
        
        {error && <Alert severity="error" sx={{ width: '100%', mb: 2 }}>{error}</Alert>}

        <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%' }}>
          <TextField
            fullWidth
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            margin="normal"
            required
          />
          <Button
            fullWidth
            type="submit"
            variant="contained"
            sx={{ mt: 2 }}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Login'}
          </Button>
        </Box>
      </Box>
    </Container>
  );
}