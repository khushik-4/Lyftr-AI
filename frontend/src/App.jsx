import React, { useState } from 'react';
import { useChat } from './hooks/useChat';
import Header from './components/Header';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import SystemPrompt from './components/SystemPrompt';
import ReliabilityTest from './components/ReliabilityTest';
import { SlidersHorizontal, ShieldCheck, ChevronDown, ChevronUp } from 'lucide-react';
import './styles/global.css';
import './styles/components.css';

export default function App() {
  const {
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
  } = useChat();

  const [showSystemPrompt, setShowSystemPrompt] = useState(false);
  const [showReliability, setShowReliability] = useState(false);

  return (
    <div className="app-container">
      {/* Top Header */}
      <Header
        backendConnected={backendConnected}
        onNewChat={startNewChat}
      />

      {/* Collapsible Utility Panels */}
      <div className="controls-bar">
        <div className="controls-toggles">
          <button
            type="button"
            className={`control-toggle-btn ${showSystemPrompt ? 'active' : ''}`}
            onClick={() => {
              setShowSystemPrompt(!showSystemPrompt);
              if (showReliability) setShowReliability(false);
            }}
          >
            <SlidersHorizontal size={13} />
            <span>System Persona</span>
            {showSystemPrompt ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>

          <button
            type="button"
            className={`control-toggle-btn ${showReliability || simulateFailure ? 'active' : ''}`}
            onClick={() => {
              setShowReliability(!showReliability);
              if (showSystemPrompt) setShowSystemPrompt(false);
            }}
          >
            <ShieldCheck size={13} />
            <span>Reliability Test</span>
            {simulateFailure ? (
              <span className="simulation-active-badge">Active</span>
            ) : showReliability ? (
              <ChevronUp size={12} />
            ) : (
              <ChevronDown size={12} />
            )}
          </button>
        </div>

        {/* System Prompt Collapsible Panel */}
        <SystemPrompt
          isOpen={showSystemPrompt}
          systemPrompt={systemPrompt}
          onSystemPromptChange={setSystemPrompt}
        />

        {/* Reliability Test Collapsible Panel */}
        <ReliabilityTest
          isOpen={showReliability}
          simulateFailure={simulateFailure}
          onSimulationChange={setSimulateFailure}
        />
      </div>

      {/* Main Conversation Area */}
      <ChatWindow
        messages={messages}
        loading={loading}
        error={error}
        onSelectPrompt={sendMessage}
      />

      {/* Bottom Message Composer */}
      <ChatInput
        onSendMessage={sendMessage}
        disabled={loading}
      />
    </div>
  );
}
