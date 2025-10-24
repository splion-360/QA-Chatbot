'use client';

import * as React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Avatar from '@mui/material/Avatar';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import Alert from '@mui/material/Alert';
import InfinityLoader from './InfinityLoader';
import PersonIcon from '@mui/icons-material/Person';
import SaveIcon from '@mui/icons-material/Save';
import { createClient } from '@utils/supabase/client';
import { useToast } from './ToastProvider';

interface AccountManagementDialogProps {
  open: boolean;
  onClose: () => void;
  onUserUpdate: () => void;
}

interface UserData {
  id: string;
  email: string;
  display_name?: string;
  created_at: string;
}

export default function AccountManagementDialog({
  open,
  onClose,
  onUserUpdate,
}: AccountManagementDialogProps) {
  const [userData, setUserData] = React.useState<UserData | null>(null);
  const [displayName, setDisplayName] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState('');
  const [success, setSuccess] = React.useState(false);
  const supabase = createClient();
  const { showToast } = useToast();

  React.useEffect(() => {
    if (open) {
      fetchUserData();
    }
  }, [open]);

  const fetchUserData = async () => {
    setLoading(true);
    setError('');

    try {
      // Get current user session
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (sessionError || !session?.user) {
        setError('No user session found');
        setLoading(false);
        return;
      }

      // Fetch user data from users table
      const { data, error } = await supabase
        .from('users')
        .select('id, email, name, created_at')
        .eq('id', session.user.id)
        .single();

      if (error) {
        showToast('User data not found', 'warning');
      } else {
        setUserData(data);
        setDisplayName(data.name || '');
      }
    } catch (error) {
      showToast('Failed to load account data', 'error');
      setError('Failed to load user data');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!userData) return;

    const startTime = Date.now();
    setSaving(true);
    setError('');
    setSuccess(false);

    try {
      const { error } = await supabase
        .from('users')
        .upsert({
          id: userData.id,
          email: userData.email,
          name: displayName.trim() || null,
        })
        .eq('id', userData.id);

      if (error) {
        setError('Failed to update display name');
        showToast('Failed to save display name', 'error');
      } else {
        setSuccess(true);
        showToast('Display name updated successfully!', 'success');
        setUserData(prev => prev ? { ...prev, display_name: displayName.trim() } : null);
        onUserUpdate();

        // Auto-close dialog after successful save
        setTimeout(() => {
          onClose();
          setSuccess(false);
        }, 1500);
      }
    } catch (error) {
      showToast('An unexpected error occurred', 'error');
      setError('An unexpected error occurred');
    } finally {
      const elapsedTime = Date.now() - startTime;
      const minDuration = 2000;
      
      if (elapsedTime < minDuration) {
        setTimeout(() => setSaving(false), minDuration - elapsedTime);
      } else {
        setSaving(false);
      }
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      return 'Unknown';
    }
  };

  const handleClose = () => {
    setError('');
    setSuccess(false);
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2 }
      }}
    >
      <DialogTitle>
        <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
          My Account
        </Typography>
      </DialogTitle>

      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <Typography>Loading account information...</Typography>
          </Box>
        ) : userData ? (
          <Stack spacing={3}>
            {/* User Avatar and Basic Info */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 2 }}>
              <Avatar
                sx={{
                  width: 64,
                  height: 64,
                  bgcolor: 'primary.main',
                  fontSize: 24,
                  fontWeight: 600,
                }}
              >
                {userData.display_name
                  ? userData.display_name.charAt(0).toUpperCase()
                  : userData.email.charAt(0).toUpperCase()
                }
              </Avatar>
              <Box>
                <Typography variant="h6">
                  {userData.display_name || userData.email.split('@')[0]}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {userData.email}
                </Typography>
              </Box>
            </Box>

            <Divider />

            {/* Display Name Editor */}
            <Box>
              <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                Display Name
              </Typography>
              <TextField
                fullWidth
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Enter your display name"
                helperText="This is how your name will appear in the chat interface"
                variant="outlined"
                size="medium"
              />
            </Box>

            <Divider />

            {/* Account Information */}
            <Box>
              <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>
                Account Information
              </Typography>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Email Address
                  </Typography>
                  <Typography variant="body1">
                    {userData.email}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Account Created
                  </Typography>
                  <Typography variant="body1">
                    {formatDate(userData.created_at)}
                  </Typography>
                </Box>
              </Stack>
            </Box>

            {/* Success/Error Messages */}
            {success && (
              <Alert severity="success">
                Display name updated successfully!
              </Alert>
            )}
            {error && (
              <Alert severity="error">
                {error}
              </Alert>
            )}
          </Stack>
        ) : (
          <Alert severity="error">
            Failed to load account information
          </Alert>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 3, pt: 1 }}>
        <Button onClick={handleClose} disabled={saving}>
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={!userData || loading || saving}
          startIcon={saving ? <InfinityLoader size={20} /> : <SaveIcon />}
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}