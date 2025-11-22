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
  const [hasActiveStream, setHasActiveStream] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string>('');
  const [currentAssistantMessage, setCurrentAssistantMessage] = useState<string>('');
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const processedMessageIds = useRef<Set<string>>(new Set());
  const currentMessageId = useRef<string | null>(null);

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

    // Generate unique session ID for this chat session
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSessionId);
    console.log('Generated session ID:', newSessionId);
  }, [supabase]);


  useEffect(() => {
    if (!userId) return;

    console.log('Setting up socket manager for userId:', userId);

    const handleMessage = (data: any) => {
      switch (data.type) {
        case 'message_received':
          console.log('Message received by server');
          break;

        case 'stream_start':
          console.log('Stream starting with message ID:', data.message_id);
          currentMessageId.current = data.message_id;
          setCurrentAssistantMessage('');
          setHasActiveStream(true);
          break;

        case 'stream':
          console.log('Stream chunk received:', {
            messageId: data.message_id,
            currentMessageId: currentMessageId.current,
            content: data.content?.slice(0, 50)
          });
          if (data.message_id === currentMessageId.current) {
            setCurrentAssistantMessage(prev => {
              const newContent = prev + data.content;
              console.log('Updated current message:', newContent.slice(0, 100) + '...');
              return newContent;
            });
          }
          break;

        case 'complete':
          if (data.message_id && data.message_id === currentMessageId.current) {
            setCurrentAssistantMessage(current => {
              console.log('Complete received:', {
                messageId: data.message_id,
                currentMessageId: currentMessageId.current,
                currentContent: current.slice(0, 100) + '...'
              });

              if (current.trim()) {
                console.log('Creating assistant message with backend ID:', data.message_id);

                if (processedMessageIds.current.has(data.message_id)) {
                  console.log('Duplicate message ID detected, skipping:', data.message_id);
                  return '';
                }

                const assistantMessage: Message = {
                  id: data.message_id,
                  content: current,
                  role: 'assistant',
                  timestamp: new Date(),
                };

                processedMessageIds.current.add(data.message_id);
                setMessages(prev => [...prev, assistantMessage]);
              }
              return '';
            });
          }
          setIsLoading(false);
          setHasActiveStream(false);
          currentMessageId.current = null;
          break;

        case 'generation_stopped':
          if (data.message_id && data.message_id === currentMessageId.current) {
            setCurrentAssistantMessage(current => {
              if (current.trim()) {
                if (processedMessageIds.current.has(data.message_id)) {
                  return '';
                }

                const assistantMessage: Message = {
                  id: data.message_id,
                  content: current,
                  role: 'assistant',
                  timestamp: new Date(),
                };

                processedMessageIds.current.add(data.message_id);
                setMessages(prev => [...prev, assistantMessage]);
              }
              return '';
            });
          }
          setIsLoading(false);
          setHasActiveStream(false);
          currentMessageId.current = null;
          break;

        case 'stop_ack':
          console.log('Stop acknowledged for', data.message_id);
          break;

        case 'error':
          console.error('WebSocket error:', data.message);
          setError(data.message);
          setIsLoading(false);
          setHasActiveStream(false);
          break;


        case 'idle_timeout':
          console.log('Connection timed out due to inactivity');
          setError('Connection timed out due to inactivity');
          setWsConnected(false);
          setIsLoading(false);
          setHasActiveStream(false);
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
      currentMessageId.current = null;
      setIsLoading(false);
      setHasActiveStream(false);
    };

    const handleError = (error: any) => {
      console.error('Socket manager error:', error);
      setWsConnected(false);
      setIsLoading(false);
      setError(typeof error === 'string' ? error : 'Connection error');
      setHasActiveStream(false);
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
      setHasActiveStream(false);
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
    currentMessageId.current = null;
    setError(null);

    const messageData = {
      message: content,
      session_id: sessionId
    };
    socketManager.send(messageData);
  };

  const handleStopGeneration = () => {
    if (!socketManager.isConnected() || !currentMessageId.current) {
      return;
    }

    socketManager.send({
      type: 'stop',
      message_id: currentMessageId.current,
    });
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
          <ChatInput
            ref={chatInputRef}
            onSendMessage={handleSendMessage}
            disabled={isLoading}
            isLoading={hasActiveStream}
            canStop={hasActiveStream}
            onStopGeneration={handleStopGeneration}
          />
        </Box>
      </Stack>
    </Paper>
  );
}
