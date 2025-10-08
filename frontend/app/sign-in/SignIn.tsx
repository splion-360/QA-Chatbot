import * as React from 'react';
import { useRouter } from 'next/navigation';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CssBaseline from '@mui/material/CssBaseline';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import MuiCard from '@mui/material/Card';
import { styled } from '@mui/material/styles';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import AppTheme from '../shared-theme/AppTheme';
import ColorModeSelect from '../shared-theme/ColorModeSelect';
import { GoogleIcon } from './components/CustomIcons';
import { createClient } from '@utils/supabase/client';
import { handleAuthError } from '@utils/supabase/auth-helpers';
import { config } from '@utils/config';

const Card = styled(MuiCard)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignSelf: 'center',
  width: '100%',
  padding: theme.spacing(4),
  gap: theme.spacing(2),
  margin: 'auto',
  [theme.breakpoints.up('sm')]: {
    maxWidth: '450px',
  },
  boxShadow:
    'hsla(220, 30%, 5%, 0.05) 0px 5px 15px 0px, hsla(220, 25%, 10%, 0.05) 0px 15px 35px -5px',
  ...theme.applyStyles('dark', {
    boxShadow:
      'hsla(220, 30%, 5%, 0.5) 0px 5px 15px 0px, hsla(220, 25%, 10%, 0.08) 0px 15px 35px -5px',
  }),
}));

const SignInContainer = styled(Stack)(({ theme }) => ({
  height: 'calc((1 - var(--template-frame-height, 0)) * 100dvh)',
  minHeight: '100%',
  padding: theme.spacing(2),
  [theme.breakpoints.up('sm')]: {
    padding: theme.spacing(4),
  },
  '&::before': {
    content: '""',
    display: 'block',
    position: 'absolute',
    zIndex: -1,
    inset: 0,
    backgroundImage:
      'radial-gradient(ellipse at 50% 50%, hsl(210, 100%, 97%), hsl(0, 0%, 100%))',
    backgroundRepeat: 'no-repeat',
    ...theme.applyStyles('dark', {
      backgroundImage:
        'radial-gradient(at 50% 50%, hsla(210, 100%, 16%, 0.5), hsl(220, 30%, 5%))',
    }),
  },
}));

export default function SignIn(props: { disableCustomTheme?: boolean }) {
  const [loading, setLoading] = React.useState(false);
  const [authError, setAuthError] = React.useState('');

  const router = useRouter();
  const supabase = createClient();

  React.useEffect(() => {
    // Clear any invalid sessions on component mount
    const checkSession = async () => {
      try {
        const { error } = await supabase.auth.getSession();
        if (error) {
          await handleAuthError(error);
        }
      } catch (error: any) {
        await handleAuthError(error);
      }
    };
    checkSession();
  }, [supabase.auth]);


  const handleGoogleSignIn = async () => {
    setLoading(true);
    setAuthError('');

    try {
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${typeof window !== 'undefined' ? window.location.origin : config.baseUrl}/auth/callback`,
          queryParams: {
            access_type: 'offline',
          },
        },
      });

      if (error) {
        await handleAuthError(error);
        setAuthError(error.message);
        setLoading(false);
      }
      // Don't set loading to false here as user will be redirected
    } catch (error: any) {
      await handleAuthError(error);
      setAuthError('An unexpected error occurred. Please try again.');
      setLoading(false);
    }
  };

  return (
    <AppTheme {...props}>
      <CssBaseline enableColorScheme />
      <SignInContainer direction="column" justifyContent="space-between">
        <ColorModeSelect sx={{ position: 'fixed', top: '1rem', right: '1rem' }} />
        <Card variant="outlined">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Box
              component="img"
              src="/chatbot.svg"
              alt="QA Chatbot"
              sx={{
                width: 40,
                height: 40,
              }}
            />
            <Typography
              variant="h5"
              component="div"
              sx={{ fontWeight: 600, color: 'primary.main' }}
            >
              QA Chatbot
            </Typography>
          </Box>
          <Typography
            component="h1"
            variant="h4"
            sx={{ width: '100%', fontSize: 'clamp(2rem, 10vw, 2.15rem)' }}
          >
            Sign in
          </Typography>

          {authError && (
            <Alert severity="error" sx={{ width: '100%' }}>
              {authError}
            </Alert>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Button
              fullWidth
              variant="contained"
              onClick={handleGoogleSignIn}
              startIcon={<GoogleIcon />}
              disabled={loading}
              sx={{ position: 'relative' }}
            >
              {loading && (
                <CircularProgress size={24} sx={{ position: 'absolute' }} />
              )}
              {loading ? 'Signing in...' : 'Sign in with Google'}
            </Button>
          </Box>
        </Card>
      </SignInContainer>
    </AppTheme>
  );
}
