import axios from 'axios';

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const configService = {
  getICP: async () => (await api.get('/api/config/icp')).data,
  updateICP: async (data) => (await api.put('/api/config/icp', data)).data,
  getPersona: async () => (await api.get('/api/config/persona')).data,
  updatePersona: async (data) => (await api.put('/api/config/persona', data)).data,
  getThresholds: async () => (await api.get('/api/config/thresholds')).data,
  updateThresholds: async (data) => (await api.put('/api/config/thresholds', data)).data,
  resetConfig: async () => (await api.post('/api/config/reset')).data,
};

export const prospectsService = {
  getProspects: async (params) => (await api.get('/api/prospects', { params })).data,
  createProspect: async (data) => (await api.post('/api/prospects', data)).data,
  getProspectDetail: async (id) => (await api.get(`/api/prospects/${id}`)).data,
  deleteProspect: async (id) => (await api.delete(`/api/prospects/${id}`)).data,
  getProspectStreamUrl: (id) => `${API_URL}/api/prospects/${id}/stream`,
};

export const hitlService = {
  getPendingRequests: async () => (await api.get('/api/hitl/pending')).data,
  getRequestDetail: async (id) => (await api.get(`/api/hitl/${id}`)).data,
  approveRequest: async (id, corrections) => (await api.post(`/api/hitl/${id}/approve`, { corrections })).data,
  rejectRequest: async (id) => (await api.post(`/api/hitl/${id}/reject`)).data,
};

export const agentService = {
  getAgents: async () => (await api.get('/api/agents')).data,
  getCoreAgents: async () => (await api.get('/api/agents/core')).data,
  getTools: async () => (await api.get('/api/agents/tools')).data,
  createAgent: async (data) => (await api.post('/api/agents', data)).data,
  deleteAgent: async (id) => (await api.delete(`/api/agents/${id}`)).data,
  getAgentStreamUrl: (id) => `${API_URL}/api/agents/${id}/logs/stream`,
};

export const workflowService = {
  getWorkflows: async () => (await api.get('/api/workflows')).data,
  createWorkflow: async (data) => (await api.post('/api/workflows', data)).data,
  deleteWorkflow: async (id) => (await api.delete(`/api/workflows/${id}`)).data,
};

export const triggerService = {
  getSources: async () => (await api.get('/api/triggers/sources')).data,
  createSource: async (data) => (await api.post('/api/triggers/sources', data)).data,
  deleteSource: async (id) => (await api.delete(`/api/triggers/sources/${id}`)).data,
  start: async () => (await api.post('/api/triggers/start')).data,
  stop: async () => (await api.post('/api/triggers/stop')).data,
  getStatus: async () => (await api.get('/api/triggers/status')).data,
};

