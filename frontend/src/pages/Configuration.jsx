import React, { useState, useEffect } from 'react';
import { configService } from '../services/api';
import { Card, Button, PageHeader, Input } from '../components/UI';
import { Save, RefreshCw, Layers, Users, Sliders, ShieldAlert } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Configuration() {
  const [icp, setIcp] = useState({ industries: [], tech_stack: [] });
  const [persona, setPersona] = useState({ job_titles: [] });
  const [thresholds, setThresholds] = useState({ min_confidence_score: 50, hitl_confidence_threshold: 70 });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchConfig = async () => {
    try {
      const [icpData, personaData, thresholdsData] = await Promise.all([
        configService.getICP(),
        configService.getPersona(),
        configService.getThresholds()
      ]);
      setIcp(icpData || { industries: [], tech_stack: [] });
      setPersona(personaData || { job_titles: [] });
      setThresholds(thresholdsData || { min_confidence_score: 50, hitl_confidence_threshold: 70 });
    } catch (error) {
      console.error('Failed to fetch configuration:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await Promise.all([
        configService.updateICP(icp),
        configService.updatePersona(persona),
        configService.updateThresholds(thresholds)
      ]);
      toast.success('Configuration deployed successfully!');
    } catch (error) {
      console.error('Failed to save config:', error);
      alert('Failed to save configuration.');
    } finally {
      setSaving(false);
    }
  };

  const handleArrayChange = (setter, state, field, value) => {
    const arr = value.split(',').map(item => item.trim());
    setter({ ...state, [field]: arr });
  };

  if (loading) return <div className="spinner"></div>;

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', width: '100%', paddingBottom: '100px' }}>
      <PageHeader 
        title="System Parameters" 
        description="Fine-tune the heuristics and thresholds for your autonomous agents."
        actions={
          <div className="flex-row gap-4">
            <Button variant="secondary" icon={<RefreshCw size={16} />} onClick={fetchConfig}>
              Reset Values
            </Button>
            <Button 
              variant="primary" 
              icon={<Save size={16} />} 
              onClick={handleSave} 
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Deploy Updates'}
            </Button>
          </div>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '32px', marginTop: '32px' }}>
        
        {/* ICP Section */}
        <Card>
          <div style={{ marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid var(--border-light)' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', fontFamily: '"Source Serif 4", serif' }}>
              <Layers size={18} color="var(--primary-accent)" /> Target Firmographics
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              Define the attributes the agent should lock onto during organizational scans.
            </p>
          </div>
          <div className="flex-col" style={{ gap: '16px' }}>
            <Input 
              label="Target Industries (comma separated)"
              value={(icp.industries || []).join(', ')}
              onChange={(e) => handleArrayChange(setIcp, icp, 'industries', e.target.value)}
            />
            <Input 
              component="textarea"
              label="Tech Stack Constraints"
              value={(icp.tech_stack || []).join(', ')}
              onChange={(e) => handleArrayChange(setIcp, icp, 'tech_stack', e.target.value)}
            />
          </div>
        </Card>

        {/* Personas Section */}
        <Card>
          <div style={{ marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid var(--border-light)' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', fontFamily: '"Source Serif 4", serif' }}>
              <Users size={18} color="var(--primary-accent)" /> Persona Vectors
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              Identify the key decision-makers the agent must extract during reconnaissance.
            </p>
          </div>
          <Input 
            component="textarea"
            label="Target Titles (comma separated)"
            value={(persona.job_titles || []).join(', ')}
            onChange={(e) => handleArrayChange(setPersona, persona, 'job_titles', e.target.value)}
          />
        </Card>

        {/* Thresholds Section */}
        <Card>
          <div style={{ marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid var(--border-light)' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', fontFamily: '"Source Serif 4", serif' }}>
              <Sliders size={18} color="var(--primary-accent)" /> Execution Thresholds
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              Calibrate the AI's confidence bounds. Determines when the agent requires human intervention.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <Input 
              type="number"
              label={"Minimum Viable Confidence\u00A0(%)"}
              value={thresholds.min_confidence_score || 50}
              onChange={(e) => setThresholds({...thresholds, min_confidence_score: parseFloat(e.target.value)})}
            />
            <Input 
              type="number"
              label={"Human Review Threshold\u00A0(%)"}
              value={thresholds.hitl_confidence_threshold || 70}
              onChange={(e) => setThresholds({...thresholds, hitl_confidence_threshold: parseFloat(e.target.value)})}
            />
          </div>
          <div style={{ padding: '16px', background: '#fdf5eb', borderRadius: 'var(--radius-sm)', fontSize: '13px', color: 'var(--text-secondary)', marginTop: '24px', border: '1px solid #f7dec0' }}>
            <strong style={{ color: 'var(--warning)', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '8px' }}>
              <ShieldAlert size={14}/> Threshold Logic
            </strong>
            <ul style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <li>&lt; <strong>{thresholds.min_confidence_score}%</strong>: Target automatically rejected.</li>
              <li><strong>{thresholds.min_confidence_score}% - {thresholds.hitl_confidence_threshold}%</strong>: Escalated to Human Review Queue.</li>
              <li>&gt; <strong>{thresholds.hitl_confidence_threshold}%</strong>: Autonomous approval granted.</li>
            </ul>
          </div>
        </Card>

      </div>

    </div>
  );
}
