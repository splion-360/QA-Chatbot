import * as React from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import DescriptionIcon from '@mui/icons-material/Description';
import SearchIcon from '@mui/icons-material/Search';
import ChatIcon from '@mui/icons-material/Chat';

const items = [
  {
    icon: <SmartToyIcon sx={{ color: 'text.secondary' }} />,
    title: 'AI-Powered Conversations',
    description:
      'Engage with an intelligent chatbot that understands context and provides accurate, helpful responses to your questions.',
  },
  {
    icon: <DescriptionIcon sx={{ color: 'text.secondary' }} />,
    title: 'Document Intelligence',
    description:
      'Upload and analyze your documents. The AI extracts insights and answers questions based on your specific content.',
  },
  {
    icon: <SearchIcon sx={{ color: 'text.secondary' }} />,
    title: 'Smart Search & Retrieval',
    description:
      'Find information instantly across all your uploaded documents with advanced semantic search capabilities.',
  },
  {
    icon: <ChatIcon sx={{ color: 'text.secondary' }} />,
    title: 'Interactive Q&A',
    description:
      'Get instant answers from your documents through natural conversations. Ask follow-up questions and dive deeper into topics.',
  },
];

export default function Content() {
  return (
    <Stack
      sx={{ flexDirection: 'column', alignSelf: 'center', gap: 4, maxWidth: 450 }}
    >
      <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center', gap: 2 }}>
        <img 
          src="/mascot.svg" 
          alt="QA Chatbot Mascot" 
          width={60}
          height={60}
          style={{
            display: 'block'
          }}
        />
        <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          QA Chatbot
        </Typography>
      </Box>
      {items.map((item, index) => (
        <Stack key={index} direction="row" sx={{ gap: 2 }}>
          {item.icon}
          <div>
            <Typography gutterBottom sx={{ fontWeight: 'medium' }}>
              {item.title}
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              {item.description}
            </Typography>
          </div>
        </Stack>
      ))}
    </Stack>
  );
}
