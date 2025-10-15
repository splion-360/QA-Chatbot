'use client';

import * as React from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Avatar from '@mui/material/Avatar';
import { createClient } from '@utils/supabase/client';
import PersonIcon from '@mui/icons-material/Person';
import OptionsMenu from './OptionsMenu';
import { useToast } from './ToastProvider';

interface UserData {
  id: string;
  email: string;
  name?: string;
  created_at: string;
}

export default function UserAccountSection() {
  const [userData, setUserData] = React.useState<UserData | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [mounted, setMounted] = React.useState(false);
  const [hasShownFallbackToast, setHasShownFallbackToast] = React.useState(false);

  const supabase = createClient();
  const { showToast } = useToast();

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const fetchUserData = React.useCallback(async () => {
    if (!mounted) return;

    try {
      // Get current user session
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (sessionError || !session?.user) {
        showToast('Authentication session not found', 'error');
        setLoading(false);
        return;
      }

      const { data, error } = await supabase
        .from('users')
        .select('id, email, name, created_at')
        .eq('id', session.user.id)
        .single();

      if (!error) {
        setUserData(data);
      }
    } catch (error) {
      showToast('Failed to load user account information', 'error');
    } finally {
      setLoading(false);
    }
  }, [mounted, supabase]);

  React.useEffect(() => {
    if (mounted) {
      fetchUserData();
    }
  }, [mounted, fetchUserData]);

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch (error) {
      return 'Unknown';
    }
  };

  if (!mounted) {
    return (
      <Stack
        direction="row"
        sx={{
          p: 2,
          gap: 1,
          alignItems: 'center',
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Avatar sx={{ width: 36, height: 36, bgcolor: 'grey.300' }}>
          <PersonIcon sx={{ fontSize: 20 }} />
        </Avatar>
        <Box sx={{ mr: 'auto' }}>
          <Typography variant="body2" sx={{ fontWeight: 500, lineHeight: '16px' }}>
            Loading...
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            Please wait
          </Typography>
        </Box>
      </Stack>
    );
  }

  if (loading) {
    return (
      <Stack
        direction="row"
        sx={{
          p: 2,
          gap: 1,
          alignItems: 'center',
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Avatar sx={{ width: 36, height: 36, bgcolor: 'grey.300' }}>
          <PersonIcon sx={{ fontSize: 20 }} />
        </Avatar>
        <Box sx={{ mr: 'auto' }}>
          <Typography variant="body2" sx={{ fontWeight: 500, lineHeight: '16px' }}>
            Loading...
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            Please wait
          </Typography>
        </Box>
      </Stack>
    );
  }

  if (!userData) {
    return (
      <Stack
        direction="row"
        sx={{
          p: 2,
          gap: 1,
          alignItems: 'center',
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Avatar sx={{ width: 36, height: 36, bgcolor: 'error.main' }}>
          <PersonIcon sx={{ fontSize: 20 }} />
        </Avatar>
        <Box sx={{ mr: 'auto' }}>
          <Typography variant="body2" sx={{ fontWeight: 500, lineHeight: '16px' }}>
            Guest User
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            Not signed in
          </Typography>
        </Box>
      </Stack>
    );
  }

  return (
    <Stack
      direction="row"
      sx={{
        p: 2,
        gap: 1,
        alignItems: 'center',
        borderTop: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Avatar
        sx={{
          width: 36,
          height: 36,
          bgcolor: 'primary.main',
          fontSize: 14,
          fontWeight: 600,
        }}
      >
        {userData.name ? userData.name.charAt(0).toUpperCase() : userData.email.charAt(0).toUpperCase()}
      </Avatar>
      <Box sx={{ mr: 'auto', minWidth: 0, flex: 1 }}>
        <Typography
          variant="body2"
          sx={{
            fontWeight: 500,
            lineHeight: '16px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {userData.name}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            color: 'text.secondary',
            display: 'block',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {userData.email}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            color: 'text.secondary',
            fontSize: '0.65rem',
            display: 'block',
          }}
        >
          Joined {formatDate(userData.created_at)}
        </Typography>
      </Box>
      <OptionsMenu onUserDataUpdate={fetchUserData} />
    </Stack>
  );
}