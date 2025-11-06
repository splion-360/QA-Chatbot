'use client';

import { useState, useRef, useEffect } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import WelcomeScreen from './WelcomeScreen';
import { createClient } from '@utils/supabase/client';
import React from "react";
import { socketManager } from './Socket';




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
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const chatInputRef = useRef<HTMLInputElement>(null);
  // const processingComplete = useRef(false);
  const processedMessageHashes = useRef<Set<string>>(new Set());

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


  useEffect(() => {
    if (!userId) return;

    console.log('Setting up socket manager for userId:', userId);

    const handleMessage = (data: any) => {
      switch (data.type) {
        case 'message_received':
          console.log('Message received by server');
          break;

        case 'stream':
          setCurrentAssistantMessage(prev => prev + data.content);
          break;

        case 'complete':
          setCurrentAssistantMessage(current => {
            if (current.trim()) {
              console.log('Creating assistant message with content:', current);
              const assistantMessage: Message = {
                id: `assistant-${Date.now()}-${Math.random().toString(36)}`,
                content: current,
                role: 'assistant',
                timestamp: new Date(),
              };
              console.log('Assistant message created with ID:', assistantMessage.id);

              setMessages(prev => {
                const messageHash = btoa(assistantMessage.content).slice(0, 16);

                if (processedMessageHashes.current.has(messageHash)) {
                  console.log('Duplicate message hash detected, skipping:', messageHash);
                  return prev;
                }


                processedMessageHashes.current.add(messageHash);
                return [...prev, assistantMessage];
              });
            }
            setIsLoading(false);
            console.log('Resetting processingComplete flag to false');
            return '';
          });
          break;

        case 'error':
          console.error('WebSocket error:', data.message);
          setError(data.message);
          setIsLoading(false);
          break;

        case 'ping':
          console.log('Ping received, sending pong');
          socketManager.send({ type: 'pong' });
          break;

        case 'idle_timeout':
          console.log('Connection timed out due to inactivity');
          setError('Connection timed out due to inactivity');
          setWsConnected(false);
          setIsLoading(false);
          break;

        default:
          console.log('Unknown message type:', data.type);
      }
    };

    const handleOpen = () => {
      console.log('Socket manager connected');
      setWsConnected(true);
    };

    const handleClose = () => {
      console.log('Socket manager disconnected');
      setWsConnected(false);
      setCurrentAssistantMessage('');
      setIsLoading(false);
    };

    const handleError = (error: any) => {
      console.error('Socket manager error:', error);
      setWsConnected(false);
      setIsLoading(false);
      setError(typeof error === 'string' ? error : 'Connection error');
    };

    const unsubscribeMessage = socketManager.onMessage(handleMessage);
    const unsubscribeOpen = socketManager.onOpen(handleOpen);
    const unsubscribeClose = socketManager.onClose(handleClose);
    const unsubscribeError = socketManager.onError(handleError);

    socketManager.connect(userId);

    return () => {
      unsubscribeMessage();
      unsubscribeOpen();
      unsubscribeClose();
      unsubscribeError();
    };
  }, [userId]);

  useEffect(() => {
    return () => {
      console.log('Component unmounting, cleaning up socket manager');
      socketManager.disconnect();
    };
  }, []);

  const sendMessage = (content: string) => {
    if (!userId || !socketManager.isConnected()) {
      console.error('WebSocket not connected');
      setError('Not connected to server');
      return;
    }

    const userMessage: Message = {
      id: `user-${Date.now()}-${Math.random().toString(36)}`,
      content,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setCurrentAssistantMessage('');
    setError(null);

    const messageData = { message: content };
    socketManager.send(messageData);
  };





  const handleSendMessage = (content: string) => {
    sendMessage(content);
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