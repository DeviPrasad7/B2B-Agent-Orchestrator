import React from 'react';

export function Card({ children, className = '', style = {} }) {
  return (
    <div className={`card ${className}`} style={style}>
      {children}
    </div>
  );
}

export function Button({ 
  children, 
  variant = 'secondary', 
  onClick, 
  disabled = false, 
  icon = null,
  className = '',
  style = {},
  type = 'button'
}) {
  return (
    <button 
      type={type}
      className={`btn btn-${variant} ${className}`} 
      onClick={onClick} 
      disabled={disabled}
      style={style}
    >
      {icon}
      {children}
    </button>
  );
}

export function Input({ 
  label, 
  value, 
  onChange, 
  type = 'text', 
  required = false, 
  placeholder = '',
  component = 'input',
  className = ''
}) {
  return (
    <div className={`input-group ${className}`}>
      {label && <label className="input-label">{label} {required && <span style={{color: 'var(--danger)'}}>*</span>}</label>}
      {component === 'textarea' ? (
        <textarea 
          className="input-field" 
          value={value} 
          onChange={onChange} 
          required={required} 
          placeholder={placeholder}
          rows={3}
        />
      ) : (
        <input 
          type={type} 
          className="input-field" 
          value={value} 
          onChange={onChange} 
          required={required} 
          placeholder={placeholder}
        />
      )}
    </div>
  );
}

export function Badge({ children, variant = 'neutral', className = '' }) {
  return (
    <span className={`badge badge-${variant} ${className}`}>
      {children}
    </span>
  );
}

export function PageHeader({ title, description, actions = null }) {
  return (
    <div className="page-header">
      <div>
        <h1 className="page-title">{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {actions && <div>{actions}</div>}
    </div>
  );
}

export function Modal({ isOpen, onClose, title, children, footer, icon = null }) {
  if (!isOpen) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            {icon && <span style={{ color: 'var(--primary-cyan)', display: 'flex', alignItems: 'center' }}>{icon}</span>}
            {title}
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>
        <div className="modal-body">
          {children}
        </div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}
