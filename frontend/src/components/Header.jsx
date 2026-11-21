import React from 'react';
import { PlusCircle, Wifi, WifiOff } from 'lucide-react';

export default function Header({ backendConnected, onNewChat }) {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-title-row">
          <span className="brand-name">Lyftr AI</span>
          <span
            className={`status-badge ${backendConnected ? 'connected' : 'disconnected'}`}
            title={backendConnected ? 'Backend Connected' : 'Backend Disconnected'}
          >
            <span className="status-dot"></span>
            {backendConnected ? 'Online' : 'Offline'}
          </span>
        </div>
        <p className="brand-subtitle">Intelligent conversations, built for reliability.</p>
      </div>

      <div className="header-actions">
        <button
          className="btn-new-chat"
          onClick={onNewChat}
          title="Start a new session"
          type="button"
        >
          <PlusCircle size={15} />
          <span>New Chat</span>
        </button>
      </div>
    </header>
  );
}
