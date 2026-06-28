import React, { useEffect, useState } from 'react';
import { prospectsService } from '../services/api';
import { Badge, Button } from './UI';
import { X, Network, Briefcase, ChevronRight, Activity, FileText, LayoutList, Mail, AlignLeft, Clock, UserCheck } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useNavigate } from 'react-router-dom';

export default function ProspectDetailPanel({ prospectId, onClose }) {
  const navigate = useNavigate();
  const [prospect, setProspect] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (!prospectId) return;
    setLoading(true);
    prospectsService.getProspectDetail(prospectId)
      .then(data => setProspect(data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [prospectId]);

  if (loading) {
    return (
      <div style={panelStyles.container}>
        <div style={panelStyles.header}>
          <h2 style={{ fontSize: '18px', margin: 0 }}>Loading Details...</h2>
          <button onClick={onClose} style={panelStyles.closeBtn}><X size={20} /></button>
        </div>
        <div style={panelStyles.content} className="flex-row justify-center items-center">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  if (error || !prospect) {
    return (
      <div style={panelStyles.container}>
        <div style={panelStyles.header}>
          <h2 style={{ fontSize: '18px', margin: 0 }}>Error</h2>
          <button onClick={onClose} style={panelStyles.closeBtn}><X size={20} /></button>
        </div>
        <div style={{ padding: '20px', color: 'var(--danger)' }}>
          Failed to load prospect details: {error || 'Not found'}
        </div>
      </div>
    );
  }

  const state = prospect.state_json || {};
  const data = state.data || {};
  const executionTrace = state.execution_trace || [];
  const executedAgents = state.executed_agents || [];
  const outreachDrafts = data.outreach_drafts || [];

  return (
    <div style={panelStyles.container}>
      <div style={panelStyles.header}>
        <div className="flex-col">
          <h2 style={{ fontSize: '20px', margin: 0, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Briefcase size={20} color="var(--primary-accent)" /> 
            {prospect.company_name}
          </h2>
          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
            Workflow Thread: {prospect.workflow_thread_id || prospect.id}
          </div>
        </div>
        <button onClick={onClose} style={panelStyles.closeBtn}><X size={20} /></button>
      </div>
      
      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border-light)', background: 'var(--bg-main)' }}>
        <button 
          style={activeTab === 'overview' ? panelStyles.activeTabBtn : panelStyles.tabBtn} 
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button 
          style={activeTab === 'trace' ? panelStyles.activeTabBtn : panelStyles.tabBtn} 
          onClick={() => setActiveTab('trace')}
        >
          Execution Trace
        </button>
        <button 
          style={activeTab === 'outreach' ? panelStyles.activeTabBtn : panelStyles.tabBtn} 
          onClick={() => setActiveTab('outreach')}
        >
          Outreach Drafts {outreachDrafts.length > 0 && <Badge variant="success" style={{ marginLeft: '6px' }}>{outreachDrafts.length}</Badge>}
        </button>
      </div>

      <div style={panelStyles.content}>
        
        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <>
            <div style={{ padding: '16px', background: 'var(--bg-surface)', borderBottom: '1px solid var(--border-light)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 600 }}>Final Status</div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>{prospect.status}</div>
              </div>
              <div>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 600 }}>Trigger Source</div>
                <div style={{ fontSize: '14px', marginTop: '4px' }}>{state.current_trigger_event || 'Unknown'}</div>
              </div>
              <div>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 600 }}>Confidence</div>
                <div style={{ fontSize: '14px', marginTop: '4px', color: state.confidence_score > 0.7 ? 'var(--success)' : 'var(--warning)' }}>
                  {Math.round((state.confidence_score || 0) * 100)}%
                </div>
              </div>
            </div>

            <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '32px' }}>
              {/* Actionable Summary */}
              {data.summary_object && (
                <section>
                  <h3 style={panelStyles.sectionTitle}><FileText size={16} /> Actionable Summary</h3>
                  {(() => {
                    let summary = data.summary_object;
                    let isJson = false;
                    let parsedSummary = {};
                    if (typeof summary === 'string') {
                      try { 
                        parsedSummary = JSON.parse(summary); 
                        isJson = true;
                      } catch (e) { 
                        isJson = false;
                      }
                    } else if (typeof summary === 'object') {
                      parsedSummary = summary;
                      isJson = true;
                    }

                    if (isJson) {
                      return (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          {parsedSummary.overview && (
                            <div style={panelStyles.summaryBox}>
                              <div style={panelStyles.summaryLabel}>Overview</div>
                              <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>{parsedSummary.overview}</div>
                            </div>
                          )}
                          {parsedSummary.strengths && (
                            <div style={{ ...panelStyles.summaryBox, borderLeft: '3px solid var(--success)' }}>
                              <div style={{ ...panelStyles.summaryLabel, color: 'var(--success)' }}>Strengths</div>
                              <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>{parsedSummary.strengths}</div>
                            </div>
                          )}
                          {parsedSummary.risks && (
                            <div style={{ ...panelStyles.summaryBox, borderLeft: '3px solid var(--danger)' }}>
                              <div style={{ ...panelStyles.summaryLabel, color: 'var(--danger)' }}>Risks / Weaknesses</div>
                              <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>{parsedSummary.risks}</div>
                            </div>
                          )}
                          {parsedSummary.recommendation && (
                            <div style={{ ...panelStyles.summaryBox, borderLeft: '3px solid var(--primary-accent)' }}>
                              <div style={{ ...panelStyles.summaryLabel, color: 'var(--primary-accent)' }}>Recommendation</div>
                              <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>{parsedSummary.recommendation}</div>
                            </div>
                          )}
                        </div>
                      );
                    }

                    // Markdown rendering
                    return (
                      <div className="markdown-summary" style={panelStyles.markdownContainer}>
                        <ReactMarkdown>{summary}</ReactMarkdown>
                      </div>
                    );
                  })()}
                </section>
              )}

              {/* Firmographics & Tech */}
              <section>
                <h3 style={panelStyles.sectionTitle}><LayoutList size={16} /> Discovered Data</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div style={{ background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', padding: '16px' }}>
                    <div style={panelStyles.summaryLabel}>Tech Stack</div>
                    {data.tech_stack && data.tech_stack.length > 0 ? (
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '8px' }}>
                        {data.tech_stack.map((tech, i) => (
                          <Badge key={i} variant="neutral" style={{ background: 'var(--bg-surface)' }}>
                            {typeof tech === 'string' ? tech : tech.technology || tech}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: '13px', color: 'var(--text-tertiary)', marginTop: '8px' }}>None detected</div>
                    )}
                  </div>
                  
                  <div style={{ background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', padding: '16px' }}>
                    <div style={panelStyles.summaryLabel}>Firmographics</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px', fontSize: '13px' }}>
                      {data.firmographics ? (
                        <>
                          {data.firmographics.employee_count && <div><strong>Employees:</strong> {data.firmographics.employee_count}</div>}
                          {data.firmographics.estimated_revenue && <div><strong>Revenue:</strong> {data.firmographics.estimated_revenue}</div>}
                          {data.firmographics.industry && <div><strong>Industry:</strong> {data.firmographics.industry}</div>}
                        </>
                      ) : (
                        <div style={{ color: 'var(--text-tertiary)' }}>No firmographics found</div>
                      )}
                    </div>
                  </div>
                </div>
              </section>

              {/* HITL Action */}
              {prospect.status === 'HITL' && (
                 <div style={{ marginTop: '16px' }}>
                   <Button 
                      variant="warning" 
                      icon={<UserCheck size={16} />} 
                      style={{ width: '100%', justifyContent: 'center' }}
                      onClick={() => navigate('/hitl')}
                   >
                     Go to Human Review
                   </Button>
                 </div>
              )}
            </div>
          </>
        )}

        {/* EXECUTION TRACE TAB */}
        {activeTab === 'trace' && (
          <div style={{ padding: '24px' }} className="slideInRight">
            <h3 style={panelStyles.sectionTitle}><Network size={16} /> Orchestrator Timeline</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
              A visualization of the dynamically orchestrated agent execution path.
            </p>
            
            {(prospect.status === 'PENDING' || prospect.status === 'IN_PROGRESS' || state.overall_status === 'PENDING') && (
              <div className="rate-limit-banner">
                <Clock size={16} />
                <div>
                  <strong>Rate Limit Pacing Active</strong> — Enforcing a 2.5s delay between LLM calls to respect free tier quotas.
                </div>
              </div>
            )}
            
            {executionTrace.length === 0 ? (
              executedAgents.length === 0 ? (
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
                  No execution trace available for this workflow. 
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', position: 'relative' }}>
                  <div className="trace-line-animated"></div>
                  {executedAgents.map((agent, idx) => {
                    const isLast = idx === executedAgents.length - 1;
                    return (
                      <div key={idx} style={{ display: 'flex', gap: '20px', position: 'relative', zIndex: 1 }}>
                        <div className={isLast ? "glow-node" : ""} style={{ width: '40px', height: '40px', borderRadius: '50%', background: isLast ? 'var(--primary-accent)' : 'var(--bg-surface)', border: `2px solid var(--primary-accent)`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '4px', transition: 'all 0.3s' }}>
                          <Activity size={18} color={isLast ? '#fff' : 'var(--primary-accent)'} />
                        </div>
                        <div className="shine-effect" style={{ background: 'var(--bg-main)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: '20px', flex: 1, position: 'relative', boxShadow: isLast ? 'var(--shadow-sm)' : 'none' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '15px' }}>{agent.replace('_node', '').replace(/_/g, ' ').toUpperCase()}</div>
                            <Badge variant={isLast ? "primary" : "success"} style={{ fontSize: '11px' }}>{isLast ? "Active/Completed" : "Completed"}</Badge>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', position: 'relative' }}>
                <div className="trace-line-animated"></div>
                {executionTrace.map((step, idx) => {
                  const isLast = idx === executionTrace.length - 1;
                  return (
                    <div key={idx} style={{ display: 'flex', gap: '20px', position: 'relative', zIndex: 1 }}>
                      <div className={isLast ? "glow-node" : ""} style={{ width: '40px', height: '40px', borderRadius: '50%', background: isLast ? 'var(--primary-accent)' : 'var(--bg-surface)', border: `2px solid var(--primary-accent)`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '4px', transition: 'all 0.3s' }}>
                        <Activity size={18} color={isLast ? '#fff' : 'var(--primary-accent)'} />
                      </div>
                      <div className="shine-effect" style={{ background: 'var(--bg-main)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: '20px', flex: 1, position: 'relative', boxShadow: isLast ? 'var(--shadow-sm)' : 'none' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '15px' }}>{step.agent.replace('_node', '').replace(/_/g, ' ').toUpperCase()}</div>
                          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--bg-surface)', padding: '2px 8px', borderRadius: '100px', border: '1px solid var(--border-light)' }}>
                            <Clock size={12} /> {(step.duration_seconds || 0).toFixed(2)}s
                          </div>
                        </div>
                        
                        {step.recent_thoughts && step.recent_thoughts.length > 0 && (
                          <div style={{ marginBottom: '16px', background: 'rgba(255,255,255,0.5)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                            <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 600, marginBottom: '8px' }}><AlignLeft size={10} style={{ display: 'inline', marginRight: '4px' }}/> Agent Thoughts</div>
                            <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                              {step.recent_thoughts.map((t, i) => <li key={i}>{t}</li>)}
                            </ul>
                          </div>
                        )}
                        
                        {step.updates && Object.keys(step.updates).length > 0 && (
                          <div>
                            <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', fontWeight: 600, marginBottom: '8px' }}>State Updates (Outputs)</div>
                            <pre style={{ margin: 0, padding: '16px', background: '#2d2d2d', borderRadius: 'var(--radius-sm)', fontSize: '12px', overflowX: 'auto', color: '#e6e6e6', fontFamily: '"JetBrains Mono", monospace' }}>
                              {JSON.stringify(step.updates, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* OUTREACH DRAFTS TAB */}
        {activeTab === 'outreach' && (
          <div style={{ padding: '24px' }}>
            <h3 style={panelStyles.sectionTitle}><Mail size={16} /> Generated Outreach Sequences</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
              Highly personalized email drafts generated by the Outreach Generator Agent.
            </p>
            
            {outreachDrafts.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
                No outreach drafts available for this prospect. 
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {outreachDrafts.map((draft, idx) => (
                  <div key={idx} style={{ background: 'var(--bg-main)', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                    <div style={{ padding: '12px 16px', background: 'var(--bg-surface)', borderBottom: '1px solid var(--border-light)', display: 'flex', justifyContent: 'space-between' }}>
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>To: {draft.contact_name}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>{draft.contact_title}</div>
                      </div>
                      <Badge variant="primary">Draft</Badge>
                    </div>
                    <div style={{ padding: '16px' }}>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
                        Subject: {draft.subject}
                      </div>
                      <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                        {draft.body}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

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
    background: 'var(--bg-panel)',
    borderLeft: '1px solid var(--border-light)',
    boxShadow: '-4px 0 32px rgba(0,0,0,0.15)',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 1000,
    animation: 'slideInRight 0.3s ease-out forwards'
  },
  header: {
    padding: '24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    background: 'var(--bg-main)'
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--text-tertiary)',
    padding: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 'var(--radius-sm)',
    transition: 'background 0.2s'
  },
  tabBtn: {
    flex: 1,
    padding: '12px',
    background: 'transparent',
    border: 'none',
    borderBottom: '2px solid transparent',
    color: 'var(--text-secondary)',
    fontWeight: 600,
    fontSize: '13px',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  activeTabBtn: {
    flex: 1,
    padding: '12px',
    background: 'transparent',
    border: 'none',
    borderBottom: '2px solid var(--primary-accent)',
    color: 'var(--primary-accent)',
    fontWeight: 600,
    fontSize: '13px',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  content: {
    flex: 1,
    overflowY: 'auto'
  },
  sectionTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: '12px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  summaryBox: {
    background: 'var(--bg-main)', 
    borderRadius: 'var(--radius-sm)', 
    border: '1px solid var(--border-light)', 
    padding: '16px'
  },
  summaryLabel: {
    fontSize: '11px', 
    textTransform: 'uppercase', 
    fontWeight: 600, 
    marginBottom: '8px',
    color: 'var(--text-tertiary)'
  },
  markdownContainer: {
    background: 'var(--bg-main)',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-light)',
    padding: '24px',
    fontSize: '14px',
    lineHeight: 1.6,
    color: 'var(--text-primary)'
  }
};
