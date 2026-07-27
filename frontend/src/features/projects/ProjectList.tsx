import React from 'react';

interface Project {
  id: number;
  name: string;
  client: string;
  year: number;
  status: 'Active' | 'Completed' | 'Review' | 'On Hold';
}

const mockProjects: Project[] = [
  { id: 1, name: 'Acme Corp FY2025 Audit', client: 'Acme Corporation', year: 2025, status: 'Active' },
  { id: 2, name: 'Beta LLC Q4 Review', client: 'Beta LLC', year: 2024, status: 'Review' },
  { id: 3, name: 'Gamma Industries Compliance', client: 'Gamma Industries', year: 2025, status: 'Active' },
  { id: 4, name: 'Delta Partners Due Diligence', client: 'Delta Partners AG', year: 2024, status: 'Completed' },
  { id: 5, name: 'Epsilon Group Risk Assessment', client: 'Epsilon Group Ltd', year: 2025, status: 'On Hold' },
];

const statusColors: Record<Project['status'], { bg: string; text: string }> = {
  Active: { bg: '#dbeafe', text: '#1e40af' },
  Completed: { bg: '#d1fae5', text: '#065f46' },
  Review: { bg: '#fef3c7', text: '#92400e' },
  'On Hold': { bg: '#f3f4f6', text: '#6b7280' },
};

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: 14,
};

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '12px 16px',
  borderBottom: '2px solid #e5e7eb',
  color: '#6b7280',
  fontWeight: 600,
  fontSize: 12,
  textTransform: 'uppercase',
  letterSpacing: 0.5,
};

const tdStyle: React.CSSProperties = {
  padding: '14px 16px',
  borderBottom: '1px solid #f3f4f6',
  color: '#1f2937',
};

const ProjectList: React.FC = () => {
  return (
    <div
      style={{
        padding: '32px 40px',
        fontFamily: "'Segoe UI', Roboto, Arial, sans-serif",
        background: '#f3f4f6',
        minHeight: '100vh',
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111827' }}>Projects</h1>
        <p style={{ margin: '4px 0 0', fontSize: 14, color: '#6b7280' }}>
          Manage and review audit engagements
        </p>
      </div>

      {/* Table */}
      <div
        style={{
          background: '#fff',
          borderRadius: 10,
          border: '1px solid #e9ecef',
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          overflow: 'hidden',
        }}
      >
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Client</th>
              <th style={thStyle}>Year</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {mockProjects.map((p) => {
              const sc = statusColors[p.status];
              return (
                <tr key={p.id}>
                  <td style={tdStyle}>{p.name}</td>
                  <td style={{ ...tdStyle, color: '#6b7280' }}>{p.client}</td>
                  <td style={tdStyle}>{p.year}</td>
                  <td style={tdStyle}>
                    <span
                      style={{
                        display: 'inline-block',
                        padding: '2px 10px',
                        borderRadius: 12,
                        fontSize: 12,
                        fontWeight: 600,
                        background: sc.bg,
                        color: sc.text,
                      }}
                    >
                      {p.status}
                    </span>
                  </td>
                  <td style={tdStyle}>
                    <button
                      style={{
                        padding: '4px 12px',
                        fontSize: 12,
                        fontWeight: 600,
                        color: '#2563eb',
                        background: '#eff6ff',
                        border: '1px solid #bfdbfe',
                        borderRadius: 6,
                        cursor: 'pointer',
                      }}
                    >
                      View
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ProjectList;
