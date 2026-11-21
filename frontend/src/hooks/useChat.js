import { useState, useEffect, useCallback, useRef } from 'react';
import { sendChatMessage, checkHealth } from '../services/api';

export function useChat() {
  // Generate a persistent session ID on load
  const [sessionId, setSessionId] = useState(() => {
    return 's-' + Math.random().toString(36).substring(2, 10);
  });

  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backendConnected, setBackendConnected] = useState(true);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [simulateFailure, setSimulateFailure] = useState('');

  const activeSimulationRef = useRef('');
  activeSimulationRef.current = simulateFailure;

  // Poll backend health on mount and periodically
  const verifyHealth = useCallback(async () => {
    try {
      await checkHealth();
      setBackendConnected(true);
    } catch {
      setBackendConnected(false);
    }
  }, []);

  useEffect(() => {
    verifyHealth();
    const interval = setInterval(verifyHealth, 15000);
    return () => clearInterval(interval);
  }, [verifyHealth]);

  // Start a fresh session
  const startNewChat = useCallback(() => {
    const newId = 's-' + Math.random().toString(36).substring(2, 10);
    setSessionId(newId);
    setMessages([]);
    setError(null);
    setSimulateFailure('');
  }, []);

  // Send message
  const sendMessage = useCallback(async (text) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setError(null);
    setLoading(true);

    const simulationToSend = activeSimulationRef.current;
    // Always reset simulation to normal operation after scheduling the request
    setSimulateFailure('');

    // Optimistically record user message
    const userMessageObj = {
      role: 'user',
      content: trimmed
    };

    setMessages((prev) => [...prev, userMessageObj]);

    try {
      const response = await sendChatMessage({
        sessionId,
        message: trimmed,
        systemPrompt: systemPrompt.trim() || undefined,
        simulateFailureHeader: simulationToSend || undefined
      });

      const assistantMessageObj = {
        role: 'assistant',
        content: response.reply,
        metadata: response.metadata
      };

      setMessages((prev) => [...prev, assistantMessageObj]);
      setBackendConnected(true);
    } catch (err) {
      // If error occurs, we keep the user message visible or show error message
      setError(err.message || 'An error occurred while sending the message.');
      if (err.status !== 422 && err.status !== 503) {
        setBackendConnected(false);
      }
    } finally {
      setLoading(false);
    }
  }, [sessionId, systemPrompt, loading]);

  return {
    sessionId,
    messages,
    loading,
    error,
    backendConnected,
    systemPrompt,
    setSystemPrompt,
    simulateFailure,
    setSimulateFailure,
    sendMessage,
    startNewChat
  };
}

