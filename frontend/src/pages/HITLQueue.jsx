import React, { useState, useEffect } from 'react';
import { hitlService } from '../services/api';
import { PageHeader, Card, Button, Badge, Input, Modal } from '../components/UI';
import { UserCheck, Check, X, AlertCircle, FileSearch, Bug } from 'lucide-react';

export default function HITLQueue() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null);
  
  // Side-by-side review state
  const [activeReview, setActiveReview] = useState(null);
  const [corrections, setCorrections] = useState({});

  const fetchRequests = async () => {
    try {
      const data = await hitlService.getPendingRequests();
      setRequests(data || []);
    } catch (error) {
      console.error('Failed to fetch HITL requests:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
    const interval = setInterval(fetchRequests, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (id, action) => {
    setProcessingId(id);
    try {
      if (action === 'approve') {
        const payload = Object.keys(corrections).length > 0 ? corrections : null;
        await hitlService.approveRequest(id, payload);
      } else {
        await hitlService.rejectRequest(id);
      }
      setRequests((prev) => prev.filter(req => req.id !== id));
      setActiveReview(null);
      setCorrections({});
    } catch (error) {
      console.error(`Failed to ${action} request:`, error);
      alert(`Failed to ${action} request.`);
    } finally {
      setProcessingId(null);
    }
  };

  const openReview = (req) => {
    setActiveReview(req);
    const aiData = req.state_json?.data || {};
    setCorrections({ 
      company_name: aiData.company_name || req.company_name || '', 
      website: aiData.website || '' 
    });
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', width: '100%' }}>
      <PageHeader 
        title="Human Review Queue" 
        description="Review anomalies and edge cases flagged by the autonomous system."
      />

      {loading ? (
        <div className="spinner"></div>
      ) : requests.length === 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '400px', border: '1px dashed var(--border-light)', borderRadius: 'var(--radius-lg)' }}>
          <Check size={48} color="var(--success)" style={{ opacity: 0.5, marginBottom: '16px' }} />
          <h3 style={{ fontSize: '20px', color: 'var(--text-primary)', marginBottom: '8px', fontFamily: '"Source Serif 4", serif' }}>All Clear</h3>
          <p style={{ color: 'var(--text-secondary)' }}>No pending anomalies detected. The system is operating autonomously.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '24px' }}>
          {requests.map((req) => (
            <Card key={req.id} style={{ display: 'flex', flexDirection: 'column' }}>
              <div className="flex-row justify-between" style={{ marginBottom: '16px' }}>
                <Badge variant="warning"><AlertCircle size={12} /> Low Confidence</Badge>
                <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>{new Date(req.created_at).toLocaleTimeString()}</span>
              </div>
              
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px', fontFamily: '"Source Serif 4", serif' }}>
                {req.company_name || `Target: ${req.prospect_id.split('-')[0]}`}
              </h3>
              
              <div style={{ padding: '12px', background: '#fdf5eb', borderLeft: '3px solid var(--warning)', borderRadius: '0 4px 4px 0', fontSize: '13px', color: '#b25000', marginBottom: '24px', flex: 1 }}>
                {req.summary || 'The agent could not confidently verify the firmographic data against the ICP.'}
              </div>

              <Button variant="secondary" icon={<FileSearch size={16} />} onClick={() => openReview(req)} style={{ width: '100%' }}>
                Review Document
              </Button>
            </Card>
          ))}
        </div>
      )}

      <Modal
        isOpen={!!activeReview}
        onClose={() => setActiveReview(null)}
        title="Document Review & Correction"
        icon={<UserCheck size={20} />}
        footer={
          <>
            <Button variant="danger" icon={<X size={16} />} onClick={() => handleAction(activeReview.id, 'reject')} disabled={!!processingId}>
              Reject
            </Button>
            <Button variant="success" icon={<Check size={16} />} onClick={() => handleAction(activeReview.id, 'approve')} disabled={!!processingId}>
              Apply & Approve
            </Button>
          </>
        }
      >
        {activeReview && (
          <div className="diff-container" style={{ margin: '-24px', border: 'none', borderRadius: 0, borderBottom: '1px solid var(--border-light)' }}>
            
            {/* Left Side: AI Findings */}
            <div className="diff-half">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', color: 'var(--danger)', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                <Bug size={16} /> AI Findings
              </h3>
              
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                <strong>Flagged Issue:</strong> {activeReview.summary}
              </div>

              <div className="terminal-window" style={{ background: '#ffffff', border: '1px solid #f7c5c5' }}>
                <div className="terminal-body" style={{ padding: '16px', fontSize: '12px', color: '#b71c1c' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(activeReview.state_json?.data || { error: "No data payload attached" }, null, 2)}
                  </pre>
                </div>
              </div>
            </div>

            {/* Right Side: Human Override */}
            <div className="diff-half">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', color: 'var(--success)', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                <UserCheck size={16} /> Human Correction
              </h3>
              
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
                Provide the correct values to resolve the anomaly and continue the workflow.
              </p>

              <div className="flex-col">
                <Input 
                  label="Company Name"
                  value={corrections.company_name || ''}
                  onChange={(e) => setCorrections({...corrections, company_name: e.target.value})}
                />
                <Input 
                  label="Website URL"
                  value={corrections.website || ''}
                  onChange={(e) => setCorrections({...corrections, website: e.target.value})}
                />
                <Input 
                  label="Estimated Revenue"
                  value={corrections.revenue || ''}
                  onChange={(e) => setCorrections({...corrections, revenue: e.target.value})}
                />
                <Input 
                  label="Verified Industry"
                  value={corrections.industry || ''}
                  onChange={(e) => setCorrections({...corrections, industry: e.target.value})}
                />
              </div>
            </div>

          </div>
        )}
      </Modal>
    </div>
  );
}
