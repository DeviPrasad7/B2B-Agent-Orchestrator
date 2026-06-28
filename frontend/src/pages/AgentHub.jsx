import React from 'react';
import { PageHeader, Button, Card, Badge } from '../components/UI';
import { Plus, Zap, Activity, Cpu, Database, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

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
      {/* Radar dish */}
      <path d="M 20 60 Q 50 10 80 60" fill="none" stroke="#5c7c73" strokeWidth="5" strokeLinecap="round" />
      <circle cx="50" cy="50" r="8" fill="#5c7c73" />
      <line x1="50" y1="50" x2="50" y2="20" stroke="#5c7c73" strokeWidth="4" strokeLinecap="round" className="bot-radar-sweep" />
      {/* Lights */}
      <rect x="30" y="75" width="8" height="8" rx="2" fill="#da7756" className="bot-scraper-light" />
      <rect x="62" y="75" width="8" height="8" rx="2" fill="#5c7c73" className="bot-scraper-light" style={{ animationDelay: '0.5s' }} />
    </svg>
  </div>
);

const EnricherBot = () => (
  <div style={{ width: '100%', height: '160px', background: 'linear-gradient(135deg, #64748b15, #64748b05)', borderBottom: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
    <svg viewBox="0 0 100 100" width="65%" height="65%" className="bot-svg-float">
      {/* Neural nodes base */}
      <polygon points="50,15 85,45 70,85 30,85 15,45" fill="none" stroke="#64748b" strokeWidth="2" />
      
      {/* Animated Data lines */}
      <line x1="50" y1="15" x2="70" y2="85" stroke="#da7756" strokeWidth="3" className="bot-data-line" />
      <line x1="15" y1="45" x2="85" y2="45" stroke="#da7756" strokeWidth="3" className="bot-data-line" style={{ animationDelay: '0.3s' }} />
      <line x1="30" y1="85" x2="50" y2="15" stroke="#da7756" strokeWidth="3" className="bot-data-line" style={{ animationDelay: '0.6s' }} />
      
      {/* Glowing nodes */}
      <circle cx="50" cy="15" r="6" className="bot-enricher-node" />
      <circle cx="85" cy="45" r="6" className="bot-enricher-node" style={{ animationDelay: '0.4s' }} />
      <circle cx="70" cy="85" r="6" className="bot-enricher-node" style={{ animationDelay: '0.8s' }} />
      <circle cx="30" cy="85" r="6" className="bot-enricher-node" style={{ animationDelay: '1.2s' }} />
      <circle cx="15" cy="45" r="6" className="bot-enricher-node" style={{ animationDelay: '1.6s' }} />
    </svg>
  </div>
);

export default function AgentHub() {
  const navigate = useNavigate();

  const agents = [
    {
      id: 'core',
      name: 'Primary ICP Evaluator',
      role: 'System Core',
      description: 'The master orchestrator. Consumes target firmographics and coordinates sub-agents to perform full LangGraph analysis.',
      tools: ['Orchestration', 'Validation', 'Decision Matrix'],
      icon: <Zap size={12} style={{ marginRight: '4px' }}/>,
      visual: <CoreBot />
    },
    {
      id: 'scraper',
      name: 'Reconnaissance Drone',
      role: 'Extraction Agent',
      description: 'Autonomous crawler that scrapes target domains, reads site metadata, and extracts raw unstructured text for processing.',
      tools: ['Web Scraper', 'DOM Parser', 'Metadata Extractor'],
      icon: <Search size={12} style={{ marginRight: '4px' }}/>,
      visual: <ScraperBot />
    },
    {
      id: 'enricher',
      name: 'Firmographic Enricher',
      role: 'Data Synthesizer',
      description: 'Correlates raw scraped data against third-party APIs to verify employee counts, tech stacks, and revenue estimations.',
      tools: ['Clearbit API', 'Crunchbase API', 'LinkedIn Filter'],
      icon: <Database size={12} style={{ marginRight: '4px' }}/>,
      visual: <EnricherBot />
    }
  ];

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', width: '100%', paddingBottom: '100px' }}>
      <PageHeader 
        title="Agent Directory" 
        description="Monitor and manage the autonomous agents executing tasks in your workspace."
        actions={
          <Button variant="primary" icon={<Plus size={16} />}>
            Train New Agent
          </Button>
        }
      />

      {/* Grid of Vertical Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
        
        {agents.map((agent) => (
          <Card key={agent.id} style={{ padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            
            {/* Top Visual Half */}
            {agent.visual}

            {/* Bottom Text Half */}
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

              <Button variant={agent.id === 'core' ? 'primary' : 'secondary'} onClick={() => navigate('/prospects')} style={{ width: '100%' }}>
                {agent.id === 'core' ? 'View Active Pipeline' : 'Inspect Agent Logs'}
              </Button>
            </div>
          </Card>
        ))}

      </div>
    </div>
  );
}
