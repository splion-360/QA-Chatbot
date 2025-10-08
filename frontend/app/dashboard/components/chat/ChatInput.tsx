'use client';

import { useState, forwardRef } from 'react';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import SendIcon from '@mui/icons-material/Send';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

const ChatInput = forwardRef<HTMLInputElement, ChatInputProps>(
  ({ onSendMessage, disabled = false }, ref) => {
    const [message, setMessage] = useState('');

    const handleSend = () => {
      if (message.trim() && !disabled) {
        onSendMessage(message.trim());
        setMessage('');
      }
    };

    const handleKeyPress = (event: React.KeyboardEvent) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSend();
      }
    };


    return (
      <Paper
        elevation={1}
        sx={{
          p: 1,
          borderRadius: 3,
          border: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Stack direction="row" spacing={1} alignItems="flex-end">
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder="Type a message..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={disabled}
            variant="outlined"
            size="small"
            inputRef={ref}
            sx={{
              '& .MuiOutlinedInput-root': {
                border: 'none',
                '& fieldset': {
                  border: 'none',
                },
                '&:hover fieldset': {
                  border: 'none',
                },
                '&.Mui-focused fieldset': {
                  border: 'none',
                },
              },
              '& .MuiInputBase-input': {
                py: 1,
              },
            }}
          />

          <IconButton
            color="primary"
            onClick={handleSend}
            disabled={disabled || !message.trim()}
            sx={{
              mb: 0.5,
              bgcolor: message.trim() && !disabled ? 'primary.main' : 'transparent',
              color: message.trim() && !disabled ? 'primary.contrastText' : 'text.disabled',
              '&:hover': {
                bgcolor: message.trim() && !disabled ? 'primary.dark' : 'action.hover',
              },
            }}
          >
            <SendIcon />
          </IconButton>
        </Stack>
      </Paper>
    );
  });

ChatInput.displayName = 'ChatInput';

export default ChatInput;