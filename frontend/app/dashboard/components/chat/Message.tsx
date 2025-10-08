'use client';

import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Avatar from '@mui/material/Avatar';
import Stack from '@mui/material/Stack';
import IconButton from '@mui/material/IconButton';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { Message as MessageType } from './ChatContainer';

interface MessageProps {
  message: MessageType;
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
  };

  return (
    <Stack
      direction="row"
      spacing={2}
      sx={{
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        alignItems: 'flex-start',
      }}
    >
      {!isUser && (
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
      )}

      <Box sx={{ maxWidth: '70%', minWidth: '100px' }}>
        <Paper
          elevation={0}
          sx={{
            p: 2,
            bgcolor: isUser ? 'primary.main' : 'background.paper',
            color: isUser ? 'primary.contrastText' : 'text.primary',
            borderRadius: 2,
            border: isUser ? 'none' : '1px solid',
            borderColor: 'divider',
            position: 'relative',
            '&:hover .copy-button': {
              opacity: 1,
            },
          }}
        >
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
            {message.content}
          </Typography>

          <IconButton
            className="copy-button"
            size="small"
            onClick={handleCopy}
            sx={{
              position: 'absolute',
              top: 4,
              right: 4,
              opacity: 0,
              transition: 'opacity 0.2s',
              color: isUser ? 'primary.contrastText' : 'text.secondary',
              '&:hover': {
                bgcolor: isUser ? 'rgba(255,255,255,0.1)' : 'action.hover',
              },
            }}
          >
            <ContentCopyIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </Paper>

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            display: 'block',
            mt: 0.5,
            textAlign: isUser ? 'right' : 'left',
          }}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </Typography>
      </Box>

      {isUser && (
        <Avatar
          sx={{
            bgcolor: 'secondary.main',
            width: 32,
            height: 32,
          }}
        >
          <PersonIcon sx={{ fontSize: 18 }} />
        </Avatar>
      )}
    </Stack>
  );
}