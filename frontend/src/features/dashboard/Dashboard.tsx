import React from 'react';

interface KpiCardProps {
  title: string;
  value: string;
  change: string;
  color: string;
}

const KpiCard: React.FC<KpiCardProps> = ({ title, value, change, color }) => (
  <div
    style={{
      background: '#fff',
      borderRadius: 10,
      padding: '20px 24px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      border: '1px solid #e9ecef',
      flex: '1 1 200px',
      minWidth: 180,
    }}
  >
    <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 8 }}>{title}</div>
    <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
    <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>{change}</div>
  </div>
);

interface Activity {
  id: number;
  action: string;
  project: string;
  time: string;
}

const mockActivities: Activity[] = [
  { id: 1, action: 'Document uploaded', project: 'Acme Corp FY2025', time: '2 min ago' },
  { id: 2, action: 'Risk assessment completed', project: 'Beta LLC Q4 Audit', time: '18 min ago' },
  { id: 3, action: 'Review requested', project: 'Gamma Industries', time: '1 hr ago' },
  { id: 4, action: 'Workflow approved', project: 'Delta Partners', time: '3 hr ago' },
  { id: 5, action: 'New project created', project: 'Epsilon Group', time: '5 hr ago' },
];

interface Approval {
  id: number;
  name: string;
  project: string;
  status: 'Pending' | 'Approved' | 'Rejected';
}

const mockApprovals: Approval[] = [
  { id: 1, name: 'Risk report review', project: 'Acme Corp FY2025', status: 'Pending' },
  { id: 2, name: 'Control testing sign-off', project: 'Beta LLC Q4 Audit', status: 'Pending' },
  { id: 3, name: 'Final clearance', project: 'Gamma Industries', status: 'Pending' },
];

const Dashboard: React.FC = () => {
  const kpis = [
    { title: 'Active Projects', value: '24', change: '+3 this quarter', color: '#2563eb' },
    { title: 'Documents Processed', value: '1,482', change: '+127 this week', color: '#059669' },
    { title: 'Risks Detected', value: '37', change: '5 critical', color: '#dc2626' },
    { title: 'Pending Reviews', value: '12', change: '8 overdue', color: '#d97706' },
  ];

  const sectionHeader = (title: string) => (
    <h3
      style={{
        margin: 0,
        fontSize: 16,
        fontWeight: 600,
        color: '#1f2937',
      }}
    >
      {title}
    </h3>
  );

  return (
    <div style={{ padding: '32px 40px', fontFamily: "'Segoe UI', Roboto, Arial, sans-serif", background: '#f3f4f6', minHeight: '100vh' }}>
      {/* Page header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111827' }}>Audit Dashboard</h1>
        <p style={{ margin: '4px 0 0', fontSize: 14, color: '#6b7280' }}>Overview of audit operations and compliance status</p>
      </div>

      {/* KPI cards */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 32 }}>
        {kpis.map((kpi) => (
          <KpiCard key={kpi.title} {...kpi} />
        ))}
      </div>

      {/* Two-column layout */}
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
        {/* Workflow Timeline */}
        <div
          style={{
            flex: '2 1 400px',
            background: '#fff',
            borderRadius: 10,
            border: '1px solid #e9ecef',
            padding: 24,
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}
        >
          {sectionHeader('Workflow Timeline')}
          <div style={{ marginTop: 20 }}>
            {mockActivities.map((a, i) => (
              <div
                key={a.id}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 12,
                  paddingBottom: i < mockActivities.length - 1 ? 16 : 0,
                  position: 'relative',
                }}
              >
                {/* Timeline dot + line */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 12 }}>
                  <div
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: '#2563eb',
                      marginTop: 4,
                      flexShrink: 0,
                    }}
                  />
                  {i < mockActivities.length - 1 && (
                    <div style={{ width: 2, flex: 1, background: '#e5e7eb', minHeight: 20 }} />
                  )}
                </div>
                {/* Content */}
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: '#1f2937' }}>{a.action}</div>
                  <div style={{ fontSize: 13, color: '#6b7280' }}>{a.project}</div>
                  <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{a.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Pending Approvals */}
        <div
          style={{
            flex: '1 1 280px',
            background: '#fff',
            borderRadius: 10,
            border: '1px solid #e9ecef',
            padding: 24,
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}
        >
          {sectionHeader('Pending Approvals')}
          <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {mockApprovals.map((app) => (
              <div
                key={app.id}
                style={{
                  padding: '12px 14px',
                  borderRadius: 8,
                  border: '1px solid #f3f4f6',
                  background: '#fafafa',
                }}
              >
                <div style={{ fontSize: 14, fontWeight: 500, color: '#1f2937', marginBottom: 2 }}>
                  {app.name}
                </div>
                <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>{app.project}</div>
                <div
                  style={{
                    display: 'inline-block',
                    fontSize: 11,
                    fontWeight: 600,
                    padding: '2px 10px',
                    borderRadius: 12,
                    background: '#fef3c7',
                    color: '#92400e',
                  }}
                >
                  {app.status}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
