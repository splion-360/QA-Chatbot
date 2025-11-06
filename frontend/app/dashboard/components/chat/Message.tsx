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
import ReactMarkdown from 'react-markdown';
import toast from 'react-hot-toast';
import { Message as MessageType } from './ChatContainer';

interface MessageProps {
  message: MessageType;
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      toast.success('Copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy');
    }
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

      <Box 
        sx={{ 
          maxWidth: '70%', 
          minWidth: '100px', 
          position: 'relative',
          '&:hover .copy-button': {
            opacity: 1,
          },
        }}
      >
        <Paper
          elevation={0}
          sx={{
            p: 2,
            bgcolor: isUser ? 'primary.main' : 'background.paper',
            color: isUser ? 'primary.contrastText' : 'text.primary',
            borderRadius: 2,
            border: isUser ? 'none' : '1px solid',
            borderColor: 'divider',
          }}
        >
          <Box
            sx={{
              '& p': { margin: 0, marginBottom: 1 },
              '& p:last-child': { marginBottom: 0 },
              '& ul, & ol': { paddingLeft: 3, margin: 0 },
              '& li': { marginBottom: 0.5 },
              '& code': {
                backgroundColor: 'action.hover',
                padding: '2px 4px',
                borderRadius: 1,
                fontSize: '0.875em',
                fontFamily: 'monospace',
              },
              '& pre': {
                backgroundColor: 'action.hover',
                padding: 2,
                borderRadius: 1,
                overflow: 'auto',
                margin: '8px 0',
              },
              '& pre code': {
                backgroundColor: 'transparent',
                padding: 0,
              },
              '& blockquote': {
                borderLeft: '4px solid',
                borderColor: 'divider',
                paddingLeft: 2,
                margin: '8px 0',
                fontStyle: 'italic',
              },
              '& h1, & h2, & h3, & h4, & h5, & h6': {
                margin: '16px 0 8px 0',
                fontWeight: 'bold',
              },
              '& h1:first-child, & h2:first-child, & h3:first-child': {
                marginTop: 0,
              },
            }}
          >
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </Box>
        </Paper>

        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: isUser ? 'flex-end' : 'flex-start',
            mt: 0.5,
            gap: 1,
          }}
        >
          <Typography
            variant="caption"
            color="text.secondary"
          >
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </Typography>
          
          <IconButton
            className="copy-button"
            size="small"
            onClick={handleCopy}
            sx={{
              opacity: 0,
              transition: 'opacity 0.2s',
              color: 'text.secondary',
              padding: '2px',
              minWidth: '20px',
              width: '20px',
              height: '20px',
              '&:hover': {
                bgcolor: 'action.hover',
              },
            }}
          >
            <ContentCopyIcon sx={{ fontSize: 12 }} />
          </IconButton>
        </Box>
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