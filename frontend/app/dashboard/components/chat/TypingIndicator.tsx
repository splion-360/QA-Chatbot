'use client';

import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Avatar from '@mui/material/Avatar';
import Stack from '@mui/material/Stack';
import { styled, keyframes } from '@mui/material/styles';

const bounce = keyframes`
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
`;

const Dot = styled(Box)(({ theme }) => ({
  width: 8,
  height: 8,
  borderRadius: '50%',
  backgroundColor: theme.palette.text.secondary,
  animation: `${bounce} 1.4s infinite ease-in-out both`,
  '&:nth-of-type(1)': {
    animationDelay: '-0.32s',
  },
  '&:nth-of-type(2)': {
    animationDelay: '-0.16s',
  },
}));

export default function TypingIndicator() {
  return (
    <Stack
      direction="row"
      spacing={2}
      sx={{
        justifyContent: 'flex-start',
        alignItems: 'flex-start',
      }}
    >
      <Avatar
        sx={{
          bgcolor: 'transparent',
          width: 48,
          height: 48,
        }}
      >
        <Box
          component="img"
          src="/mascot.svg"
          alt="AI Assistant"
          sx={{
            width: 48,
            height: 48,
            objectFit: 'contain',
          }}
        />
      </Avatar>
      
      <Paper
        elevation={0}
        sx={{
          p: 2,
          bgcolor: 'background.paper',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          minWidth: 60,
        }}
      >
        <Stack direction="row" spacing={0.5} justifyContent="center">
          <Dot />
          <Dot />
          <Dot />
        </Stack>
      </Paper>
    </Stack>
  );
}