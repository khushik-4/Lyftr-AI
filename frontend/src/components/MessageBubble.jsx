import React from 'react';
import MessageMetadata from './MessageMetadata';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="message-row user">
        <div className="message-bubble">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="message-row assistant">
      <div data-testid="assistant-message" className="message-bubble">
        <div className="assistant-text">{message.content}</div>
        <MessageMetadata metadata={message.metadata} />
      </div>
    </div>
  );
}
