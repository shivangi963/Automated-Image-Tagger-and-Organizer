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
import { api } from '../store/auth.js';
import { useToken } from '../hooks/useToken.js';
import Mascot from '../components/Mascot.jsx';

export default function Register() {
  const navigate = useNavigate();
  const { setToken } = useToken();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [focusedField, setFocusedField] = useState(null);
  const [isTypingPassword, setIsTypingPassword] = useState(false);

  const handleSubmit = async e => {
    e.preventDefault();

    if (!fullName.trim() || !email.trim() || !password.trim()) {
      setError('All fields are required');
      return;
    }

    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const res = await api(null).post('/auth/register', {
        full_name: fullName,
        email,
        password,
      });
      setToken(res.data.access_token);  // Auto-login after registration
      navigate('/');
    } catch (err) {
      const errorMsg = Array.isArray(err?.response?.data)
        ? err.response.data[0]?.msg || 'Registration failed'
        : err?.response?.data?.detail || 'Registration failed';
      setError(errorMsg);
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
            label="Full Name"
            fullWidth
            margin="normal"
            value={fullName}
            onFocus={() => setFocusedField('name')}
            onBlur={() => setFocusedField(null)}
            onChange={e => setFullName(e.target.value)}
          />
          <TextField
            label="Email"
            fullWidth
            margin="normal"
            type="email"
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
            onFocus={() => setFocusedField('password')}
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
            onFocus={() => setFocusedField('confirm')}
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