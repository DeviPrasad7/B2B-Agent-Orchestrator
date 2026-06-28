import React, { useState, useEffect } from 'react';
import { PageHeader, Button, Card, Badge, Modal, Input } from '../components/UI';
import { Plus, Zap, Activity, Cpu, Database, Search, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { agentService } from '../services/api';
import AgentLogsPanel from '../components/AgentLogsPanel';

const CoreBot = () => (
  <div style={{ width: '100%', height: '160px', background: 'linear-gradient(135deg, #da775615, #da775605)', borderBottom: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
    <svg viewBox="0 0 100 100" width="55%" height="55%" className="bot-svg-float">
      <circle cx="50" cy="50" r="35" fill="none" stroke="#da775644" strokeWidth="2" strokeDasharray="4 4" className="bot-core-orbit" />
      <circle cx="50" cy="50" r="18" fill="#da7756" className="bot-core-eye" />
      <circle cx="50" cy="50" r="6" fill="#fff" />
    </svg>
  </div>
);

const ScraperBot = () => (
  <div style={{ width: '100%', height: '160px', background: 'linear-gradient(135deg, #5c7c7315, #5c7c7305)', borderBottom: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
    <svg viewBox="0 0 100 100" width="65%" height="65%" className="bot-svg-float">
      <path d="M 20 60 Q 50 10 80 60" fill="none" stroke="#5c7c73" strokeWidth="5" strokeLinecap="round" />
      <circle cx="50" cy="50" r="8" fill="#5c7c73" />
      <line x1="50" y1="50" x2="50" y2="20" stroke="#5c7c73" strokeWidth="4" strokeLinecap="round" className="bot-radar-sweep" />
      <rect x="30" y="75" width="8" height="8" rx="2" fill="#da7756" className="bot-scraper-light" />
      <rect x="62" y="75" width="8" height="8" rx="2" fill="#5c7c73" className="bot-scraper-light" style={{ animationDelay: '0.5s' }} />
    </svg>
  </div>
);

const EnricherBot = () => (
  <div style={{ width: '100%', height: '160px', background: 'linear-gradient(135deg, #64748b15, #64748b05)', borderBottom: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
    <svg viewBox="0 0 100 100" width="65%" height="65%" className="bot-svg-float">
      <polygon points="50,15 85,45 70,85 30,85 15,45" fill="none" stroke="#64748b" strokeWidth="2" />
      <line x1="50" y1="15" x2="70" y2="85" stroke="#da7756" strokeWidth="3" className="bot-data-line" />
      <line x1="15" y1="45" x2="85" y2="45" stroke="#da7756" strokeWidth="3" className="bot-data-line" style={{ animationDelay: '0.3s' }} />
      <line x1="30" y1="85" x2="50" y2="15" stroke="#da7756" strokeWidth="3" className="bot-data-line" style={{ animationDelay: '0.6s' }} />
      <circle cx="50" cy="15" r="6" className="bot-enricher-node" />
      <circle cx="85" cy="45" r="6" className="bot-enricher-node" style={{ animationDelay: '0.4s' }} />
      <circle cx="70" cy="85" r="6" className="bot-enricher-node" style={{ animationDelay: '0.8s' }} />
      <circle cx="30" cy="85" r="6" className="bot-enricher-node" style={{ animationDelay: '1.2s' }} />
      <circle cx="15" cy="45" r="6" className="bot-enricher-node" style={{ animationDelay: '1.6s' }} />
    </svg>
  </div>
);

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

const coreAgents = [
  {
    id: 'core',
    name: 'Dynamic Orchestrator',
    role: 'System Core',
    description: 'The master workflow engine. Consumes target firmographics and intelligently coordinates specialized services via LLM routing.',
    tools: ['LangGraph Orchestration', 'Decision Matrix'],
    icon: <Zap size={12} style={{ marginRight: '4px' }}/>,
    visual: <CoreBot />,
    isCore: true,
    actionLabel: 'View Pipeline',
    actionRoute: '/prospects'
  },
  {
    id: 'scraper',
    name: 'Data Extraction Service',
    role: 'Extraction Engine',
    description: 'Autonomous crawler that scrapes target domains, parses metadata, and extracts unstructured text for deep processing.',
    tools: ['Web Scraper', 'DOM Parser'],
    icon: <Search size={12} style={{ marginRight: '4px' }}/>,
    visual: <ScraperBot />,
    isCore: true,
    actionLabel: 'Test Scraper',
    actionRoute: '/scraper-sandbox'
  },
  {
    id: 'enricher',
    name: 'Firmographic Enricher',
    role: 'Data Synthesizer',
    description: 'Correlates raw data against third-party APIs to verify employee counts, tech stacks, and revenue estimations.',
    tools: ['Clearbit API', 'Crunchbase API'],
    icon: <Database size={12} style={{ marginRight: '4px' }}/>,
    visual: <EnricherBot />,
    isCore: true,
    actionLabel: 'Test Enricher',
    actionRoute: '/enricher-sandbox'
  },
  {
    id: 'custom-fleet',
    name: 'Custom Agents Fleet',
    role: 'Specialized Agents',
    description: 'Manage and monitor all custom agents trained to perform domain-specific data retrieval and processing.',
    tools: ['Custom LLM Prompts', 'External APIs'],
    icon: <Cpu size={12} style={{ marginRight: '4px' }}/>,
    visual: <CustomBot />,
    isCore: true,
    actionLabel: 'Manage Custom Agents',
    actionRoute: '/custom-agents'
  },
  {
    id: 'workflow-studio',
    name: 'Workflow Studio',
    role: 'Orchestration Builder',
    description: 'Build, name, and use custom sequences of agents. Connect your custom agents into a tailored pipeline.',
    tools: ['Visual Builder', 'Pipeline Routing'],
    icon: <Database size={12} style={{ marginRight: '4px' }}/>,
    visual: <CoreBot />,
    isCore: true,
    actionLabel: 'Open Studio',
    actionRoute: '/workflow-studio'
  }
];

export default function AgentHub() {
  const navigate = useNavigate();
  const [agents] = useState(coreAgents);
  const [loading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', width: '100%', paddingBottom: '100px' }}>
      <PageHeader 
        title="Agent Directory" 
        description="Monitor and manage the autonomous agents executing tasks in your workspace."
      />

      {loading ? (
        <div className="spinner"></div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
          {agents.map((agent) => (
            <Card key={agent.id} style={{ padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {agent.visual}
              <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', flex: 1 }}>
                <div className="flex-row justify-between" style={{ marginBottom: '12px' }}>
                  <Badge variant={agent.id === 'core' ? 'warning' : 'neutral'} style={{ background: agent.id === 'core' ? '#fdfaf6' : 'var(--bg-main)', borderColor: agent.id === 'core' ? 'var(--primary-accent)' : 'var(--border-light)', color: agent.id === 'core' ? 'var(--primary-accent)' : 'var(--text-secondary)' }}>
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

                <div className="flex-row gap-2">
                  <Button 
                    variant={agent.isCore ? 'primary' : 'secondary'} 
                    onClick={() => {
                      if (agent.isCore) {
                        navigate(agent.actionRoute);
                      } else {
                        setSelectedAgent(agent.fullAgentRef);
                      }
                    }} 
                    style={{ flex: 1 }}
                  >
                    {agent.actionLabel}
                  </Button>
                  {!agent.isCore && (
                    <Button variant="danger" icon={<Trash2 size={16} />} onClick={() => handleDelete(agent.id)} />
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {selectedAgent && (
        <AgentLogsPanel 
          agent={selectedAgent} 
          onClose={() => setSelectedAgent(null)} 
        />
      )}
    </div>
  );
}
