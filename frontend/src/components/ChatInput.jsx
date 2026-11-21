import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';

export default function ChatInput({ onSendMessage, disabled }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [text]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;

    onSendMessage(trimmed);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="chat-composer">
      <form onSubmit={handleSubmit} className="composer-wrapper">
        <textarea
          ref={textareaRef}
          data-testid="chat-input"
          className="composer-textarea"
          placeholder="Ask a question or explore a concept..."
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />
        <button
          type="submit"
          data-testid="send-button"
          className="btn-send"
          disabled={disabled || !text.trim()}
          title="Send message (Enter)"
        >
          <ArrowUp size={18} />
        </button>
      </form>
      <div className="composer-hints">
        <span>Enter to send, Shift + Enter for new line</span>
        <span>Up to 4,000 characters</span>
      </div>
    </div>
  );
}

