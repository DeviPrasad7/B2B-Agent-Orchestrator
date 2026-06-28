import React from 'react';
import { Activity, Search, Database, Zap, UserCheck, CheckCircle, XCircle } from 'lucide-react';

export default function WorkflowGraph({ stateLogs, currentState }) {
  // Extract executed agents and status from the currentState
  const executedAgents = currentState?.executed_agents || [];
  const status = currentState?.overall_status || 'PENDING';
  
  // Determine active node based on the latest executed agent or overall status
  let activeNode = 'init';
  if (status === 'HITL_REQUIRED') activeNode = 'hitl';
  else if (status === 'APPROVED' || status === 'REJECTED') activeNode = 'output';
  else if (executedAgents.includes('score_node') || executedAgents.includes('cross_validator_node') || executedAgents.includes('persona_matcher_node')) activeNode = 'evaluator';
  else if (executedAgents.includes('enricher_node') || executedAgents.includes('contact_finder_node')) activeNode = 'enricher';
  else if (executedAgents.includes('researcher_node') || executedAgents.includes('tech_stack_detector_node')) activeNode = 'scraper';
  
  const nodes = [
    { id: 'init', label: 'Initialization', icon: <Activity size={18} /> },
    { id: 'scraper', label: 'Scraping', icon: <Search size={18} /> },
    { id: 'enricher', label: 'Enriching', icon: <Database size={18} /> },
    { id: 'evaluator', label: 'Evaluating', icon: <Zap size={18} /> },
    { id: 'hitl', label: 'HITL Review', icon: <UserCheck size={18} /> },
    { id: 'output', label: 'Output', icon: status === 'REJECTED' ? <XCircle size={18} /> : <CheckCircle size={18} /> }
  ];

  const getStatusColor = (nodeId) => {
    if (activeNode === nodeId) {
      if (nodeId === 'hitl') return 'var(--warning)';
      if (nodeId === 'output') return status === 'REJECTED' ? 'var(--danger)' : 'var(--success)';
      return 'var(--primary-accent)';
    }
    const idx = nodes.findIndex(n => n.id === nodeId);
    const activeIdx = nodes.findIndex(n => n.id === activeNode);
    return idx < activeIdx ? 'var(--success)' : 'var(--border-light)';
  };

  const getStatusBg = (nodeId) => {
    if (activeNode === nodeId) {
      if (nodeId === 'hitl') return '#fdfaf6';
      if (nodeId === 'output') return status === 'REJECTED' ? '#fff5f5' : '#f0fdf4';
      return 'rgba(218, 119, 86, 0.1)';
    }
    const idx = nodes.findIndex(n => n.id === nodeId);
    const activeIdx = nodes.findIndex(n => n.id === activeNode);
    return idx < activeIdx ? '#f0fdf4' : 'var(--bg-main)';
  };

  const getStatusStyle = (nodeId) => {
    const isActive = activeNode === nodeId;
    return {
      borderColor: getStatusColor(nodeId),
      backgroundColor: getStatusBg(nodeId),
      color: isActive || nodes.findIndex(n => n.id === nodeId) <= nodes.findIndex(n => n.id === activeNode) 
        ? getStatusColor(nodeId) 
        : 'var(--text-tertiary)',
      transform: isActive ? 'scale(1.05)' : 'scale(1)',
      boxShadow: isActive ? `0 0 15px ${getStatusColor(nodeId)}40` : 'none',
      transition: 'all 0.3s ease'
    };
  };

  // Get the most recent logs to show as "thinking"
  const recentLogs = stateLogs.slice(-3).reverse();

  return (
    <div style={{ padding: '24px', background: 'var(--bg-surface)', borderRadius: '8px', border: '1px solid var(--border-light)' }}>
      <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '24px' }}>Agent Thinking Process</h3>
      
      {/* Workflow Graph visualization */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '32px', position: 'relative' }}>
        {/* Connecting line background */}
        <div style={{ position: 'absolute', top: '50%', left: '40px', right: '40px', height: '2px', background: 'var(--border-light)', zIndex: 0, transform: 'translateY(-50%)' }} />
        
        {nodes.map((node, i) => {
          const isActive = activeNode === node.id;
          return (
            <div key={node.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', zIndex: 1, position: 'relative' }}>
              <div 
                style={{ 
                  width: '40px', 
                  height: '40px', 
                  borderRadius: '50%', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  border: '2px solid',
                  ...getStatusStyle(node.id)
                }}
                className={isActive ? 'pulse-animation' : ''}
              >
                {node.icon}
              </div>
              <div style={{ 
                marginTop: '8px', 
                fontSize: '11px', 
                fontWeight: isActive ? 600 : 400,
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)'
              }}>
                {node.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Live Thinking Logs */}
      <div style={{ background: '#1e1e1e', borderRadius: '6px', padding: '16px', fontFamily: 'monospace', fontSize: '12px', minHeight: '120px' }}>
        <div style={{ color: '#888', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
          <span>Live Execution Logs</span>
          {activeNode !== 'output' && activeNode !== 'hitl' && (
            <span style={{ color: 'var(--primary-accent)' }} className="blink-text">Processing...</span>
          )}
        </div>
        {recentLogs.map((log, idx) => {
          // If it's a state_update, maybe show something specific
          let displayMsg = log.type;
          if (log.type === 'state_update') {
            displayMsg = `Agent state updated: ${log.payload?.last_agent || log.payload?.current_trigger_event || 'evaluating'}...`;
          } else if (log.type === 'tool_call') {
            displayMsg = `Executing tool: ${log.payload?.tool_name}`;
          }
          
          return (
            <div key={idx} style={{ 
              color: idx === 0 ? '#4ade80' : '#888',
              marginBottom: '4px',
              opacity: 1 - (idx * 0.3)
            }}>
              <span style={{ color: '#555' }}>[{new Date(log.timestamp || Date.now()).toLocaleTimeString()}]</span> {displayMsg}
            </div>
          );
        })}
        {recentLogs.length === 0 && (
          <div style={{ color: '#555', fontStyle: 'italic' }}>Waiting for agent execution...</div>
        )}
      </div>

      <style>{`
        .pulse-animation {
          animation: pulse-glow 2s infinite;
        }
        @keyframes pulse-glow {
          0% { box-shadow: 0 0 0 0 rgba(218, 119, 86, 0.4); }
          70% { box-shadow: 0 0 0 10px rgba(218, 119, 86, 0); }
          100% { box-shadow: 0 0 0 0 rgba(218, 119, 86, 0); }
        }
        .blink-text {
          animation: blink 1.5s infinite;
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
