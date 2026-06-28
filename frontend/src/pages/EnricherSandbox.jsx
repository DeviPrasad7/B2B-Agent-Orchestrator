import React, { useState } from 'react';
import { PageHeader, Card, Button, Input, Badge } from '../components/UI';
import { Database, CheckCircle, Loader } from 'lucide-react';

export default function EnricherSandbox() {
  const [company, setCompany] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleEnrich = (e) => {
    e.preventDefault();
    if (!company) return;
    setLoading(true);
    setResult(null);

    // Mock enrichment sequence
    setTimeout(() => {
      setResult({
        name: company || 'Example Corp',
        employeeCount: 450,
        revenue: '$50M - $100M',
        techStack: ['React', 'Python', 'AWS', 'Docker'],
        status: 'Correlated (Clearbit + Crunchbase)'
      });
      setLoading(false);
    }, 2000);
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
      <PageHeader 
        title="Enricher Sandbox" 
        description="Test the Firmographic Enricher against simulated third-party APIs."
      />

      <Card style={{ marginBottom: '32px' }}>
        <form onSubmit={handleEnrich} style={{ display: 'flex', gap: '16px', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <Input 
              label="Company Name" 
              value={company} 
              onChange={e => setCompany(e.target.value)} 
              placeholder="e.g. Acme Corp" 
              required 
            />
          </div>
          <Button type="submit" variant="primary" icon={loading ? <Loader className="spin" size={16}/> : <Database size={16}/>} disabled={loading}>
            {loading ? 'Correlating...' : 'Enrich Data'}
          </Button>
        </form>
      </Card>

      {loading && (
        <Card style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px', color: 'var(--text-secondary)' }}>
          <div className="flex-col" style={{ alignItems: 'center', gap: '16px' }}>
            <div className="spinner"></div>
            <p>Querying Clearbit & Crunchbase... correlating firmographics...</p>
          </div>
        </Card>
      )}

      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
          <Card>
            <div className="flex-row justify-between" style={{ marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Database size={20} color="#0288d1" /> Firmographic Vector
              </h3>
              <Badge variant="success"><CheckCircle size={14} style={{ marginRight: '4px' }}/> {result.status}</Badge>
            </div>
            
            <div style={{ background: 'var(--bg-main)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-light)' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div>
                  <strong style={{ display: 'block', fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Company Name</strong>
                  <div style={{ fontSize: '16px', color: 'var(--text-primary)', fontWeight: 600 }}>{result.name}</div>
                </div>
                <div>
                  <strong style={{ display: 'block', fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Estimated Revenue</strong>
                  <div style={{ fontSize: '16px', color: 'var(--success)' }}>{result.revenue}</div>
                </div>
                <div>
                  <strong style={{ display: 'block', fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Verified Headcount</strong>
                  <div style={{ fontSize: '16px', color: 'var(--text-primary)' }}>{result.employeeCount}</div>
                </div>
                <div>
                  <strong style={{ display: 'block', fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Tech Stack Signatures</strong>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
                    {result.techStack.map(tech => (
                      <Badge key={tech} variant="neutral" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border-light)' }}>{tech}</Badge>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
