'use client';

import { useRef, useEffect } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Message from './Message';
import TypingIndicator from './TypingIndicator';
import { Message as MessageType } from './ChatContainer';

interface MessageListProps {
  messages: MessageType[];
  isLoading: boolean;
  currentAssistantMessage?: string;
}

export default function MessageList({ messages, isLoading, currentAssistantMessage }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, currentAssistantMessage]);

  return (
    <Box
      sx={{
        flexGrow: 1,
        overflow: 'auto',
        p: 2,
        maxHeight: 'calc(100vh - 200px)',
      }}
    >
      <Stack spacing={2}>
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        {currentAssistantMessage && (
          <Message 
            key="streaming" 
            message={{
              id: 'streaming',
              content: currentAssistantMessage,
              role: 'assistant',
              timestamp: new Date()
            }} 
          />
        )}
        {isLoading && !currentAssistantMessage && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </Stack>
    </Box>
  );
}