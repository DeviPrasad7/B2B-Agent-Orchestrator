import React, { useState } from 'react';
import { PageHeader, Card, Button, Input, Badge } from '../components/UI';
import { Search, Code, CheckCircle, Loader } from 'lucide-react';

export default function ScraperSandbox() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleScrape = (e) => {
    e.preventDefault();
    if (!url) return;
    setLoading(true);
    setResult(null);

    // Mock scraping sequence
    setTimeout(() => {
      setResult({
        title: 'Example Corp - Enterprise AI Solutions',
        metaDescription: 'Leading provider of enterprise AI agents and automated workflows.',
        extractedLinks: 42,
        keyText: 'We build autonomous systems for B2B scale...',
        status: 'Success'
      });
      setLoading(false);
    }, 2000);
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
      <PageHeader 
        title="Scraper Sandbox" 
        description="Test the Data Extraction Service on any target URL in real-time."
      />

      <Card style={{ marginBottom: '32px' }}>
        <form onSubmit={handleScrape} style={{ display: 'flex', gap: '16px', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <Input 
              label="Target Domain" 
              value={url} 
              onChange={e => setUrl(e.target.value)} 
              placeholder="https://example.com" 
              required 
            />
          </div>
          <Button type="submit" variant="primary" icon={loading ? <Loader className="spin" size={16}/> : <Search size={16}/>} disabled={loading}>
            {loading ? 'Scraping...' : 'Extract Data'}
          </Button>
        </form>
      </Card>

      {loading && (
        <Card style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px', color: 'var(--text-secondary)' }}>
          <div className="flex-col" style={{ alignItems: 'center', gap: '16px' }}>
            <div className="spinner"></div>
            <p>Initializing headless browser... parsing DOM...</p>
          </div>
        </Card>
      )}

      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
          <Card>
            <div className="flex-row justify-between" style={{ marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Code size={20} color="var(--primary-accent)" /> Extracted Payload
              </h3>
              <Badge variant="success"><CheckCircle size={14} style={{ marginRight: '4px' }}/> {result.status}</Badge>
            </div>
            
            <div style={{ background: 'var(--bg-main)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-light)' }}>
              <div style={{ marginBottom: '12px' }}>
                <strong style={{ display: 'block', fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Page Title</strong>
                <div style={{ fontSize: '14px', color: 'var(--text-primary)' }}>{result.title}</div>
              </div>
              <div style={{ marginBottom: '12px' }}>
                <strong style={{ display: 'block', fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Meta Description</strong>
                <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>{result.metaDescription}</div>
              </div>
              <div style={{ marginBottom: '12px' }}>
                <strong style={{ display: 'block', fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Links Discovered</strong>
                <div style={{ fontSize: '14px', color: 'var(--text-primary)' }}>{result.extractedLinks} internal URLs</div>
              </div>
              <div>
                <strong style={{ display: 'block', fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>Raw Text Snippet</strong>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', background: 'var(--bg-panel)', padding: '12px', borderRadius: '4px', fontFamily: 'monospace', marginTop: '8px' }}>
                  {result.keyText}
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
