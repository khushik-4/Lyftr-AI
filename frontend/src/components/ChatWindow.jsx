import React, { useEffect, useRef } from 'react';
import { Sparkles, AlertCircle } from 'lucide-react';
import MessageBubble from './MessageBubble';

export default function ChatWindow({
  messages,
  loading,
  error,
  onSelectPrompt
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, error]);

  const suggestedPrompts = [
    "What is the capital of France?",
    "Explain how API key failover ensures high availability.",
    "Why does response caching improve latency and reduce LLM cost?"
  ];

  return (
    <main className="chat-window" aria-label="Conversation area">
      {messages.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <Sparkles size={22} />
          </div>
          <h2 className="empty-greeting">Hello! What would you like to explore today?</h2>
          <p className="empty-subtext">
            Start a conversation with persistent multi-turn memory, automatic key failover, and high-performance response caching.
          </p>

          <div className="suggested-prompts">
            {suggestedPrompts.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                className="suggested-btn"
                onClick={() => onSelectPrompt(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      ) : (
        messages.map((msg, index) => (
          <MessageBubble key={index} message={msg} />
        ))
      )}

      {/* Loading state indicator */}
      {loading && (
        <div className="message-row assistant">
          <div className="loading-indicator">
            <div className="dot-pulse">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span>Generating response...</span>
          </div>
        </div>
      )}

      {/* Error message banner */}
      {error && (
        <div className="error-banner" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div ref={bottomRef} />
    </main>
  );
}
