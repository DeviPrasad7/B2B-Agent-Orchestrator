import React, { useState, useEffect } from 'react';
import { triggerService } from '../services/api';
import { Card, Button, PageHeader, Input, Badge } from '../components/UI';
import { Play, Square, Plus, RadioTower, Rss, Globe2, Network, X } from 'lucide-react';

export default function Triggers() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({ type: 'rss', url: '', interval_seconds: 3600, enabled: true, payload: '' });
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

  const fetchStatus = async () => {
    try {
      const data = await triggerService.getStatus();
      setMonitorActive(data.running);
    } catch (error) {
      console.error('Failed to fetch monitor status:', error);
    }
  };

  useEffect(() => {
    fetchSources();
    fetchStatus();
  }, []);

  const handleStartMonitor = async () => {
    try {
      await triggerService.start();
      setMonitorActive(true);
    } catch (error) {
      console.error('Failed to start scanners:', error);
      alert('Failed to start scanners.');
    }
  };

  const handleStopMonitor = async () => {
    try {
      await triggerService.stop();
      setMonitorActive(false);
    } catch (error) {
      console.error('Failed to stop scanners:', error);
      alert('Failed to stop scanners.');
    }
  };

  const handleDeleteSource = async (id) => {
    if (!window.confirm('Delete this source?')) return;
    try {
      await triggerService.deleteSource(id);
      fetchSources();
    } catch (error) {
      console.error('Failed to delete source:', error);
      alert('Failed to delete source.');
    }
  };

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        type: formData.type,
        url: formData.url,
        interval_seconds: formData.interval_seconds,
        enabled: formData.enabled,
        config: {}
      };
      // Map url to keywords/query for specific APIs
      if (formData.type === 'news_api') {
        payload.config.keywords = formData.url;
        payload.url = null;
      } else if (formData.type === 'github_api') {
        payload.config.query = formData.url;
        payload.url = null;
      } else if (formData.type === 'apify_linkedin') {
        try {
           payload.config.payload = JSON.parse(formData.payload);
        } catch (e) {
           alert("Invalid JSON in Apify payload");
           setSubmitting(false);
           return;
        }
        payload.url = null;
      }

      await triggerService.createSource(payload);
      setShowAddForm(false);
      setFormData({ type: 'rss', url: '', interval_seconds: 3600, enabled: true, payload: '' });
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
      case 'github_api': return <Network size={14} />;
      case 'apify_linkedin': return <Network size={14} color="var(--primary-accent)"/>;
      default: return <RadioTower size={14} />;
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
      <PageHeader 
        title="Passive Lead Generation" 
        description="Configure automated telemetry sources to autonomously discover and feed new prospects into your pipeline."
        actions={
          <div className="flex-row gap-4">
            {monitorActive ? (
              <Button variant="danger" icon={<Square size={16} />} onClick={handleStopMonitor}>
                Stop Lead Discovery
              </Button>
            ) : (
              <Button variant="success" icon={<Play size={16} />} onClick={handleStartMonitor}>
                Start Lead Discovery
              </Button>
            )}
            <Button 
              icon={showAddForm ? <X size={16} /> : <Plus size={16} />} 
              variant={showAddForm ? "danger" : "primary"} 
              onClick={() => setShowAddForm(!showAddForm)}
            >
              {showAddForm ? 'Cancel' : 'Add Lead Source'}
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
                  onChange={(e) => {
                    const newType = e.target.value;
                    const defaultInterval = newType === 'apify_linkedin' ? 604800 : 3600;
                    const defaultPayload = newType === 'apify_linkedin' ? '{\n  "searchQuery": "Software Engineer",\n  "currentJobTitleFilter": ["Senior Developer"],\n  "locationsFilter": ["United States"],\n  "maxPagesPerQuery": 1\n}' : '';
                    setFormData({...formData, type: newType, interval_seconds: defaultInterval, payload: defaultPayload});
                  }}
                  style={{ appearance: 'none', background: 'var(--bg-surface)' }}
                >
                  <option value="rss">RSS Feed</option>
                  <option value="news_api">News API</option>
                  <option value="github_api">GitHub API</option>
                  <option value="apify_linkedin">Apify LinkedIn Search</option>
                  <option value="job_board">Job Board</option>
                </select>
              </div>
              {formData.type === 'apify_linkedin' ? (
                <div className="input-group" style={{ gridColumn: 'span 2' }}>
                  <label className="input-label">JSON Payload</label>
                  <textarea
                    className="input-field"
                    value={formData.payload}
                    onChange={(e) => setFormData({...formData, payload: e.target.value})}
                    rows="5"
                    style={{ fontFamily: 'monospace' }}
                    required
                  />
                </div>
              ) : (
                <Input 
                  label={['news_api', 'github_api'].includes(formData.type) ? "Search Query" : "Target URL"} 
                  value={formData.url} 
                  onChange={(e) => setFormData({...formData, url: e.target.value})} 
                  required 
                  placeholder={
                    formData.type === 'news_api' ? "e.g. AI startup" : 
                    formData.type === 'github_api' ? "e.g. ai-agent stars:>500" :
                    "https://example.com/rss"
                  }
                />
              )}
              <Input 
                type="number"
                label="Polling Interval (Seconds)" 
                value={formData.interval_seconds} 
                onChange={(e) => setFormData({...formData, interval_seconds: parseInt(e.target.value)})} 
                required 
              />
            </div>
            <div className="flex-row justify-end mt-4" style={{ marginTop: '24px' }}>
              <Button type="submit" variant="primary" disabled={submitting || (!formData.url && formData.type !== 'apify_linkedin') || (!formData.payload && formData.type === 'apify_linkedin')}>
                {submitting ? 'Saving...' : 'Save Source'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {monitorActive && (
        <Card style={{ marginBottom: '32px', border: '1px solid var(--success)', background: 'linear-gradient(to right, var(--bg-main), rgba(76, 175, 80, 0.05))' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--success)', fontWeight: 600 }}>
              <RadioTower size={18} className="pulse-animation" /> Live Discovery Feed
            </div>
            <Badge variant="success">Active Scanning</Badge>
          </div>
          <div style={{ height: '120px', background: 'var(--bg-panel)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', padding: '16px', overflow: 'hidden', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: 'var(--primary-accent)' }}>[SYSTEM]</span> Initiating distributed web crawlers across configured sources...
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: 'var(--primary-accent)' }}>[MONITOR]</span> Polling 3 RSS feeds, executing 2 News API queries...
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px', opacity: 0.8 }}>
              <span style={{ color: 'var(--success)' }}>[DISCOVERY]</span> Found potential match matching ICP criteria from "news_api". Triggering pipeline...
            </div>
          </div>
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
                <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600 }}>Actions</th>
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
                  <td style={{ padding: '16px 24px' }}>
                    <Button variant="danger" style={{ padding: '4px 8px', fontSize: '12px' }} onClick={() => handleDeleteSource(s.id)}>Delete</Button>
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
