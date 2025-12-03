import React from 'react';
import { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  TextField,
  Typography,
  Alert,
  Link,
  Paper,
} from '@mui/material';
import { api, setToken } from '../store/auth.js';
import Mascot from '../components/Mascot.jsx';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [focusedField, setFocusedField] = useState(null);
  const [isTypingPassword, setIsTypingPassword] = useState(false);

  const handleSubmit = async e => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api().post('/auth/login', { email, password });
      setToken(res.data.token); // adjust field name if needed
      navigate('/');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
      <Paper sx={{ p: 4, width: 400 }}>
        <Mascot focusedField={focusedField} isTypingPassword={isTypingPassword} />
        <Typography variant="h5" mb={2}>
          Login
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            label="Email"
            fullWidth
            margin="normal"
            value={email}
            onFocus={() => setFocusedField('email')}
            onBlur={() => setFocusedField(null)}
            onChange={e => setEmail(e.target.value)}
          />
          <TextField
            label="Password"
            type="password"
            fullWidth
            margin="normal"
            value={password}
            onFocus={() => {
              setFocusedField('password');
              setIsTypingPassword(true);
            }}
            onBlur={() => {
              setFocusedField(null);
              setIsTypingPassword(false);
            }}
            onChange={e => {
              setPassword(e.target.value);
              setIsTypingPassword(true);
            }}
          />
          <Button
            type="submit"
            variant="contained"
            fullWidth
            sx={{ mt: 2 }}
            disabled={loading}
          >
            {loading ? 'Logging in...' : 'Login'}
          </Button>
        </Box>
        <Typography variant="body2" mt={2}>
          Don&apos;t have an account?{' '}
          <Link component={RouterLink} to="/register">
            Register
          </Link>
        </Typography>
      </Paper>
    </Box>
  );
}
