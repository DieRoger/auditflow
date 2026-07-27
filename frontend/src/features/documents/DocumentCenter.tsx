import React, { useState, useEffect, useCallback } from "react";

interface Document {
  id: string;
  project_id: string;
  filename: string;
  document_type: string;
  status: "PENDING" | "PARSING" | "OCR" | "CHUNKING" | "EMBEDDING" | "READY" | "FAILED";
  size_bytes: number;
  page_count: number;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: "#f59e0b",
  PARSING: "#3b82f6",
  OCR: "#8b5cf6",
  CHUNKING: "#06b6d4",
  EMBEDDING: "#10b981",
  READY: "#22c55e",
  FAILED: "#ef4444",
};

const API = "http://localhost:8000/api/v1/documents";

const DocumentCenter: React.FC = () => {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("");
  const [uploading, setUploading] = useState(false);

  const fetchDocs = useCallback(async () => {
    try {
      const params = new URLSearchParams({ project_id: "proj_001" });
      if (filter) params.set("status", filter);
      const res = await fetch(`${API}?${params}`);
      const data = await res.json();
      setDocs(data.items || []);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("project_id", "proj_001");
      await fetch(API, { method: "POST", body: form });
      await fetchDocs();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("确认删除此文档？")) return;
    try {
      await fetch(`${API}/${id}`, { method: "DELETE" });
      await fetchDocs();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 16 }}>Document Center</h1>

      {error && <div style={{ color: "red", marginBottom: 12 }}>Error: {error}</div>}

      <div style={{ border: "2px dashed #ccc", borderRadius: 8, padding: 32, textAlign: "center", marginBottom: 16 }}>
        <input type="file" accept=".pdf" onChange={handleUpload} disabled={uploading} style={{ display: "none" }} id="file-upload" />
        <label htmlFor="file-upload" style={{ cursor: "pointer", color: "#3b82f6", fontWeight: 500 }}>
          {uploading ? "Uploading..." : "Click to upload PDF or drag & drop"}
        </label>
      </div>

      <div style={{ marginBottom: 12 }}>
        <select value={filter} onChange={(e) => setFilter(e.target.value)} style={{ padding: "4px 8px" }}>
          <option value="">All Status</option>
          <option value="PENDING">Pending</option>
          <option value="READY">Ready</option>
          <option value="FAILED">Failed</option>
        </select>
      </div>

      {loading ? (
        <div>Loading...</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f8fafc", textAlign: "left" }}>
              <th style={thStyle}>Filename</th>
              <th style={thStyle}>Type</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle}>Pages</th>
              <th style={thStyle}>Created</th>
              <th style={thStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((doc) => (
              <tr key={doc.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                <td style={tdStyle}>{doc.filename}</td>
                <td style={tdStyle}>{doc.document_type}</td>
                <td style={tdStyle}>
                  <span style={{
                    background: STATUS_COLORS[doc.status] || "#94a3b8",
                    color: "#fff", borderRadius: 12, padding: "2px 8px", fontSize: 12,
                  }}>
                    {doc.status}
                  </span>
                </td>
                <td style={tdStyle}>{doc.page_count || "-"}</td>
                <td style={tdStyle}>{new Date(doc.created_at).toLocaleDateString()}</td>
                <td style={tdStyle}>
                  <button onClick={() => handleDelete(doc.id)} style={{ color: "#ef4444", border: "none", background: "none", cursor: "pointer" }}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {docs.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: "center", padding: 24, color: "#94a3b8" }}>No documents yet</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};

const thStyle: React.CSSProperties = { padding: "8px 12px", fontWeight: 600, fontSize: 13, color: "#475569" };
const tdStyle: React.CSSProperties = { padding: "8px 12px", fontSize: 13 };

export default DocumentCenter;
