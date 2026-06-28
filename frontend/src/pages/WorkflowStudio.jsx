import React, { useState, useEffect, useRef } from 'react';
import { PageHeader, Button, Card, Badge, Modal, Input } from '../components/UI';
import { Plus, GitMerge, Trash2, GripVertical, Settings2, Info, ArrowRight, Play, Server, Bot, Search, Briefcase, User, PenTool, LayoutTemplate, Layers } from 'lucide-react';
import { workflowService, agentService } from '../services/api';
import toast from 'react-hot-toast';

export default function WorkflowStudio() {
  const [workflows, setWorkflows] = useState([]);
  const [coreAgents, setCoreAgents] = useState([]);
  const [customAgents, setCustomAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [showAddForm, setShowAddForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  const [formData, setFormData] = useState({ name: '', description: '', steps: [] });
  
  // For showing agent details in a popover/modal
  const [selectedAgentDetails, setSelectedAgentDetails] = useState(null);

  const fetchData = async () => {
    try {
      const [wfData, coreData, customData] = await Promise.all([
        workflowService.getWorkflows(),
        agentService.getCoreAgents(),
        agentService.getAgents()
      ]);
      setWorkflows(wfData || []);
      setCoreAgents(coreData || []);
      setCustomAgents(customData || []);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load Workflow Studio');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    if (formData.steps.length === 0) {
      toast.error("Please add at least one step to the workflow.");
      return;
    }
    
    setSubmitting(true);
    try {
      await workflowService.createWorkflow({
        name: formData.name,
        description: formData.description,
        steps: formData.steps.map(s => s.name)
      });
      setShowAddForm(false);
      setFormData({ name: '', description: '', steps: [] });
      toast.success('Workflow created successfully');
      fetchData();
    } catch (error) {
      console.error('Failed to create workflow:', error);
      toast.error('Failed to create workflow.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await workflowService.deleteWorkflow(id);
      toast.success('Workflow deleted');
      fetchData();
    } catch (error) {
      console.error('Failed to delete workflow:', error);
      toast.error('Failed to delete workflow');
    }
  };
  
  const addStep = (agent) => {
    setFormData(prev => ({
      ...prev,
      steps: [...prev.steps, agent]
    }));
  };
  
  const removeStep = (index) => {
    setFormData(prev => {
      const newSteps = [...prev.steps];
      newSteps.splice(index, 1);
      return { ...prev, steps: newSteps };
    });
  };
  
  // Icon mapping for agents
  const getAgentIcon = (name) => {
    const iconProps = { size: 18, color: 'var(--text-primary)' };
    const n = name.toLowerCase();
    if (n.includes('scraper')) return <LayoutTemplate {...iconProps} />;
    if (n.includes('enricher')) return <Server {...iconProps} />;
    if (n.includes('researcher')) return <Search {...iconProps} />;
    if (n.includes('persona')) return <User {...iconProps} />;
    if (n.includes('contact')) return <Briefcase {...iconProps} />;
    if (n.includes('outreach')) return <PenTool {...iconProps} />;
    if (n.includes('hitl')) return <User {...iconProps} />;
    return <Bot {...iconProps} />;
  };

  const allAgents = [
    ...coreAgents.map(a => ({ ...a, type: 'core' })),
    ...customAgents.map(a => ({ ...a, type: 'custom' }))
  ];

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', width: '100%', paddingBottom: '100px' }}>
      <PageHeader 
        title="Workflow Studio" 
        description="Design and manage custom orchestration pipelines using your trained agents."
        actions={
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setShowAddForm(true)}>
            Create Workflow
          </Button>
        }
      />

      {loading ? (
        <div className="spinner"></div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
          {workflows.length === 0 && (
            <div style={{ gridColumn: '1 / -1', padding: '40px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
              No workflows created yet. Click "Create Workflow" to get started.
            </div>
          )}
          {workflows.map((workflow) => (
            <Card key={workflow.id} style={{ display: 'flex', flexDirection: 'column' }}>
              <div className="flex-row justify-between" style={{ marginBottom: '16px' }}>
                <Badge variant="neutral">
                  <GitMerge size={12} style={{ marginRight: '4px' }} /> Custom Pipeline
                </Badge>
                <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
                  {workflow.steps.length} steps
                </div>
              </div>

              <h3 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px', fontFamily: '"Source Serif 4", serif' }}>
                {workflow.name}
              </h3>
              
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px', flex: 1 }}>
                {workflow.description}
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '24px' }}>
                {workflow.steps.map((step, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                    <div style={{ width: '18px', height: '18px', borderRadius: '50%', background: 'var(--bg-main)', border: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px' }}>
                      {i + 1}
                    </div>
                    {step}
                  </div>
                ))}
              </div>

              <div className="flex-row justify-between" style={{ gap: '12px', paddingTop: '16px', borderTop: '1px solid var(--border-light)' }}>
                <button onClick={() => handleDelete(workflow.id)} style={{ padding: '8px', background: 'transparent', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', color: 'var(--danger)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%' }} title="Delete Workflow">
                  <Trash2 size={16} style={{marginRight: '8px'}} /> Delete Workflow
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* FULL SCREEN MODAL FOR N8N STYLE EDITOR */}
      {showAddForm && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'var(--bg-panel)', zIndex: 9999, display: 'flex', flexDirection: 'column' }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px', background: 'var(--bg-main)', borderBottom: '1px solid var(--border-light)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <Layers size={24} color="var(--primary-accent)" />
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Workflow Studio Canvas</h2>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Design your custom agent sequence</div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <Button onClick={() => setShowAddForm(false)}>Cancel</Button>
              <Button variant="primary" onClick={handleAddSubmit} disabled={submitting || !formData.name || formData.steps.length === 0}>
                {submitting ? 'Saving...' : 'Save Workflow'}
              </Button>
            </div>
          </div>

          {/* Canvas Area */}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            
            {/* Left Panel - Canvas */}
            <div style={{ flex: 1, background: '#1a1a1a', position: 'relative', overflow: 'auto', padding: '40px' }}>
              {/* Dot grid background */}
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundImage: 'radial-gradient(circle, #333 1px, transparent 1px)', backgroundSize: '20px 20px', opacity: 0.5, pointerEvents: 'none' }} />
              
              <div style={{ position: 'relative', zIndex: 10, display: 'flex', alignItems: 'center', minWidth: 'max-content' }}>
                
                {/* START NODE */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginRight: '40px' }}>
                  <div style={{ width: '60px', height: '60px', borderRadius: '12px', background: 'var(--primary-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 8px 24px rgba(230, 226, 216, 0.2)' }}>
                    <Play size={24} color="#000" fill="#000" />
                  </div>
                  <div style={{ marginTop: '12px', fontSize: '12px', fontWeight: 600, color: '#fff' }}>On Prospect Trigger</div>
                </div>

                {formData.steps.map((step, index) => (
                  <React.Fragment key={index}>
                    {/* CONNECTOR */}
                    <div style={{ width: '40px', height: '2px', background: 'var(--primary-accent)', position: 'relative', marginRight: '40px' }}>
                       <div style={{ position: 'absolute', right: '-6px', top: '-4px', width: 0, height: 0, borderTop: '5px solid transparent', borderBottom: '5px solid transparent', borderLeft: '8px solid var(--primary-accent)' }}></div>
                    </div>

                    {/* AGENT NODE */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginRight: '40px', position: 'relative', minWidth: '220px' }}>
                      <div 
                        style={{ 
                          width: '100%', 
                          background: 'var(--bg-main)', 
                          border: `1px solid ${step.type === 'core' ? '#3b82f6' : '#10b981'}`, 
                          borderRadius: '8px', 
                          padding: '16px', 
                          boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '12px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{ padding: '6px', background: 'var(--bg-panel)', borderRadius: '6px' }}>
                              {getAgentIcon(step.name)}
                            </div>
                            <div>
                              <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>{step.name}</div>
                              <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                {step.type === 'core' ? 'System Agent' : 'Custom Agent'}
                              </div>
                            </div>
                          </div>
                          <button type="button" onClick={() => removeStep(index)} style={{ background: 'transparent', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', padding: '4px' }}>
                            <Trash2 size={14} />
                          </button>
                        </div>
                        
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4, maxHeight: '40px', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                          {step.description}
                        </div>

                        {/* Node Input/Output Ports (Visual only) */}
                        <div style={{ position: 'absolute', left: '-5px', top: '50%', transform: 'translateY(-50%)', width: '10px', height: '10px', background: 'var(--bg-main)', border: '2px solid var(--primary-accent)', borderRadius: '50%' }} />
                        <div style={{ position: 'absolute', right: '-5px', top: '50%', transform: 'translateY(-50%)', width: '10px', height: '10px', background: 'var(--primary-accent)', borderRadius: '50%' }} />
                      </div>
                    </div>
                  </React.Fragment>
                ))}

                {/* END CONNECTOR & NODE */}
                {formData.steps.length > 0 && (
                   <React.Fragment>
                    <div style={{ width: '40px', height: '2px', background: 'var(--primary-accent)', position: 'relative', marginRight: '40px' }}>
                       <div style={{ position: 'absolute', right: '-6px', top: '-4px', width: 0, height: 0, borderTop: '5px solid transparent', borderBottom: '5px solid transparent', borderLeft: '8px solid var(--primary-accent)' }}></div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <div style={{ width: '60px', height: '60px', borderRadius: '50%', background: 'transparent', border: '2px dashed var(--text-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <div style={{ width: '20px', height: '20px', background: 'var(--text-tertiary)', borderRadius: '2px' }} />
                      </div>
                      <div style={{ marginTop: '12px', fontSize: '12px', fontWeight: 600, color: 'var(--text-tertiary)' }}>End</div>
                    </div>
                   </React.Fragment>
                )}

                {formData.steps.length === 0 && (
                   <div style={{ marginLeft: '40px', padding: '20px', border: '1px dashed var(--border-light)', borderRadius: '8px', color: 'var(--text-tertiary)', fontSize: '14px' }}>
                     Add nodes from the sidebar →
                   </div>
                )}
              </div>
            </div>

            {/* Right Panel - Configuration & Agents */}
            <div style={{ width: '400px', background: 'var(--bg-main)', borderLeft: '1px solid var(--border-light)', display: 'flex', flexDirection: 'column', zIndex: 20, boxShadow: '-4px 0 24px rgba(0,0,0,0.2)' }}>
              
              <div style={{ padding: '24px', borderBottom: '1px solid var(--border-light)' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '16px' }}>Workflow Settings</h3>
                <Input 
                  label="Workflow Name" 
                  value={formData.name} 
                  onChange={(e) => setFormData({...formData, name: e.target.value})} 
                  required 
                  placeholder="e.g. Enterprise ICP Enrichment"
                />
                <Input 
                  label="Description" 
                  value={formData.description} 
                  onChange={(e) => setFormData({...formData, description: e.target.value})} 
                  placeholder="What does this workflow accomplish?"
                  style={{ marginTop: '12px' }}
                />
              </div>

              <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '16px' }}>Nodes</h3>
                
                <div style={{ marginBottom: '24px' }}>
                  <h4 style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '12px', letterSpacing: '0.5px' }}>Core Agents</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {coreAgents.map(agent => (
                      <div key={agent.name} style={{ display: 'flex', flexDirection: 'column', background: 'var(--bg-panel)', border: '1px solid var(--border-light)', borderRadius: '6px', overflow: 'hidden' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', borderBottom: '1px solid var(--border-light)', background: '#1c1c1c' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {getAgentIcon(agent.name)}
                            <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>{agent.name}</span>
                          </div>
                          <Button variant="secondary" style={{ padding: '4px 8px', fontSize: '11px', height: 'auto' }} onClick={() => addStep({...agent, type: 'core'})}>
                            Add Node
                          </Button>
                        </div>
                        <div style={{ padding: '12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                          <div style={{ marginBottom: '8px' }}>{agent.description}</div>
                          <div style={{ display: 'flex', gap: '16px', marginTop: '12px' }}>
                             <div style={{ flex: 1 }}>
                               <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '4px' }}>Inputs</div>
                               <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                 {(agent.inputs || []).map((inp, idx) => <span key={idx} style={{ background: '#2d2d2d', padding: '2px 6px', borderRadius: '4px', fontSize: '10px', color: '#a3a3a3' }}>{inp}</span>)}
                               </div>
                             </div>
                             <div style={{ flex: 1 }}>
                               <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '4px' }}>Outputs</div>
                               <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                 {(agent.outputs || []).map((out, idx) => <span key={idx} style={{ background: '#2d2d2d', padding: '2px 6px', borderRadius: '4px', fontSize: '10px', color: '#a3a3a3' }}>{out}</span>)}
                               </div>
                             </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '12px', letterSpacing: '0.5px' }}>Custom Agents</h4>
                  {customAgents.length === 0 ? (
                    <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', padding: '16px', background: 'var(--bg-panel)', borderRadius: '6px', textAlign: 'center' }}>
                      No custom agents available. Create them in the Agent Hub.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {customAgents.map(agent => (
                        <div key={agent.id} style={{ display: 'flex', flexDirection: 'column', background: 'var(--bg-panel)', border: '1px solid var(--border-light)', borderRadius: '6px', overflow: 'hidden' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', borderBottom: '1px solid var(--border-light)', background: '#1c1c1c' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <Bot size={18} color="#10b981" />
                              <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>{agent.name}</span>
                            </div>
                            <Button variant="secondary" style={{ padding: '4px 8px', fontSize: '11px', height: 'auto' }} onClick={() => addStep({...agent, type: 'custom', inputs: ['prospect_data'], outputs: ['custom_insights']})}>
                              Add Node
                            </Button>
                          </div>
                          <div style={{ padding: '12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                            <div style={{ marginBottom: '8px' }}>{agent.description}</div>
                            {agent.allowed_tools && agent.allowed_tools.length > 0 && (
                               <div style={{ marginTop: '12px' }}>
                                 <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '4px' }}>Tools</div>
                                 <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                   {agent.allowed_tools.map((tool, idx) => <span key={idx} style={{ background: '#2d2d2d', padding: '2px 6px', borderRadius: '4px', fontSize: '10px', color: '#10b981' }}>{tool}</span>)}
                                 </div>
                               </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
