import React, { useState, useEffect } from 'react';
import { triggerService } from '../services/api';
import { Card, Button, PageHeader, Input, Badge } from '../components/UI';
import { Play, Square, Plus, RadioTower, Rss, Globe2, Network } from 'lucide-react';

export default function Triggers() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({ type: 'rss', url: '', interval_seconds: 3600, enabled: true });
  const [submitting, setSubmitting] = useState(false);
  const [monitorActive, setMonitorActive] = useState(false); // Mock state

  const fetchSources = async () => {
    try {
      const data = await triggerService.getSources();
      setSources(data || []);
    } catch (error) {
      console.error('Failed to fetch triggers:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const handleStartMonitor = async () => {
    setMonitorActive(true);
  };

  const handleStopMonitor = async () => {
    setMonitorActive(false);
  };

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await triggerService.createSource(formData);
      setShowAddForm(false);
      setFormData({ type: 'rss', url: '', interval_seconds: 3600, enabled: true });
      fetchSources();
    } catch (error) {
      console.error('Failed to add trigger source:', error);
      alert('Failed to add trigger source.');
    } finally {
      setSubmitting(false);
    }
  };

  const getTypeIcon = (type) => {
    switch(type) {
      case 'rss': return <Rss size={14} />;
      case 'news_api': return <Globe2 size={14} />;
      default: return <RadioTower size={14} />;
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
      <PageHeader 
        title="Data Sources" 
        description="Configure automated telemetry sources for passive prospect discovery."
        actions={
          <div className="flex-row gap-4">
            {monitorActive ? (
              <Button variant="danger" icon={<Square size={16} />} onClick={handleStopMonitor}>
                Stop Scanners
              </Button>
            ) : (
              <Button variant="success" icon={<Play size={16} />} onClick={handleStartMonitor}>
                Start Scanners
              </Button>
            )}
            <Button icon={<Plus size={16} />} variant="primary" onClick={() => setShowAddForm(!showAddForm)}>
              {showAddForm ? 'Cancel' : 'Add Source'}
            </Button>
          </div>
        }
      />

      {showAddForm && (
        <Card style={{ borderLeft: '4px solid var(--primary-accent)', marginBottom: '32px', background: 'var(--bg-main)' }}>
          <div className="card-title" style={{ color: 'var(--text-primary)' }}><Network size={20} color="var(--primary-accent)" /> Add Data Source</div>
          <form onSubmit={handleAddSubmit} className="flex-col">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr', gap: '24px' }}>
              <div className="input-group">
                <label className="input-label">Source Type</label>
                <select 
                  className="input-field" 
                  value={formData.type}
                  onChange={(e) => setFormData({...formData, type: e.target.value})}
                  style={{ appearance: 'none', background: 'var(--bg-surface)' }}
                >
                  <option value="rss">RSS Feed</option>
                  <option value="news_api">News API</option>
                  <option value="job_board">Job Board</option>
                </select>
              </div>
              <Input 
                label="Target URL" 
                value={formData.url} 
                onChange={(e) => setFormData({...formData, url: e.target.value})} 
                required 
                placeholder="https://news.ycombinator.com/rss"
              />
              <Input 
                type="number"
                label="Polling Interval (Seconds)" 
                value={formData.interval_seconds} 
                onChange={(e) => setFormData({...formData, interval_seconds: parseInt(e.target.value)})} 
                required 
              />
            </div>
            <div className="flex-row justify-end mt-4" style={{ marginTop: '24px' }}>
              <Button type="submit" variant="primary" disabled={submitting || !formData.url}>
                {submitting ? 'Saving...' : 'Save Source'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div className="spinner"></div>
        ) : sources.length === 0 ? (
          <div className="text-center" style={{ padding: '80px 20px', color: 'var(--text-tertiary)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <RadioTower size={48} style={{ opacity: 0.2, margin: '0 auto 16px' }} />
            <p>No active data sources found.</p>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'var(--bg-main)', borderBottom: '1px solid var(--border-light)' }}>
                <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Protocol</th>
                <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Vector</th>
                <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Frequency</th>
                <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s, idx) => (
                <tr key={s.id || idx} style={{ borderBottom: '1px solid var(--border-light)' }}>
                  <td style={{ padding: '16px 24px' }}>
                    <Badge variant="neutral" style={{ background: 'var(--bg-surface)' }}>
                      {getTypeIcon(s.type)}
                      {s.type.toUpperCase()}
                    </Badge>
                  </td>
                  <td style={{ padding: '16px 24px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-primary)' }}>
                    {s.url}
                  </td>
                  <td style={{ padding: '16px 24px', color: 'var(--text-secondary)' }}>{s.interval_seconds}s</td>
                  <td style={{ padding: '16px 24px' }}>
                    {s.enabled ? <Badge variant="success">Active</Badge> : <Badge variant="danger">Disabled</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
