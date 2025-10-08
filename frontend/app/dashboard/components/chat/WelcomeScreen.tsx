'use client';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import { alpha } from '@mui/material/styles';

interface WelcomeScreenProps {
  onSendMessage: (message: string) => void;
}

const suggestionQuestions = [
  "How can I help you today?",
  "What would you like to know?",
  "Ask me anything about our services",
  "Need help with a specific topic?",
];

export default function WelcomeScreen({ onSendMessage }: WelcomeScreenProps) {
  const handleSuggestionClick = (suggestion: string) => {
    onSendMessage(suggestion);
  };

  return (
    <Box
      sx={{
        flexGrow: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        p: 4,
        textAlign: 'center',
      }}
    >
      <Stack spacing={4} sx={{ maxWidth: 600, width: '100%' }}>
        {/* Welcome Header */}
        <Box>
          <Box
            component="img"
            src="/mascot.svg"
            alt="QA Chatbot"
            sx={{
              width: 120,
              height: 120,
              mb: 2,
              opacity: 0.9,
              objectFit: 'contain',
            }}
          />
          <Typography variant="h4" component="h1" gutterBottom>
            Welcome to QA Chatbot
          </Typography>
          <Typography variant="body1" color="text.secondary">
            I'm here to help answer your questions and assist you with anything you need.
            Start a conversation by typing a message or selecting one of the suggestions below.
          </Typography>
        </Box>

        {/* Suggestion Cards */}
        <Paper
          elevation={0}
          sx={{
            p: 3,
            bgcolor: (theme) => alpha(theme.palette.primary.main, 0.04),
            border: '1px solid',
            borderColor: (theme) => alpha(theme.palette.primary.main, 0.1),
            borderRadius: 2,
          }}
        >
          <Typography variant="h6" gutterBottom>
            Try asking:
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {suggestionQuestions.map((suggestion, index) => (
              <Chip
                key={index}
                label={suggestion}
                variant="outlined"
                clickable
                onClick={() => handleSuggestionClick(suggestion)}
                sx={{
                  mb: 1,
                  '&:hover': {
                    bgcolor: 'primary.main',
                    color: 'primary.contrastText',
                    borderColor: 'primary.main',
                  },
                }}
              />
            ))}
          </Stack>
        </Paper>

        {/* Features */}
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              flex: 1,
              textAlign: 'center',
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            <Typography variant="subtitle2" gutterBottom>
              💬 Natural Conversation
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Chat naturally as you would with a human assistant
            </Typography>
          </Paper>

          <Paper
            elevation={0}
            sx={{
              p: 2,
              flex: 1,
              textAlign: 'center',
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            <Typography variant="subtitle2" gutterBottom>
              🎯 Smart Responses
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Get accurate answers based on your uploaded documents
            </Typography>
          </Paper>
        </Stack>
      </Stack>
    </Box>
  );
}