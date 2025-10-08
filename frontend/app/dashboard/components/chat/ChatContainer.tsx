'use client';

import { useState, useRef, useEffect } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import WelcomeScreen from './WelcomeScreen';

export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

export default function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const chatInputRef = useRef<HTMLInputElement>(null);

  // Auto-focus input when component mounts or when switching to chat tab
  useEffect(() => {
    const timer = setTimeout(() => {
      chatInputRef.current?.focus();
    }, 100);
    return () => clearTimeout(timer);
  }, []);

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Focus back to input after sending message
    setTimeout(() => {
      chatInputRef.current?.focus();
    }, 100);

    // Simulate AI response (replace with actual API call later)
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "I'm a demo response. This would be replaced with actual AI response.",
        role: 'assistant',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
      setIsLoading(false);
      
      // Focus input again after AI response
      setTimeout(() => {
        chatInputRef.current?.focus();
      }, 100);
    }, 1000);
  };

  return (
    <Paper
      elevation={0}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'background.default',
      }}
    >
      <Stack sx={{ flexGrow: 1, height: '100%' }}>
        {messages.length === 0 ? (
          <WelcomeScreen onSendMessage={handleSendMessage} />
        ) : (
          <MessageList messages={messages} isLoading={isLoading} />
        )}
        <Box sx={{ p: 2, borderTop: '1px solid', borderColor: 'divider' }}>
          <ChatInput ref={chatInputRef} onSendMessage={handleSendMessage} disabled={isLoading} />
        </Box>
      </Stack>
    </Paper>
  );
}