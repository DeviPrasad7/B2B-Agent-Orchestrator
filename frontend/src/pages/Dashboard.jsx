import React, { useState, useEffect, useRef } from 'react';
import { prospectsService, agentService } from '../services/api';
import { PageHeader, Card, Button, Badge, Modal, Input } from '../components/UI';
import { LayoutDashboard, UserCheck, Settings, Activity, Bot, Database, Globe, Search, Plus, Terminal as TerminalIcon, Cpu, Layers, Archive, CheckCircle2, AlertTriangle, Clock, Radio, Shield, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import LiveGraph from '../components/LiveGraph';
import ProspectDetailPanel from '../components/ProspectDetailPanel';
import AgentLogsPanel from '../components/AgentLogsPanel';

export default function Dashboard() {
  const navigate = useNavigate();
  const [prospects, setProspects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({ company_name: '', website: '', simulate_failure: false, custom_workflow_id: '' });
  const [submitting, setSubmitting] = useState(false);
  const [availableWorkflows, setAvailableWorkflows] = useState([]);
  
  // UI State
  const [activeTab, setActiveTab] = useState('active'); // 'active' or 'history'
  const [selectedProspectId, setSelectedProspectId] = useState(null);

  
  // Custom Agents State
  const [customAgents, setCustomAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);

  // Streaming state
  const [activeStreamId, setActiveStreamId] = useState(null);
  const [streamLogs, setStreamLogs] = useState([]);
  const [currentState, setCurrentState] = useState(null);
  const logsEndRef = useRef(null);
  const sseRef = useRef(null);

  const fetchProspects = async () => {
    try {
      const [data, agentsData, wfData] = await Promise.all([
        prospectsService.getProspects({ limit: 50 }),
        agentService.getAgents().catch(() => []),
        import('../services/api').then(m => m.workflowService.getWorkflows()).catch(() => [])
      ]);
      setProspects(data || []);
      setCustomAgents(agentsData || []);
      setAvailableWorkflows(wfData || []);
    } catch (error) {
      console.error('Failed to fetch prospects:', error);
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
      const submitData = {
        ...formData,
        trigger_event: 'manual_submission'
      };
      
      // Don't send empty string
      if (!submitData.custom_workflow_id) {
        delete submitData.custom_workflow_id;
      }
      
      const result = await prospectsService.createProspect(submitData);
      
      setFormData({ company_name: '', website: '', simulate_failure: false, custom_workflow_id: '' });
      
      if (result.status === 'cached') {
        toast.success('Found recent execution, loading cached data.');
      } else {
        toast.success('Evaluation started.');
      }
      
      const prospectId = result.id || result.prospect_id; 
      startStream(prospectId);

    } catch (error) {
      console.error('Failed to submit prospect:', error);
      toast.error('Failed to submit prospect.');
      setSubmitting(false);
    }
  };

  const startStream = async (prospectId) => {
    setActiveStreamId(prospectId);
    setStreamLogs([{ ts: new Date().toISOString(), agent: 'SYSTEM', msg: `Initializing Live Feed for ${prospectId}...` }]);
    
    // Load historical state immediately
    try {
      const existing = await prospectsService.getProspectById(prospectId);
      if (existing && existing.state_json) {
        let parsed = existing.state_json;
        if (typeof parsed === 'string') parsed = JSON.parse(parsed);
        setCurrentState(parsed);
        setStreamLogs(prev => [...prev, { ts: new Date().toISOString(), agent: 'SYSTEM', msg: 'Historical state loaded.' }]);
      }
    } catch(err) {
      console.warn("Failed to load historical state", err);
    }

    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    if (sseRef.current) {
      sseRef.current.close();
    }
    sseRef.current = new EventSource(`${baseUrl}/api/prospects/${prospectId}/stream`);
    
    sseRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStreamLogs(prev => [...prev, { ts: new Date().toISOString(), agent: data.agent || 'AI', msg: data.message || event.data, type: data.type, payload: data.payload }]);
        if (data.type === 'state_update' && data.payload) {
          setCurrentState(data.payload);
        }
      } catch (e) {
        setStreamLogs(prev => [...prev, { ts: new Date().toISOString(), agent: 'AI', msg: event.data }]);
      }
    };
    
    sseRef.current.onerror = () => {
      setStreamLogs(prev => [...prev, { ts: new Date().toISOString(), agent: 'SYSTEM', msg: 'Stream closed or connection lost.' }]);
    };
  };

  const closeAddForm = () => {
    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
    }
    setShowAddForm(false);
    setActiveStreamId(null);
    setStreamLogs([]);
    setCurrentState(null);
    setSubmitting(false);
    fetchProspects();
  };

  const handleDeleteProspect = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this prospect?")) return;
    try {
      await prospectsService.deleteProspect(id);
      toast.success("Prospect deleted");
      fetchProspects();
    } catch (err) {
      console.error(err);
      toast.error("Failed to delete prospect");
    }
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

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '24px', marginBottom: '32px' }}>
        <Card style={{ padding: '20px', borderTop: '4px solid var(--text-secondary)' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 700, letterSpacing: '0.5px' }}>Total Targets</div>
          <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--text-primary)' }}>{prospects.length}</div>
        </Card>
        <Card style={{ padding: '20px', borderTop: '4px solid var(--success)' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 700, letterSpacing: '0.5px' }}>Approved</div>
          <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--success)' }}>{prospects.filter(p => p.status === 'APPROVED' || p.status === 'COMPLETED').length}</div>
        </Card>
        <Card style={{ padding: '20px', borderTop: '4px solid var(--warning)' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 700, letterSpacing: '0.5px' }}>Pending Review</div>
          <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--warning)' }}>{prospects.filter(p => p.status === 'HITL').length}</div>
        </Card>
        <Card style={{ padding: '20px', borderTop: '4px solid var(--danger)' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 700, letterSpacing: '0.5px' }}>Rejected</div>
          <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--danger)' }}>{prospects.filter(p => p.status === 'REJECTED' || p.status === 'FAILED').length}</div>
        </Card>
        <Card style={{ padding: '20px', borderTop: '4px solid var(--primary-accent)', background: 'linear-gradient(135deg, var(--bg-surface) 0%, rgba(33, 150, 243, 0.05) 100%)' }}>
          <div style={{ fontSize: '12px', color: 'var(--primary-accent)', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 700, letterSpacing: '0.5px' }}>Conversion Rate</div>
          <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--primary-accent)' }}>
            {prospects.length > 0 
              ? Math.round((prospects.filter(p => p.status === 'APPROVED' || p.status === 'COMPLETED').length / prospects.length) * 100)
              : 0}%
          </div>
        </Card>
      </div>

      <Modal 
        isOpen={showAddForm} 
        onClose={closeAddForm} 
        title={activeStreamId ? "Live Execution Feed" : "Submit New Target"}
        icon={activeStreamId ? <TerminalIcon size={20} /> : <Globe size={20} />}
        style={activeStreamId ? { maxWidth: '1200px', width: '95vw' } : {}}
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
            
            <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Workflow (Optional)</label>
              <select 
                value={formData.custom_workflow_id}
                onChange={(e) => setFormData({...formData, custom_workflow_id: e.target.value})}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', background: 'var(--bg-main)', color: 'var(--text-primary)', fontSize: '14px', outline: 'none' }}
              >
                <option value="">Default AI Routing (Dynamic Planner)</option>
                {availableWorkflows.map(wf => (
                  <option key={wf.id} value={wf.id}>{wf.name}</option>
                ))}
              </select>
            </div>
            
            <div className="flex-row" style={{ marginTop: '24px' }}>
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
            <div style={{ display: 'flex', gap: '24px', height: '75vh', minHeight: '550px' }}>
              
              {/* Column 1: Execution DAG */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                <div style={{ marginBottom: '16px', fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)' }}>Execution DAG</div>
                <div style={{ flex: 1, background: 'var(--bg-panel)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                  <LiveGraph state={currentState} />
                </div>
              </div>

              {/* Column 2: Workflow Thought Stream */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                <div style={{ marginBottom: '16px', fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)' }}>Workflow Thought Stream</div>
                <div style={{ flex: 1, background: 'var(--bg-panel)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {streamLogs.filter(log => log.type === 'thought' || log.type === 'action' || log.agent === 'SYSTEM').map((log, i) => {
                    const isSystem = log.agent === 'SYSTEM';
                    return (
                      <div key={i} style={{ display: 'flex', gap: '12px', opacity: i === streamLogs.length - 1 ? 1 : 0.7, transition: 'opacity 0.3s' }}>
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: isSystem ? 'var(--text-tertiary)' : 'var(--primary-accent)', marginTop: '6px' }} />
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '2px' }}>
                            {typeof log.agent === 'object' ? JSON.stringify(log.agent) : String(log.agent)} <span style={{ fontWeight: 400, marginLeft: '8px' }}>{new Date(log.ts).toLocaleTimeString()}</span>
                          </div>
                          <div style={{ fontSize: '14px', color: 'var(--text-primary)', lineHeight: 1.5, background: isSystem ? 'transparent' : 'var(--bg-surface)', padding: isSystem ? '0' : '10px 12px', borderRadius: 'var(--radius-sm)', border: isSystem ? 'none' : '1px solid var(--border-light)' }}>
                            {typeof log.msg === 'object' ? JSON.stringify(log.msg) : String(log.msg)}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {submitting && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text-tertiary)', padding: '8px 0' }}>
                      <div className="spinner" style={{ width: '14px', height: '14px', margin: 0, borderWidth: '2px', borderTopColor: 'var(--text-tertiary)' }} />
                      <span style={{ fontSize: '13px' }}>Agent is thinking...</span>
                    </div>
                  )}
                  <div ref={logsEndRef} />
                </div>
              </div>

              {/* Column 3: Discovered Data & Logs */}
              <div style={{ flex: 1.2, display: 'flex', flexDirection: 'column', minWidth: 0, overflowY: 'auto', paddingRight: '12px' }}>
                <div style={{ marginBottom: '16px', fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)' }}>Discovered Data</div>
                <div className="flex-col" style={{ gap: '16px' }}>
                  
                  {/* Actionable Summary Block */}
                  <div style={{ padding: '16px', background: '#fdfaf6', borderRadius: 'var(--radius-sm)', border: '1px solid var(--primary-accent)', minHeight: '120px', wordBreak: 'break-word', overflow: 'hidden' }}>
                    <div style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--primary-accent)', marginBottom: '12px', fontWeight: 600 }}>Actionable Summary</div>
                    {!currentState?.data?.summary_object ? (
                      <div className="flex-col" style={{ gap: '12px' }}>
                        <div style={{ height: '14px', background: '#e6e2d8', borderRadius: '4px', width: '100%', animation: 'pulse 1.5s infinite' }} />
                        <div style={{ height: '14px', background: '#e6e2d8', borderRadius: '4px', width: '80%', animation: 'pulse 1.5s infinite' }} />
                        <div style={{ height: '14px', background: '#e6e2d8', borderRadius: '4px', width: '90%', animation: 'pulse 1.5s infinite' }} />
                      </div>
                    ) : (() => {
                      let summary = currentState.data.summary_object;
                      if (typeof summary === 'string') {
                        try { summary = JSON.parse(summary); } catch (e) { summary = { overview: summary }; }
                      }
                      if (!summary || typeof summary !== 'object') summary = {};
                      return (
                        <div style={{ fontSize: '14px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          {summary.overview && <div><ReactMarkdown className="markdown-body">{"**Overview:** " + (typeof summary.overview === 'object' ? JSON.stringify(summary.overview) : summary.overview)}</ReactMarkdown></div>}
                          {summary.strengths && <div style={{ color: 'var(--success)' }}><ReactMarkdown className="markdown-body">{"**Strengths:** " + (typeof summary.strengths === 'object' ? JSON.stringify(summary.strengths) : summary.strengths)}</ReactMarkdown></div>}
                          {summary.risks && <div style={{ color: 'var(--danger)' }}><ReactMarkdown className="markdown-body">{"**Risks:** " + (typeof summary.risks === 'object' ? JSON.stringify(summary.risks) : summary.risks)}</ReactMarkdown></div>}
                          {summary.recommendation && <div style={{ color: 'var(--primary-accent)' }}><ReactMarkdown className="markdown-body">{"**Recommendation:** " + (typeof summary.recommendation === 'object' ? JSON.stringify(summary.recommendation) : summary.recommendation)}</ReactMarkdown></div>}
                        </div>
                      );
                    })()}
                  </div>

                  {/* Competitor Intelligence Block */}
                  <div style={{ padding: '16px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', wordBreak: 'break-word', overflow: 'hidden', minHeight: '120px' }}>
                    <div style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--primary-accent)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600 }}>
                      <Globe size={14} /> Competitor Intelligence
                    </div>
                    {!currentState?.data?.competitors_context ? (
                      <div className="flex-col" style={{ gap: '12px' }}>
                        <div style={{ height: '14px', background: '#e6e2d8', borderRadius: '4px', width: '100%', animation: 'pulse 1.5s infinite' }} />
                        <div style={{ height: '14px', background: '#e6e2d8', borderRadius: '4px', width: '90%', animation: 'pulse 1.5s infinite' }} />
                        <div style={{ height: '14px', background: '#e6e2d8', borderRadius: '4px', width: '95%', animation: 'pulse 1.5s infinite' }} />
                      </div>
                    ) : (
                      <div style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                        <ReactMarkdown className="markdown-body">{currentState.data.competitors_context}</ReactMarkdown>
                      </div>
                    )}
                  </div>

                  {/* Tech Stack & Employee Count Row */}
                  <div style={{ display: 'flex', gap: '16px' }}>
                    <div style={{ flex: 1, padding: '16px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '12px', fontWeight: 600 }}>Tech Stack</div>
                      {!currentState?.data?.tech_stack || !Array.isArray(currentState.data.tech_stack) ? (
                        <div style={{ height: '16px', background: '#e6e2d8', borderRadius: '4px', width: '80%', animation: 'pulse 1.5s infinite' }} />
                      ) : (
                        <div style={{ fontSize: '14px', wordWrap: 'break-word', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{currentState.data.tech_stack.map(t => typeof t === 'object' ? JSON.stringify(t) : t).join(', ')}</div>
                      )}
                    </div>
                    
                    <div style={{ flex: 1, padding: '16px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '12px', fontWeight: 600 }}>Employee Count</div>
                      {!currentState?.data?.employee_count ? (
                        <div style={{ height: '16px', background: '#e6e2d8', borderRadius: '4px', width: '50%', animation: 'pulse 1.5s infinite' }} />
                      ) : (
                        <div style={{ fontSize: '14px', lineHeight: 1.5 }}>{typeof currentState.data.employee_count === 'object' ? JSON.stringify(currentState.data.employee_count) : currentState.data.employee_count}</div>
                      )}
                    </div>
                  </div>

                  {/* Decision Makers Block */}
                  <div style={{ padding: '16px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)' }}>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '12px', fontWeight: 600 }}>Decision Makers</div>
                    {!currentState?.data?.contacts || !Array.isArray(currentState.data.contacts) || currentState.data.contacts.length === 0 ? (
                      <div className="flex-col" style={{ gap: '12px' }}>
                        <div style={{ height: '16px', background: '#e6e2d8', borderRadius: '4px', width: '70%', animation: 'pulse 1.5s infinite' }} />
                        <div style={{ height: '16px', background: '#e6e2d8', borderRadius: '4px', width: '60%', animation: 'pulse 1.5s infinite' }} />
                      </div>
                    ) : (
                      <div style={{ fontSize: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {currentState.data.contacts.map((c, idx) => (
                          <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: idx !== currentState.data.contacts.length -1 ? '1px solid #e6e2d8' : 'none', paddingBottom: idx !== currentState.data.contacts.length -1 ? '8px' : '0', gap: '12px', flexWrap: 'wrap' }}>
                            <span style={{ wordWrap: 'break-word', lineHeight: 1.5 }}><strong>{typeof c.name === 'object' ? JSON.stringify(c.name) : c.name}</strong> ({typeof c.title === 'object' ? JSON.stringify(c.title) : c.title})</span>
                            {c.email && <span style={{ color: 'var(--primary-accent)', wordBreak: 'break-all', lineHeight: 1.5 }}>{typeof c.email === 'object' ? JSON.stringify(c.email) : c.email}</span>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* CRM Export Action */}
                  {currentState?.overall_status === 'APPROVED' && (
                     <div style={{ marginTop: '16px' }}>
                       <Button 
                          variant="primary" 
                          icon={<Database size={16} />} 
                          style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
                          onClick={() => alert("Mock: Successfully exported enriched prospect to Salesforce/HubSpot!")}
                       >
                         Export to CRM
                       </Button>
                     </div>
                  )}

                  {/* HITL Action */}
                  {currentState?.overall_status === 'HITL' && (
                     <div style={{ marginTop: '16px' }}>
                       <Button 
                          variant="warning" 
                          icon={<UserCheck size={16} />} 
                          style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
                          onClick={() => navigate('/hitl')}
                       >
                         Go to Human Review
                       </Button>
                     </div>
                  )}

                </div>
              </div>
            </div>
        )}
      </Modal>

      <div style={{ display: 'flex', gap: '32px' }}>
        <div style={{ flex: 2 }}>
          <Card style={{ padding: 0, overflow: 'hidden', position: 'relative' }}>
            <div style={{ display: 'flex', borderBottom: '1px solid var(--border-light)', background: 'var(--bg-main)' }}>
              <button 
                onClick={() => setActiveTab('active')}
                style={{ flex: 1, padding: '16px', background: 'transparent', border: 'none', borderBottom: activeTab === 'active' ? '2px solid var(--primary-accent)' : '2px solid transparent', color: activeTab === 'active' ? 'var(--primary-accent)' : 'var(--text-secondary)', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', transition: 'all 0.2s' }}
              >
                <Layers size={18} /> Active Pipeline
              </button>
              <button 
                onClick={() => setActiveTab('history')}
                style={{ flex: 1, padding: '16px', background: 'transparent', border: 'none', borderBottom: activeTab === 'history' ? '2px solid var(--primary-accent)' : '2px solid transparent', color: activeTab === 'history' ? 'var(--primary-accent)' : 'var(--text-secondary)', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', transition: 'all 0.2s' }}
              >
                <Archive size={18} /> Historical Targets
              </button>
            </div>

            {loading ? (
              <div className="spinner" style={{ margin: '40px auto' }}></div>
            ) : (() => {
              const activeStatuses = ['PENDING', 'PROCESSING', 'HITL'];
              const displayedProspects = prospects.filter(p => activeTab === 'active' ? activeStatuses.includes(p.status) : !activeStatuses.includes(p.status));

              if (displayedProspects.length === 0) {
                return (
                  <div className="flex-col" style={{ alignItems: 'center', padding: '80px 20px', color: 'var(--text-tertiary)' }}>
                    <Globe size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
                    <p>No {activeTab} prospects currently in the pipeline.</p>
                  </div>
                );
              }

              return (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--bg-main)', borderBottom: '1px solid var(--border-light)' }}>
                    <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Target</th>
                    <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Status</th>
                    <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Last Update</th>
                    <th style={{ padding: '16px 24px', textAlign: 'right', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedProspects.map((p) => (
                    <tr 
                      key={p.id} 
                      onClick={() => setSelectedProspectId(p.id)}
                      className="table-row-hover"
                    >
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
                      <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                        {['PENDING', 'PROCESSING', 'HITL'].includes(p.status) && (
                          <button 
                            className="btn btn-secondary" 
                            style={{ padding: '4px 12px', fontSize: '12px' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setShowAddForm(true);
                              startStream(p.id);
                            }}
                          >
                            <TerminalIcon size={12} style={{ marginRight: '6px' }}/> Live Feed
                          </button>
                        )}
                        <button 
                          onClick={(e) => handleDeleteProspect(p.id, e)}
                          style={{ background: 'transparent', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: '4px 8px', marginLeft: '8px' }}
                          title="Delete Prospect"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              );
            })()}

          </Card>
        </div>

        <div style={{ flex: 1 }}>


          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px', color: 'var(--text-primary)', fontWeight: 600, fontSize: '16px' }}>
              <Cpu size={18} color="var(--primary-accent)" /> Custom Agents Fleet
            </div>
            {customAgents.length === 0 ? (
              <div style={{ fontSize: '13px', color: 'var(--text-tertiary)', textAlign: 'center', padding: '24px 0' }}>
                No custom agents deployed.
              </div>
            ) : (
              <div className="flex-col" style={{ gap: '12px' }}>
                {customAgents.map(agent => (
                  <div key={agent.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'var(--bg-main)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
                     <div>
                       <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                         {agent.name} <div className="status-dot pulsing" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--success)' }}></div>
                       </div>
                       <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                         {agent.allowed_tools?.length || 0} tools loaded
                       </div>
                     </div>
                     <button 
                       className="btn btn-secondary" 
                       style={{ padding: '6px 12px', fontSize: '12px' }}
                       onClick={() => setSelectedAgent(agent)}
                     >
                       <TerminalIcon size={12} style={{ marginRight: '6px' }}/> Inspect Logs
                     </button>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card style={{ marginTop: '24px', borderLeft: '4px solid var(--primary-accent)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: 'var(--text-primary)', fontWeight: 600, fontSize: '16px' }}>
              <Layers size={18} color="var(--primary-accent)" /> Workflow Studio
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
              Build your own workflows, create custom agents, and connect tools just like n8n.
            </p>
            <Button variant="primary" style={{ width: '100%', justifyContent: 'center' }} onClick={() => navigate('/workflow-studio')}>
              Open Workflow Studio
            </Button>
          </Card>
        </div>
      </div>
      
      {/* Slide-out detail panel */}
      {selectedProspectId && (
        <ProspectDetailPanel 
          prospectId={selectedProspectId} 
          onClose={() => setSelectedProspectId(null)} 
        />
      )}

      {/* Agent Logs Panel */}
      {selectedAgent && (
        <AgentLogsPanel 
          agent={selectedAgent} 
          onClose={() => setSelectedAgent(null)} 
        />
      )}
    </div>
  );
}
