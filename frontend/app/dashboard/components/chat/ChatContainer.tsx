'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import WelcomeScreen from './WelcomeScreen';
import { createClient } from '@utils/supabase/client';

export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

export default function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [currentAssistantMessage, setCurrentAssistantMessage] = useState<string>('');
  const [wsConnected, setWsConnected] = useState(false);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const supabase = createClient();

  useEffect(() => {
    const getUser = async () => {
      const { data: { user }, error } = await supabase.auth.getUser();
      if (error || !user) {
        console.error('Error acquiring user info:', error);
        return;
      }
      setUserId(user.id);
    };
    getUser();
  }, [supabase]);

  const connectWebSocket = useCallback(() => {
    if (!userId || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Determine WebSocket URL based on environment
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NODE_ENV === 'production' 
      ? window.location.host 
      : 'localhost:8000';
    const wsUrl = `${protocol}//${host}/api/v1/chat/ws?user_id=${userId}`;
    
    console.log('Connecting to WebSocket:', wsUrl);
    console.log('Current location:', window.location.href);

    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('WebSocket connected');
      setWsConnected(true);
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message received:', data);

      switch (data.type) {
        case 'message_received':
          console.log('Message received by server');
          break;

        case 'stream':
          setCurrentAssistantMessage(prev => prev + data.content);
          break;

        case 'complete':
          const assistantMessage: Message = {
            id: Date.now().toString(),
            content: currentAssistantMessage + data.content,
            role: 'assistant',
            timestamp: new Date(),
          };
          setMessages(prev => [...prev, assistantMessage]);
          setCurrentAssistantMessage('');
          setIsLoading(false);
          break;

        case 'error':
          console.error('WebSocket error:', data.message);
          setIsLoading(false);
          break;

        case 'ping':
          console.log('Ping received, sending pong');
          wsRef.current?.send(JSON.stringify({ type: 'pong' }));
          break;

        case 'idle_timeout':
          console.log('Connection timed out due to inactivity');
          break;

        default:
          console.log('Unknown message type:', data.type);
      }
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      console.error('WebSocket readyState:', wsRef.current?.readyState);
      setWsConnected(false);
      setIsLoading(false);
    };

    wsRef.current.onclose = (event) => {
      console.log('WebSocket closed:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
        url: wsUrl
      });
      setWsConnected(false);
      setCurrentAssistantMessage('');
      setIsLoading(false);
      
      // Retry connection after 3 seconds if it wasn't a clean close
      if (!event.wasClean && event.code !== 1000) {
        console.log('Attempting to reconnect in 3 seconds...');
        setTimeout(() => {
          if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
            connectWebSocket();
          }
        }, 3000);
      }
    };
  }, [userId, currentAssistantMessage]);

  useEffect(() => {
    if (userId) {
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [userId, connectWebSocket]);

  useEffect(() => {
    const timer = setTimeout(() => {
      chatInputRef.current?.focus();
    }, 100);
    return () => clearTimeout(timer);
  }, []);

  const handleSendMessage = async (content: string) => {
    if (!userId || !wsConnected || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setCurrentAssistantMessage('');

    const messageData = { message: content };
    wsRef.current.send(JSON.stringify(messageData));

    setTimeout(() => {
      chatInputRef.current?.focus();
    }, 100);
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
          <MessageList
            messages={messages}
            isLoading={isLoading}
            currentAssistantMessage={currentAssistantMessage}
          />
        )}
        <Box sx={{ p: 2, borderTop: '1px solid', borderColor: 'divider' }}>
          <ChatInput ref={chatInputRef} onSendMessage={handleSendMessage} disabled={isLoading} />
        </Box>
      </Stack>
    </Paper>
  );
}