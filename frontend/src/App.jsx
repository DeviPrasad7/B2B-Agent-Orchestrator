import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, UserCheck, Settings, Activity, Bot, Database } from 'lucide-react';
import { Toaster } from 'react-hot-toast';
import './index.css';


const AgentHub = React.lazy(() => import('./pages/AgentHub'));
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const HITLQueue = React.lazy(() => import('./pages/HITLQueue'));
const Configuration = React.lazy(() => import('./pages/Configuration'));
const Triggers = React.lazy(() => import('./pages/Triggers'));
const ScraperSandbox = React.lazy(() => import('./pages/ScraperSandbox'));
const EnricherSandbox = React.lazy(() => import('./pages/EnricherSandbox'));
const CustomAgents = React.lazy(() => import('./pages/CustomAgents'));
const WorkflowStudio = React.lazy(() => import('./pages/WorkflowStudio'));

function FloatingDock() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Agents', icon: <Bot size={20} /> },
    { path: '/prospects', label: 'Pipeline', icon: <LayoutDashboard size={20} /> },
    { path: '/hitl', label: 'Review', icon: <UserCheck size={20} /> },
    { path: '/config', label: 'Config', icon: <Settings size={20} /> },
    { path: '/triggers', label: 'Lead Gen', icon: <Database size={20} /> },
  ];

  return (
    <div className="floating-dock-container">
      <nav className="floating-dock">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={`dock-item ${location.pathname === item.path ? 'active' : ''}`}
          >
            {item.icon}
            <span className="dock-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

function MainLayout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const showBack = location.pathname !== '/';
  
  return (
    <div className="app-container">
      <FloatingDock />
      <main className="main-content" style={{ position: 'relative' }}>
        {showBack && (
          <button 
            onClick={() => navigate(-1)} 
            style={{ position: 'absolute', top: '24px', left: '24px', background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', zIndex: 10 }}
            className="back-button"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
            Back
          </button>
        )}
        <Suspense fallback={<div className="spinner"></div>}>
          {children}
        </Suspense>
        <Toaster position="top-right" />
      </main>
    </div>
  );
}


export default function App() {
  return (
    <Router>
      <MainLayout>
        <Routes>
          <Route path="/" element={<AgentHub />} />
          <Route path="/prospects" element={<Dashboard />} />
          <Route path="/hitl" element={<HITLQueue />} />
          <Route path="/config" element={<Configuration />} />
          <Route path="/triggers" element={<Triggers />} />
          <Route path="/scraper-sandbox" element={<ScraperSandbox />} />
          <Route path="/enricher-sandbox" element={<EnricherSandbox />} />
          <Route path="/custom-agents" element={<CustomAgents />} />
          <Route path="/workflow-studio" element={<WorkflowStudio />} />
        </Routes>
      </MainLayout>
    </Router>
  );
}
