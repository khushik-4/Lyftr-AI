import React from 'react';
import { Zap, Database, Clock, ArrowDownLeft, ArrowUpRight, ShieldAlert } from 'lucide-react';

export default function MessageMetadata({ metadata }) {
  if (!metadata) return null;

  const isCache = metadata.resolution_source === 'LLM_CACHE';

  return (
    <div className="assistant-metadata">
      {/* Resolution source: LIVE_INFERENCE or LLM_CACHE */}
      <span
        data-testid="meta-source"
        className={`meta-pill ${isCache ? 'source-cache' : 'source-live'}`}
      >
        {isCache ? <Database size={11} /> : <Zap size={11} />}
        {metadata.resolution_source}
      </span>

      {/* Model name */}
      <span className="meta-item">
        <span className="meta-label">Model:</span>
        <span data-testid="meta-model" className="meta-value">
          {metadata.model}
        </span>
      </span>

      {/* Latency */}
      <span className="meta-item">
        <Clock size={11} className="meta-label" />
        <span data-testid="meta-latency" className="meta-value">
          {metadata.latency_ms} ms
        </span>
      </span>

      {/* Input tokens */}
      <span className="meta-item" title="Input Prompt Tokens">
        <ArrowDownLeft size={11} className="meta-label" />
        <span className="meta-label">In:</span>
        <span data-testid="meta-input-tokens" className="meta-value">
          {metadata.input_tokens}
        </span>
      </span>

      {/* Output tokens */}
      <span className="meta-item" title="Output Completion Tokens">
        <ArrowUpRight size={11} className="meta-label" />
        <span className="meta-label">Out:</span>
        <span data-testid="meta-output-tokens" className="meta-value">
          {metadata.output_tokens}
        </span>
      </span>

      {/* Key ID if available (only on live inference) */}
      {metadata.key_id && (
        <span className="meta-item" title="API Key Identifier">
          <span className="meta-label">Key:</span>
          <span className="meta-value">{metadata.key_id}</span>
        </span>
      )}

      {/* Fallback attempts if any */}
      {metadata.fallback_attempts > 0 && (
        <span className="meta-item" title="Fallback Retries Before Success">
          <ShieldAlert size={11} color="#C05746" />
          <span className="meta-label">Fallbacks:</span>
          <span className="meta-value" style={{ color: 'var(--danger)' }}>
            {metadata.fallback_attempts}
          </span>
        </span>
      )}
    </div>
  );
}

