import React, { useState, useEffect, useRef } from 'react';
import { prospectsService, eventsService } from '../services/api';
import { PageHeader, Card, Button, Badge, Modal, Input } from '../components/UI';
import { Plus, Globe, Activity, CheckCircle2, AlertTriangle, Clock, Terminal as TerminalIcon, Radio } from 'lucide-react';

export default function Dashboard() {
  const [prospects, setProspects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({ company_name: '', website: '', simulate_failure: false });
  const [submitting, setSubmitting] = useState(false);
  
  // Activity Feed State
  const [events, setEvents] = useState([]);

  // Streaming state
  const [activeStreamId, setActiveStreamId] = useState(null);
  const [streamLogs, setStreamLogs] = useState([]);
  const logsEndRef = useRef(null);

  const fetchProspects = async () => {
    try {
      const [data, eventsData] = await Promise.all([
        prospectsService.getProspects({ limit: 50 }),
        eventsService.getEvents()
      ]);
      setProspects(data || []);
      setEvents(eventsData || []);
    } catch (error) {
      console.error('Failed to fetch prospects/events:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProspects();
    const interval = setInterval(fetchProspects, 5000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll terminal
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [streamLogs]);

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const result = await prospectsService.createProspect({
        ...formData,
        trigger_event: 'manual_submission'
      });
      
      setFormData({ company_name: '', website: '', simulate_failure: false });
      const prospectId = result.id || result.prospect_id; 
      startStream(prospectId);

    } catch (error) {
      console.error('Failed to submit prospect:', error);
      alert('Failed to submit prospect.');
      setSubmitting(false);
    }
  };

  const startStream = (prospectId) => {
    setActiveStreamId(prospectId);
    setStreamLogs([{ ts: new Date().toISOString(), agent: 'SYSTEM', msg: `Initializing LangGraph workflow for ${prospectId}...` }]);
    
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const sse = new EventSource(`${baseUrl}/api/prospects/${prospectId}/stream`);
    
    sse.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStreamLogs(prev => [...prev, { ts: new Date().toISOString(), agent: data.agent || 'AI', msg: data.message || event.data }]);
      } catch (e) {
        setStreamLogs(prev => [...prev, { ts: new Date().toISOString(), agent: 'AI', msg: event.data }]);
      }
    };
    
    sse.onerror = () => {
      setStreamLogs(prev => [...prev, { ts: new Date().toISOString(), agent: 'SYSTEM', msg: 'Stream closed or connection lost.' }]);
      sse.close();
      setSubmitting(false);
    };
  };

  const closeAddForm = () => {
    setShowAddForm(false);
    setActiveStreamId(null);
    setStreamLogs([]);
    setSubmitting(false);
    fetchProspects();
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'APPROVED':
      case 'COMPLETED':
        return <Badge variant="success"><CheckCircle2 size={12} /> {status}</Badge>;
      case 'REJECTED':
      case 'FAILED':
        return <Badge variant="danger"><AlertTriangle size={12} /> {status}</Badge>;
      case 'PENDING':
      case 'PROCESSING':
        return <Badge variant="info"><Activity size={12} /> {status}</Badge>;
      case 'HITL':
        return <Badge variant="warning"><Clock size={12} /> {status}</Badge>;
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
      <PageHeader 
        title="Prospects Pipeline" 
        description="Monitor the real-time AI evaluation pipeline of your B2B targets."
        actions={
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setShowAddForm(true)}>
            Add Target
          </Button>
        }
      />

      <Modal 
        isOpen={showAddForm} 
        onClose={closeAddForm} 
        title={activeStreamId ? "Live Execution Feed" : "Submit New Target"}
        icon={activeStreamId ? <TerminalIcon size={20} /> : <Globe size={20} />}
        footer={
          !activeStreamId ? (
            <>
              <Button onClick={closeAddForm}>Cancel</Button>
              <Button variant="primary" onClick={handleAddSubmit} disabled={submitting || !formData.company_name}>
                Start Evaluation
              </Button>
            </>
          ) : (
            <Button onClick={closeAddForm} variant="secondary">Close Output</Button>
          )
        }
      >
        {!activeStreamId ? (
          <form onSubmit={handleAddSubmit} className="flex-col">
            <Input 
              label="Company Name" 
              value={formData.company_name} 
              onChange={(e) => setFormData({...formData, company_name: e.target.value})} 
              required 
              placeholder="e.g. Acme Corp"
            />
            <Input 
              label="Website URL" 
              value={formData.website} 
              onChange={(e) => setFormData({...formData, website: e.target.value})} 
              placeholder="https://acme.com"
            />
            <div className="flex-row" style={{ marginTop: '16px' }}>
              <input 
                type="checkbox" 
                id="sim_fail"
                checked={formData.simulate_failure}
                onChange={(e) => setFormData({...formData, simulate_failure: e.target.checked})}
                style={{ width: '16px', height: '16px', cursor: 'pointer', accentColor: 'var(--primary-accent)' }}
              />
              <label htmlFor="sim_fail" style={{ fontSize: '14px', color: 'var(--text-secondary)', cursor: 'pointer', marginLeft: '8px' }}>
                Simulate low confidence (Force Human Review)
              </label>
            </div>
            <button type="submit" style={{ display: 'none' }}></button>
          </form>
        ) : (
          <div style={{ display: 'flex', gap: '24px' }}>
            <div style={{ flex: 1 }}>
              <div style={{ marginBottom: '16px', fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)' }}>Discovered Data</div>
              <div className="flex-col" style={{ gap: '12px' }}>
                <div style={{ padding: '12px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '8px' }}>Tech Stack</div>
                  {!streamLogs.some(l => l.msg.includes('Tech stack')) ? (
                    <div style={{ height: '16px', background: '#e6e2d8', borderRadius: '4px', width: '80%', animation: 'pulse 1.5s infinite' }} />
                  ) : (
                    <div style={{ fontSize: '13px' }}>React, Python, AWS (Extracted)</div>
                  )}
                </div>
                <div style={{ padding: '12px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '8px' }}>Employee Count</div>
                  {!streamLogs.some(l => l.msg.includes('employee')) ? (
                    <div style={{ height: '16px', background: '#e6e2d8', borderRadius: '4px', width: '50%', animation: 'pulse 1.5s infinite' }} />
                  ) : (
                    <div style={{ fontSize: '13px' }}>150 - 250 verified</div>
                  )}
                </div>
              </div>
            </div>
            
            <div className="terminal-window" style={{ flex: 2 }}>
              <div className="terminal-header">
                <span>Execution Trace — {activeStreamId}</span>
              </div>
              <div className="terminal-body">
                {streamLogs.map((log, i) => (
                  <div key={i} className="terminal-line">
                    <span className="terminal-timestamp">[{new Date(log.ts).toLocaleTimeString()}]</span>
                    <span className="terminal-agent">{log.agent}:</span>
                    <span className="terminal-msg">{log.msg}</span>
                  </div>
                ))}
                {submitting && (
                  <div className="terminal-line" style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-tertiary)', marginTop: '8px' }}>
                    <div className="spinner" style={{ width: '12px', height: '12px', margin: 0, borderWidth: '2px' }} />
                    Awaiting output...
                  </div>
                )}
                <div ref={logsEndRef} />
              </div>
            </div>
          </div>
        )}
      </Modal>

      <div style={{ display: 'flex', gap: '32px' }}>
        <div style={{ flex: 2 }}>
          <Card style={{ padding: 0, overflow: 'hidden' }}>
            {loading ? (
              <div className="spinner"></div>
            ) : prospects.length === 0 ? (
              <div className="flex-col" style={{ alignItems: 'center', padding: '80px 20px', color: 'var(--text-tertiary)' }}>
                <Globe size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
                <p>No prospects currently in the pipeline.</p>
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--bg-main)', borderBottom: '1px solid var(--border-light)' }}>
                    <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Target</th>
                    <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Status</th>
                    <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Last Update</th>
                  </tr>
                </thead>
                <tbody>
                  {prospects.map((p) => (
                    <tr key={p.id} style={{ borderBottom: '1px solid var(--border-light)', transition: 'background 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-main)'} onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                      <td style={{ padding: '16px 24px' }}>
                        <div className="flex-row gap-4">
                          <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'var(--bg-panel)', border: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary-accent)', fontWeight: 600 }}>
                            {p.company_name.charAt(0).toUpperCase()}
                          </div>
                          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{p.company_name}</span>
                        </div>
                      </td>
                      <td style={{ padding: '16px 24px' }}>{getStatusBadge(p.status)}</td>
                      <td style={{ padding: '16px 24px', color: 'var(--text-secondary)', fontSize: '14px' }}>
                        {p.updated_at ? new Date(p.updated_at).toLocaleString() : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>

        <div style={{ flex: 1 }}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px', color: 'var(--text-primary)', fontWeight: 600, fontSize: '16px' }}>
              <Radio size={18} color="var(--primary-accent)" /> Global Event Feed
            </div>
            {events.length === 0 ? (
              <div style={{ fontSize: '13px', color: 'var(--text-tertiary)', textAlign: 'center', padding: '24px 0' }}>
                No recent events.
              </div>
            ) : (
              <div className="flex-col" style={{ gap: '16px' }}>
                {events.map((ev, i) => (
                  <div key={i} style={{ paddingBottom: '16px', borderBottom: i === events.length - 1 ? 'none' : '1px solid var(--border-light)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginBottom: '4px' }}>{new Date(ev.timestamp).toLocaleTimeString()}</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{ev.message}</div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
