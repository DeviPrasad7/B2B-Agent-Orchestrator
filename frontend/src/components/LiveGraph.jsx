import React, { useMemo } from 'react';
import { ReactFlow, Background, Controls, Handle, Position } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Play, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';

const CustomGraphNode = ({ data }) => {
  let statusColor = '#4b5563'; // pending
  let bgColor = '#ffffff';
  let Icon = Play;

  if (data.status === 'completed') {
    statusColor = '#10b981'; // success
    bgColor = '#f0fdf4';
    Icon = CheckCircle2;
  } else if (data.status === 'running') {
    statusColor = '#3b82f6'; // running
    bgColor = '#eff6ff';
    Icon = Loader2;
  } else if (data.status === 'error') {
    statusColor = '#ef4444'; // error
    bgColor = '#fef2f2';
    Icon = AlertCircle;
  }

  return (
    <div style={{ 
      background: bgColor, 
      border: `2px solid ${statusColor}`, 
      borderRadius: '8px', 
      padding: '12px', 
      minWidth: '180px', 
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', 
      color: '#000000',
      display: 'flex',
      alignItems: 'center',
      gap: '12px'
    }}>
      <Handle type="target" position={Position.Top} style={{ visibility: 'hidden' }} />
      <div style={{ 
        width: '24px', 
        height: '24px', 
        borderRadius: '50%', 
        background: statusColor, 
        color: '#fff', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center' 
      }}>
        {data.status === 'running' ? (
          <Icon size={14} className="spin-animation" />
        ) : (
          <Icon size={14} />
        )}
      </div>
      <div>
        <div style={{ fontWeight: 600, fontSize: '13px' }}>{typeof data.label === 'object' ? JSON.stringify(data.label) : String(data.label)}</div>
        <div style={{ fontSize: '11px', color: '#6b7280', textTransform: 'uppercase' }}>{data.status}</div>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ visibility: 'hidden' }} />
    </div>
  );
};

const nodeTypes = {
  customGraphNode: CustomGraphNode,
};

export default function LiveGraph({ state }) {
  const { nodes, edges } = useMemo(() => {
    if (!state) return { nodes: [], edges: [] };

    const customWorkflow = state.custom_workflow_steps;
    
    // If it's a DAG workflow
    if (customWorkflow && typeof customWorkflow === 'object' && customWorkflow.nodes) {
      const executed = state.executed_agents || [];
      const dispatched = state.dispatched_agents || [];
      const errors = state.errors || [];
      
      const flowNodes = customWorkflow.nodes.map(n => {
        const agentName = n.data?.agentId || n.data?.label;
        
        let status = 'pending';
        if (errors.includes(agentName)) {
          status = 'error';
        } else if (executed.includes(agentName)) {
          status = 'completed';
        } else if (dispatched.includes(agentName)) {
          status = 'running';
        }

        return {
          id: n.id,
          type: 'customGraphNode',
          position: n.position || { x: 0, y: 0 },
          data: { label: n.data?.label || 'Node', status }
        };
      });

      return { nodes: flowNodes, edges: customWorkflow.edges || [] };
    }
    
    // Fallback for default linear execution (not a DAG custom workflow)
    const executed = state.executed_agents || [];
    const flowNodes = [];
    const flowEdges = [];
    
    let yPos = 50;
    executed.forEach((agent, idx) => {
      flowNodes.push({
        id: `node_${idx}`,
        type: 'customGraphNode',
        position: { x: 150, y: yPos },
        data: { label: agent, status: 'completed' }
      });
      if (idx > 0) {
        flowEdges.push({
          id: `edge_${idx-1}_${idx}`,
          source: `node_${idx-1}`,
          target: `node_${idx}`
        });
      }
      yPos += 100;
    });

    if (state.overall_status === 'PENDING' || state.overall_status === 'PROCESSING') {
      const nextAgents = Array.isArray(state.next_node) ? state.next_node : [state.next_node];
      nextAgents.forEach((agent, i) => {
        if (agent && agent !== '__end__') {
          const nodeId = `running_${i}`;
          flowNodes.push({
            id: nodeId,
            type: 'customGraphNode',
            position: { x: 150, y: yPos + (i * 100) },
            data: { label: agent, status: 'running' }
          });
          if (executed.length > 0) {
            flowEdges.push({
              id: `edge_last_${nodeId}`,
              source: `node_${executed.length-1}`,
              target: nodeId
            });
          }
        }
      });
    }

    return { nodes: flowNodes, edges: flowEdges };
  }, [state]);

  if (!nodes || nodes.length === 0) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6b7280' }}>
        No graph data available yet...
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', minHeight: '250px', border: '1px solid #e5e7eb', borderRadius: '8px', overflow: 'hidden' }}>
      <style>
        {`
          .spin-animation {
            animation: spin 1.5s linear infinite;
          }
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}
      </style>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background color="#ccc" gap={16} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
