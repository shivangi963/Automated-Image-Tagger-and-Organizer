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
  CircularProgress,
  Container,
} from '@mui/material';
import { registerUser } from '../api/auth';
import { useToken } from '../hooks/useToken';
import Mascot from '../components/Mascot.jsx';
import getErrorMessage from '../utils/getErrorMessage.js';

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
      const response = await registerUser({
        full_name: fullName,
        email,
        password,
      });
      setToken(response.data.access_token);
      navigate('/gallery');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        minHeight="100vh"
        sx={{ mt: 8 }}
      >
        <Mascot focusedField={focusedField} isTypingPassword={isTypingPassword} />
        <Typography variant="h4" mb={3}>
          Register
        </Typography>
        {error && (
          <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%' }}>
          <TextField
            label="Full Name"
            fullWidth
            margin="normal"
            value={fullName}
            onFocus={() => setFocusedField('name')}
            onBlur={() => setFocusedField(null)}
            onChange={e => setFullName(e.target.value)}
            required
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
            required
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
            required
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
            required
          />
          <Button
            type="submit"
            variant="contained"
            fullWidth
            sx={{ mt: 2 }}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Register'}
          </Button>
        </Box>
        <Typography variant="body2" mt={2}>
          Already have an account?{' '}
          <Link component={RouterLink} to="/login">
            Login
          </Link>
        </Typography>
      </Box>
    </Container>
  );
}