/** AuditFlow API Client — 与 FastAPI backend (:8000) 通信 */

var BASE_URL = "http://localhost:8000/api/v1";

function setBaseUrl(url) {
  BASE_URL = url.replace(/\/$/, "");
}

async function request(path, options) {
  var opts = options || {};
  var headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
  var resp = await fetch(BASE_URL + path, {
    method: opts.method || "GET",
    headers: headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!resp.ok) {
    var detail = "";
    try { detail = (await resp.json()).detail || ""; } catch (e) { /* ignore */ }
    throw new Error("API " + resp.status + ": " + path + " " + detail);
  }
  var text = await resp.text();
  return text ? JSON.parse(text) : null;
}

var api = {
  // Agents
  listAgents: function () { return request("/agents"); },

  // Workflows
  createWorkflow: function (body) { return request("/workflows", { method: "POST", body: body }); },
  getWorkflow: function (id) { return request("/workflows/" + id); },
  startWorkflow: function (id) { return request("/workflows/" + id + "/start", { method: "POST", body: {} }); },
  getWorkflowTrace: function (id) { return request("/workflows/" + id + "/trace"); },

  // Knowledge
  searchKnowledge: function (query, topK) {
    return request("/knowledge/search", {
      method: "POST",
      body: { query: query, top_k: topK || 5 },
    });
  },

  // Documents
  listDocuments: function () { return request("/documents"); },

  setBaseUrl: setBaseUrl,
};

export default api;
