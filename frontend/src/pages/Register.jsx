
import React, { useState } from 'react';
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

export default function Register() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [focusedField, setFocusedField] = useState(null);
  const [isTypingPassword, setIsTypingPassword] = useState(false);

  const handleSubmit = async e => {
    e.preventDefault();
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await api().post('/auth/register', { email, password });
      setToken(res.data.token); // adjust field name if needed
      navigate('/');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
      <Paper sx={{ p: 4, width: 400 }}>
        <Mascot focusedField={focusedField} isTypingPassword={isTypingPassword} />
        <Typography variant="h5" mb={2}>
          Register
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
          <TextField
            label="Confirm Password"
            type="password"
            fullWidth
            margin="normal"
            value={confirm}
            onFocus={() => {
              setFocusedField('password');
              setIsTypingPassword(true);
            }}
            onBlur={() => {
              setFocusedField(null);
              setIsTypingPassword(false);
            }}
            onChange={e => {
              setConfirm(e.target.value);
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
            {loading ? 'Registering...' : 'Register'}
          </Button>
        </Box>
        <Typography variant="body2" mt={2}>
          Already have an account?{' '}
          <Link component={RouterLink} to="/login">
            Login
          </Link>
        </Typography>
      </Paper>
    </Box>
  );
}
