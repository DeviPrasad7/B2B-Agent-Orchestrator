import React, { useEffect, useState, useRef } from 'react';
import { X, Terminal as TerminalIcon, Activity, Play, Square, Cpu } from 'lucide-react';
import { agentService } from '../services/api';

export default function AgentLogsPanel({ agent, onClose }) {
  const [logs, setLogs] = useState([]);
  const [isActive, setIsActive] = useState(true);
  const logsEndRef = useRef(null);

  useEffect(() => {
    if (!agent) return;
    
    // Clear previous logs
    setLogs([]);
    setIsActive(true);
    
    const streamUrl = agentService.getAgentStreamUrl(agent.id);
    const eventSource = new EventSource(streamUrl);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLogs(prev => [...prev, data]);
      } catch (e) {
        console.error("Failed to parse log event", e);
      }
    };

    eventSource.onerror = (error) => {
      console.error("Agent Log SSE error:", error);
      setIsActive(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [agent]);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  if (!agent) return null;

  return (
    <div style={panelStyles.container} className="slideInRight">
      <div style={panelStyles.header}>
        <div className="flex-col">
          <h2 style={{ fontSize: '20px', margin: 0, color: 'var(--primary-accent)', display: 'flex', alignItems: 'center', gap: '8px', fontFamily: '"Fira Code", monospace' }}>
            <TerminalIcon size={20} /> 
            {agent.name}
          </h2>
          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={14}/> ID: {agent.id}
          </div>
        </div>
        <button onClick={onClose} style={panelStyles.closeBtn}><X size={20} /></button>
      </div>

      <div style={panelStyles.statusStrip}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
           <div className={isActive ? "status-dot pulsing" : "status-dot"} style={{ background: isActive ? 'var(--success)' : 'var(--danger)', width: '8px', height: '8px', borderRadius: '50%' }}></div>
           <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.05em' }}>
             {isActive ? 'Live Stream Active' : 'Stream Disconnected'}
           </span>
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
          {agent.tools?.length || 0} Tools Loaded
        </div>
      </div>
      
      <div style={panelStyles.terminal}>
        <div style={{ fontSize: '12px', color: '#666', marginBottom: '16px' }}>
          Welcome to the Advanced Agentic AI Console.
          <br/>Establishing secure tunnel to {agent.name}... Connected.
        </div>
        
        {logs.length === 0 && isActive && (
           <div style={{ color: 'var(--primary-accent)', animation: 'pulse 1.5s infinite' }}>
             Awaiting telemetry data...
           </div>
        )}

        <div className="flex-col" style={{ gap: '6px' }}>
          {logs.map((log, idx) => {
             const timeStr = new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
             let levelColor = '#888';
             if (log.level === 'INFO') levelColor = 'var(--primary-accent)';
             if (log.level === 'DEBUG') levelColor = 'var(--success)';
             if (log.level === 'WARN') levelColor = 'var(--warning)';
             if (log.level === 'ERROR') levelColor = 'var(--danger)';

             return (
               <div key={idx} style={{ display: 'flex', gap: '12px', fontFamily: '"Fira Code", monospace', fontSize: '13px', lineHeight: 1.4 }}>
                 <span style={{ color: '#555', flexShrink: 0 }}>[{timeStr}]</span>
                 <span style={{ color: levelColor, width: '45px', flexShrink: 0 }}>{log.level}</span>
                 <span style={{ color: '#d4d4d4', wordBreak: 'break-word' }}>{log.message}</span>
               </div>
             );
          })}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}

const panelStyles = {
  container: {
    position: 'fixed',
    top: 0,
    right: 0,
    bottom: 0,
    width: '900px',
    maxWidth: '100%',
    background: '#121212', // Dark mode for terminal
    borderLeft: '1px solid #333',
    boxShadow: '-8px 0 40px rgba(0,0,0,0.5)',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 1050,
  },
  header: {
    padding: '24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    background: '#1a1a1a',
    borderBottom: '1px solid #333'
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    color: '#888',
    padding: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '4px',
    transition: 'color 0.2s'
  },
  statusStrip: {
    padding: '12px 24px',
    background: '#1e1e1e',
    borderBottom: '1px solid #333',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  terminal: {
    flex: 1,
    padding: '24px',
    overflowY: 'auto',
    background: '#0a0a0a',
    color: '#d4d4d4',
  }
};
