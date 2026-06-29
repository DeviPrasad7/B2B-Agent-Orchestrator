import React, { useState, useEffect, useCallback } from 'react';
import { PageHeader, Button, Card, Badge, Input } from '../components/UI';
import { Plus, GitMerge, Trash2, LayoutTemplate, Server, Search, User, Briefcase, PenTool, Bot, Layers, X } from 'lucide-react';
import { workflowService, agentService } from '../services/api';
import toast from 'react-hot-toast';
import { ReactFlow, Controls, Background, addEdge, applyNodeChanges, applyEdgeChanges, Handle, Position, ReactFlowProvider, BaseEdge, EdgeLabelRenderer, getBezierPath, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const CustomEdge = ({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style, markerEnd }) => {
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });
  const { setEdges } = useReactFlow();

  const onEdgeClick = (evt) => {
    evt.stopPropagation();
    setEdges((edges) => edges.filter((e) => e.id !== id));
  };

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          <button 
            onClick={onEdgeClick} 
            style={{ 
              background: '#ef4444', color: '#fff', border: 'none', borderRadius: '50%', 
              width: '18px', height: '18px', cursor: 'pointer', display: 'flex', 
              alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' 
            }}
            title="Remove Connection"
          >
            <X size={12} strokeWidth={3} />
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  );
};

// Custom Node for rendering agents in the graph
const AgentNode = ({ id, data }) => {
  const isEnder = data.agentId === 'ender_node';
  const isStart = data.agentId === 'start';
  const borderColor = isEnder ? '#ef4444' : (isStart ? '#f59e0b' : (data.type === 'core' ? '#3b82f6' : '#10b981'));
  const bgColor = isStart ? '#fffbeb' : '#ffffff';
  const { setNodes, setEdges } = useReactFlow();

  const onDeleteClick = (evt) => {
    evt.stopPropagation();
    setNodes((nds) => nds.filter((n) => n.id !== id));
    setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
  };

  const handleStyle = { 
    width: '24px', 
    height: '24px', 
    background: borderColor, 
    display: 'flex', 
    alignItems: 'center', 
    justifyContent: 'center', 
    color: '#fff', 
    fontSize: '16px', 
    fontWeight: 'bold',
    cursor: 'crosshair',
    border: '2px solid #fff'
  };

  return (
    <div style={{ background: bgColor, border: `2px solid ${borderColor}`, borderRadius: '12px', padding: isStart ? '24px' : '16px', minWidth: isStart ? '260px' : '220px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', color: '#000000', position: 'relative' }}>
      {!isEnder && !isStart && (
        <button 
          onClick={onDeleteClick}
          style={{ position: 'absolute', top: '-10px', right: '-10px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: '50%', width: '20px', height: '20px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', zIndex: 10 }}
          title="Delete Agent"
        >
          <X size={12} strokeWidth={3} />
        </button>
      )}
      
      {!isStart && <Handle type="target" position={Position.Left} style={{...handleStyle, left: '-12px'}} />}
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <div style={{ fontWeight: 700, fontSize: isStart ? '18px' : '15px', color: '#000000' }}>{data.label}</div>
      </div>
      
      <div style={{ fontSize: isStart ? '14px' : '12px', color: '#4b5563', lineHeight: 1.4 }}>
        {data.description}
      </div>
      
      {!isEnder && <Handle type="source" position={Position.Right} style={{...handleStyle, right: '-12px'}}>+</Handle>}
    </div>
  );
};

const nodeTypes = {
  agentNode: AgentNode,
};
const edgeTypes = {
  custom: CustomEdge,
};

const WorkflowStepsList = ({ nodes }) => {
  if (!nodes || nodes.length === 0) return null;
  
  // Sort nodes roughly by X position to simulate flow order
  const sortedNodes = [...nodes].sort((a, b) => (a.position?.x || 0) - (b.position?.x || 0));

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center', marginBottom: '16px', padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
      {sortedNodes.map((node, idx) => {
        const isStart = node.data?.agentId === 'start';
        const isEnder = node.data?.agentId === 'ender_node';
        
        const bgColor = isStart ? '#fffbeb' : (isEnder ? '#fef2f2' : '#eff6ff');
        const textColor = isStart ? '#b45309' : (isEnder ? '#b91c1c' : '#1d4ed8');
        const borderColor = isStart ? '#fcd34d' : (isEnder ? '#fca5a5' : '#bfdbfe');

        return (
          <React.Fragment key={node.id}>
            <div style={{
              padding: '4px 10px',
              background: bgColor,
              color: textColor,
              border: `1px solid ${borderColor}`,
              borderRadius: '16px',
              fontSize: '11px',
              fontWeight: 600,
              whiteSpace: 'nowrap'
            }}>
              {node.data?.label || node.id}
            </div>
            {idx < sortedNodes.length - 1 && (
              <div style={{ color: '#cbd5e1', fontSize: '14px', fontWeight: 'bold' }}>→</div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

export default function WorkflowStudio() {
  const [workflows, setWorkflows] = useState([]);
  const [coreAgents, setCoreAgents] = useState([]);
  const [customAgents, setCustomAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [showAddForm, setShowAddForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  const [formData, setFormData] = useState({ name: '', description: '' });
  
  // React Flow state
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);

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
  
  useEffect(() => {
    if (showAddForm) {
      // Find ender node from core agents
      const enderDesc = coreAgents.find(a => a.name === 'ender_node')?.description || "Consolidates and dispatches.";
      
      setNodes([
        { 
          id: 'start', 
          type: 'agentNode', 
          data: { agentId: 'start', type: 'trigger', label: 'On Prospect Trigger', description: 'Starts the workflow when a prospect is added.' }, 
          position: { x: 50, y: 200 }
        },
        { 
          id: 'ender_1', 
          type: 'agentNode', 
          data: { label: 'ender_node', agentId: 'ender_node', type: 'core', description: enderDesc }, 
          position: { x: 500, y: 200 } 
        }
      ]);
      setEdges([]);
      setFormData({ name: '', description: '' });
    }
  }, [showAddForm, coreAgents]);

  const onNodesChange = useCallback((changes) => setNodes((nds) => applyNodeChanges(changes, nds)), []);
  const onEdgesChange = useCallback((changes) => setEdges((eds) => applyEdgeChanges(changes, eds)), []);
  const onConnect = useCallback((params) => setEdges((eds) => addEdge({ ...params, type: 'custom' }, eds)), []);

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await workflowService.createWorkflow({
        name: formData.name,
        description: formData.description,
        steps: { nodes, edges } // Save as DAG
      });
      setShowAddForm(false);
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
  
  const addNodeToCanvas = (agent) => {
    const newNode = {
      id: `${agent.name}_${Date.now()}`,
      type: 'agentNode',
      position: { x: 250, y: 150 + Math.random() * 100 },
      data: {
        label: agent.name,
        agentId: agent.name,
        type: agent.type,
        description: agent.description
      }
    };
    setNodes((nds) => [...nds, newNode]);
  };
  
  const getAgentIcon = (name) => {
    const iconProps = { size: 16, color: '#000' };
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
                  {workflow.steps?.nodes ? workflow.steps.nodes.length : (workflow.steps?.length || 0)} nodes
                </div>
              </div>

              {workflow.steps?.nodes && (
                <WorkflowStepsList nodes={workflow.steps.nodes} />
              )}

              <h3 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px', fontFamily: '"Source Serif 4", serif' }}>
                {workflow.name}
              </h3>
              
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px', flex: 1 }}>
                {workflow.description}
              </p>
              
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
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: '#f9fafb', zIndex: 9999, display: 'flex', flexDirection: 'column' }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px', background: '#ffffff', borderBottom: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <Layers size={24} color="#3b82f6" />
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#000000', margin: 0 }}>Workflow Studio Canvas</h2>
                <div style={{ fontSize: '13px', color: '#4b5563' }}>Design your custom agent DAG</div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <Button style={{ color: '#000', border: '1px solid #ccc' }} onClick={() => setShowAddForm(false)}>Cancel</Button>
              <Button variant="primary" onClick={handleAddSubmit} disabled={submitting || !formData.name}>
                {submitting ? 'Saving...' : 'Save Workflow'}
              </Button>
            </div>
          </div>

          {/* Canvas Area */}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            
            {/* Left Panel - Canvas */}
            <div style={{ flex: 1, position: 'relative' }}>
              <ReactFlowProvider>
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  nodeTypes={nodeTypes}
                  edgeTypes={edgeTypes}
                  deleteKeyCode={['Backspace', 'Delete']}
                  fitView
                >
                  <Background color="#ccc" gap={16} />
                  <Controls />
                </ReactFlow>
              </ReactFlowProvider>
            </div>

            {/* Right Panel - Configuration & Agents */}
            <div style={{ width: '380px', background: '#ffffff', borderLeft: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column', zIndex: 20, boxShadow: '-4px 0 24px rgba(0,0,0,0.05)' }}>
              
              <div style={{ padding: '24px', borderBottom: '1px solid #e5e7eb' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#000000', marginBottom: '16px' }}>Settings</h3>
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#000', marginBottom: '4px' }}>Workflow Name</label>
                  <input 
                    type="text"
                    style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', color: '#000' }}
                    value={formData.name} 
                    onChange={(e) => setFormData({...formData, name: e.target.value})} 
                    placeholder="e.g. Parallel Pipeline"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#000', marginBottom: '4px' }}>Description</label>
                  <textarea 
                    style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', color: '#000', minHeight: '60px' }}
                    value={formData.description} 
                    onChange={(e) => setFormData({...formData, description: e.target.value})} 
                    placeholder="Workflow description..."
                  />
                </div>
              </div>

              <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#000000', marginBottom: '16px' }}>Available Agents</h3>
                
                <div style={{ marginBottom: '24px' }}>
                  <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: '#4b5563', marginBottom: '12px', fontWeight: 700 }}>Core Agents</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {coreAgents.map(agent => (
                      <div key={agent.name} style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px', background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {getAgentIcon(agent.name)}
                            <div>
                              <span style={{ fontSize: '14px', fontWeight: 600, color: '#000', display: 'block' }}>{agent.name}</span>
                              <span style={{ fontSize: '12px', color: '#6b7280', display: 'block', lineHeight: 1.3 }}>{agent.description}</span>
                            </div>
                          </div>
                          <button 
                            onClick={() => addNodeToCanvas({...agent, type: 'core'})}
                            style={{ background: '#fff', border: '1px solid #ccc', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', cursor: 'pointer', color: '#000', fontWeight: 600, flexShrink: 0 }}
                          >
                            Add
                          </button>
                        </div>
                        {((agent.inputs && agent.inputs.length > 0) || (agent.outputs && agent.outputs.length > 0)) && (
                          <div style={{ display: 'flex', gap: '16px', marginTop: '4px', fontSize: '11px', color: '#4b5563' }}>
                            {agent.inputs && agent.inputs.length > 0 && (
                              <div>
                                <strong style={{ color: '#000' }}>In:</strong> {agent.inputs.join(', ')}
                              </div>
                            )}
                            {agent.outputs && agent.outputs.length > 0 && (
                              <div>
                                <strong style={{ color: '#000' }}>Out:</strong> {agent.outputs.join(', ')}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: '#4b5563', marginBottom: '12px', fontWeight: 700 }}>Custom Agents</h4>
                  {customAgents.length === 0 ? (
                    <div style={{ fontSize: '13px', color: '#6b7280', padding: '16px', background: '#f9fafb', borderRadius: '8px', textAlign: 'center' }}>
                      No custom agents available.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {customAgents.map(agent => (
                        <div key={agent.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: '#f3f4f6', border: '1px solid #e5e7eb', borderRadius: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Bot size={16} color="#10b981" />
                            <span style={{ fontSize: '14px', fontWeight: 600, color: '#000' }}>{agent.name}</span>
                          </div>
                          <button 
                            onClick={() => addNodeToCanvas({...agent, type: 'custom'})}
                            style={{ background: '#fff', border: '1px solid #ccc', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', cursor: 'pointer', color: '#000', fontWeight: 600 }}
                          >
                            Add
                          </button>
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
