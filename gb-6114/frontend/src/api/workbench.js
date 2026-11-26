import { request } from "./http.js";

export const api = {
  config: () => request("/workbench"),
  login: data => request("/auth/login", {method: "POST", data}),
  cases: () => request("/cases"),
  createCase: data => request("/cases", {method: "POST", data}),
  runs: () => request("/runs"),
  run: (id, signal) => request(`/runs/${id}`, {signal}),
  enqueue: (id, data) => request(`/cases/${id}/runs`, {method: "POST", data}),
  review: id => request(`/runs/${id}/review`),
  submitReview: (id, data) => request(`/runs/${id}/review`, {method: "POST", data}),
  validity: id => request(`/runs/${id}/validity`),
  export: id => request(`/runs/${id}/export`, {raw: true}),
  evidenceBundle: id => request(`/runs/${id}/evidence-bundle`, {raw: true}),
  withdrawals: caseId => request(`/cases/${caseId}/withdrawals`),
  withdrawBasis: (caseId, data) => request(`/cases/${caseId}/withdrawals`, {method: "POST", data}),
  audit: () => request("/audit", {signal: AbortSignal.timeout(5000)}),
};
