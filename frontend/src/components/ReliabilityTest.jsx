import React from 'react';

export default function ReliabilityTest({
  isOpen,
  simulateFailure,
  onSimulationChange
}) {
  if (!isOpen) return null;

  return (
    <div className="panel-content reliability-panel">
      <div className="reliability-header">
        <label htmlFor="simulation-select" style={{ fontWeight: 600, fontSize: '0.8rem' }}>
          Simulated Failure Condition:
        </label>
        {simulateFailure && (
          <span className="simulation-active-badge">Active for next message</span>
        )}
      </div>

      <select
        id="simulation-select"
        className="reliability-select"
        value={simulateFailure}
        onChange={(e) => onSimulationChange(e.target.value)}
      >
        <option value="">No simulated failure</option>
        <option value="key_1=429">key_1 returns 429 (Rate Limit Failover)</option>
        <option value="key_1=500">key_1 returns 500 (Internal Error Failover)</option>
        <option value="*=429">All keys return 429 (503 Service Unavailable)</option>
      </select>

      <p className="reliability-desc">
        Injects the <code>X-Simulate-Failure</code> header into the next chat request only.
        This forces LiteLLM to simulate provider failure and demonstrate automatic key failover without burning live rate limits.
      </p>
    </div>
  );
}
