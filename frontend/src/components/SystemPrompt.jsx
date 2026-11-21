import React from 'react';

export default function SystemPrompt({ isOpen, systemPrompt, onSystemPromptChange }) {
  if (!isOpen) return null;

  return (
    <div className="panel-content">
      <textarea
        data-testid="system-prompt-input"
        className="system-prompt-textarea"
        placeholder="Enter custom instructions for this session (e.g. You are a concise technical tutor)..."
        value={systemPrompt}
        onChange={(e) => onSystemPromptChange(e.target.value)}
      />
      <div className="system-prompt-hint">
        Overrides the assistant's default persona for this session. Not stored as a chat message.
      </div>
    </div>
  );
}

