import React, { useState, useEffect } from 'react';
import { PageHeader, Button, Card, Badge, Modal, Input } from '../components/UI';
import { Plus, Cpu, Activity, Trash2 } from 'lucide-react';
import { agentService } from '../services/api';
import AgentLogsPanel from '../components/AgentLogsPanel';
import toast from 'react-hot-toast';

const CustomBot = () => (
  <div style={{ width: '100%', height: '160px', background: 'linear-gradient(135deg, #8b5cf615, #8b5cf605)', borderBottom: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
    <svg viewBox="0 0 100 100" width="60%" height="60%" className="bot-svg-float">
      <rect x="25" y="25" width="50" height="50" rx="10" fill="none" stroke="#8b5cf6" strokeWidth="3" strokeDasharray="10 5" className="bot-core-orbit"/>
      <circle cx="50" cy="50" r="12" fill="#8b5cf6" />
      <line x1="50" y1="50" x2="25" y2="25" stroke="#da7756" strokeWidth="2" className="bot-data-line" />
      <line x1="50" y1="50" x2="75" y2="75" stroke="#da7756" strokeWidth="2" className="bot-data-line" style={{ animationDelay: '0.4s' }}/>
    </svg>
  </div>
);

export default function CustomAgents() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '', system_prompt: '', allowed_tools: [] });
  const [availableTools, setAvailableTools] = useState([]);
  
  const [selectedAgent, setSelectedAgent] = useState(null);

  const fetchAgents = async () => {
    try {
      const data = await agentService.getAgents();
      const customAgents = (data || []).map(a => ({
        id: a.id,
        name: a.name,
        role: 'Custom Agent',
        description: a.description,
        tools: a.allowed_tools || [],
        icon: <Cpu size={12} style={{ marginRight: '4px' }}/>,
        visual: <CustomBot />,
        actionLabel: 'Inspect Logs',
        fullAgentRef: a
      }));
      setAgents(customAgents);
    } catch (error) {
      console.error('Failed to fetch custom agents:', error);
      toast.error('Failed to fetch custom agents');
    } finally {
      setLoading(false);
    }
  };

  const fetchTools = async () => {
    try {
      const tools = await agentService.getTools();
      setAvailableTools(tools || []);
      setFormData(prev => ({ ...prev, allowed_tools: tools || [] }));
    } catch (error) {
      console.error('Failed to fetch tools:', error);
    }
  };

  useEffect(() => {
    fetchAgents();
    fetchTools();
  }, []);

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await agentService.createAgent({
        ...formData
      });
      setShowAddForm(false);
      setFormData({ name: '', description: '', system_prompt: '', allowed_tools: availableTools });
      toast.success('Agent deployed successfully');
      fetchAgents();
    } catch (error) {
      console.error('Failed to create agent:', error);
      toast.error('Failed to create agent.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    toast((t) => (
      <div>
        <p style={{marginBottom: '12px', fontSize: '14px'}}>Are you sure you want to delete this agent?</p>
        <div style={{display: 'flex', gap: '8px'}}>
          <Button variant="danger" onClick={async () => {
            toast.dismiss(t.id);
            try {
              await agentService.deleteAgent(id);
              toast.success('Agent deleted');
              fetchAgents();
            } catch (error) {
              console.error('Failed to delete agent:', error);
              toast.error('Failed to delete agent');
            }
          }}>Delete</Button>
          <Button onClick={() => toast.dismiss(t.id)}>Cancel</Button>
        </div>
      </div>
    ), { duration: Infinity });
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', width: '100%', paddingBottom: '100px' }}>
      <PageHeader 
        title="Custom Agents Fleet" 
        description="Train, manage, and monitor your specialized domain agents."
        actions={
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setShowAddForm(true)}>
            Train New Agent
          </Button>
        }
      />

      <Modal 
        isOpen={showAddForm} 
        onClose={() => setShowAddForm(false)} 
        title="Train Custom Agent"
        icon={<Cpu size={20} />}
        style={{ maxWidth: '500px' }}
        footer={
          <>
            <Button onClick={() => setShowAddForm(false)}>Cancel</Button>
            <Button variant="primary" onClick={handleAddSubmit} disabled={submitting || !formData.name}>
              {submitting ? 'Initializing...' : 'Deploy Agent'}
            </Button>
          </>
        }
      >
        <form onSubmit={handleAddSubmit} className="flex-col">
          <Input 
            label="Agent Name" 
            value={formData.name} 
            onChange={(e) => setFormData({...formData, name: e.target.value})} 
            required 
            placeholder="e.g. Contract Analyzer"
          />
          <Input 
            label="Description" 
            value={formData.description} 
            onChange={(e) => setFormData({...formData, description: e.target.value})} 
            placeholder="What does this agent do?"
            required
          />
          <Input 
            component="textarea"
            label="System Prompt" 
            value={formData.system_prompt} 
            onChange={(e) => setFormData({...formData, system_prompt: e.target.value})} 
            placeholder="You are an expert at..."
            required
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Allowed Tools</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', background: 'var(--bg-main)', padding: '12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-light)' }}>
              {availableTools.map(tool => (
                <label key={tool} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={formData.allowed_tools.includes(tool)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFormData({ ...formData, allowed_tools: [...formData.allowed_tools, tool] });
                      } else {
                        setFormData({ ...formData, allowed_tools: formData.allowed_tools.filter(t => t !== tool) });
                      }
                    }}
                    style={{ accentColor: 'var(--primary-accent)' }}
                  />
                  {tool}
                </label>
              ))}
            </div>
          </div>
          <button type="submit" style={{ display: 'none' }}></button>
        </form>
      </Modal>

      {loading ? (
        <div className="spinner"></div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
          {agents.length === 0 && (
            <div style={{ gridColumn: '1 / -1', padding: '40px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
              No custom agents trained yet.
            </div>
          )}
          {agents.map((agent) => (
            <Card key={agent.id} style={{ padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {agent.visual}
              <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', flex: 1 }}>
                <div className="flex-row justify-between" style={{ marginBottom: '12px' }}>
                  <Badge variant="neutral">
                    {agent.icon} {agent.role}
                  </Badge>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--success)' }}>
                    <Activity size={14} /> Online
                  </div>
                </div>

                <h3 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px', fontFamily: '"Source Serif 4", serif' }}>
                  {agent.name}
                </h3>
                
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '20px', lineHeight: 1.6, flex: 1 }}>
                  {agent.description}
                </p>
                
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '24px' }}>
                  {agent.tools.map(tool => (
                    <span key={tool} style={{ fontSize: '11px', textTransform: 'uppercase', padding: '4px 10px', background: 'var(--bg-main)', border: '1px solid var(--border-light)', borderRadius: '100px', color: 'var(--text-tertiary)', fontWeight: 500, letterSpacing: '0.05em' }}>
                      {tool}
                    </span>
                  ))}
                </div>

                <div className="flex-row justify-between" style={{ gap: '12px', paddingTop: '16px', borderTop: '1px solid var(--border-light)' }}>
                  <Button variant="secondary" onClick={() => setSelectedAgent(agent.fullAgentRef)} style={{ flex: 1, justifyContent: 'center' }}>
                    {agent.actionLabel}
                  </Button>
                  <button onClick={() => handleDelete(agent.id)} style={{ padding: '8px', background: 'transparent', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)', color: 'var(--danger)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }} title="Delete Agent">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <AgentLogsPanel 
        agent={selectedAgent}
        isOpen={!!selectedAgent} 
        onClose={() => setSelectedAgent(null)} 
      />
    </div>
  );
}
