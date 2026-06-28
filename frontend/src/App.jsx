import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, UserCheck, Settings, Activity, Bot, Database } from 'lucide-react';
import './index.css';

const AgentHub = React.lazy(() => import('./pages/AgentHub'));
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const HITLQueue = React.lazy(() => import('./pages/HITLQueue'));
const Configuration = React.lazy(() => import('./pages/Configuration'));
const Triggers = React.lazy(() => import('./pages/Triggers'));

function FloatingDock() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Agents', icon: <Bot size={20} /> },
    { path: '/prospects', label: 'Pipeline', icon: <LayoutDashboard size={20} /> },
    { path: '/hitl', label: 'Review', icon: <UserCheck size={20} /> },
    { path: '/config', label: 'Config', icon: <Settings size={20} /> },
    { path: '/triggers', label: 'Sources', icon: <Database size={20} /> },
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
  return (
    <div className="app-container">
      <FloatingDock />
      <main className="main-content">
        <Suspense fallback={<div className="spinner"></div>}>
          {children}
        </Suspense>
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
        </Routes>
      </MainLayout>
    </Router>
  );
}
