import type {
  AgentAnalyzeRequest,
  AgentAnalyzeResponse,
  AgentSelfCorrectRequest,
  AgentSelfCorrectResponse,
  AnalyzeRequest,
  AnalyzeResponse,
  BranchRequest,
  BranchResponse,
  CacheStats,
  CheckpointListResponse,
  MultiAgentAnalyzeResponse,
  SelfCorrectRequest,
  SelfCorrectResponse,
  UploadResponse,
} from "@/lib/types/loop";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

let _activeController: AbortController | null = null;

function createController(): AbortSignal {
  _activeController?.abort();
  _activeController = new AbortController();
  return _activeController.signal;
}

async function requestJson<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<TResponse>;
}

async function requestFormData<TResponse>(path: string, formData: FormData): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Upload failed with status ${response.status}`);
  }

  return response.json() as Promise<TResponse>;
}

export const apiClient = {
  /** Cancel any in-flight analyze or self-correct request. */
  cancel() {
    _activeController?.abort();
    _activeController = null;
  },

  // --- Procedural endpoints ---

  analyze(payload: AnalyzeRequest): Promise<AnalyzeResponse> {
    return requestJson<AnalyzeResponse>("/api/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
      signal: createController(),
    });
  },

  selfCorrect(payload: SelfCorrectRequest): Promise<SelfCorrectResponse> {
    return requestJson<SelfCorrectResponse>("/api/self-correct", {
      method: "POST",
      body: JSON.stringify(payload),
      signal: createController(),
    });
  },

  // --- Upload endpoints ---

  uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    return requestFormData<UploadResponse>("/api/upload/file", formData);
  },

  uploadFolder(zipFile: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", zipFile);
    return requestFormData<UploadResponse>("/api/upload/folder", formData);
  },

  uploadFiles(files: File[]): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    return requestFormData<UploadResponse>("/api/upload/files", formData);
  },

  // --- Agent workflow endpoints ---

  agentAnalyze(payload: AgentAnalyzeRequest): Promise<AgentAnalyzeResponse> {
    return requestJson<AgentAnalyzeResponse>("/api/agent/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
      signal: createController(),
    });
  },

  agentSelfCorrect(payload: AgentSelfCorrectRequest): Promise<AgentSelfCorrectResponse> {
    return requestJson<AgentSelfCorrectResponse>("/api/agent/self-correct", {
      method: "POST",
      body: JSON.stringify(payload),
      signal: createController(),
    });
  },

  agentMultiAnalyze(payload: AgentAnalyzeRequest): Promise<MultiAgentAnalyzeResponse> {
    return requestJson<MultiAgentAnalyzeResponse>("/api/agent/multi-analyze", {
      method: "POST",
      body: JSON.stringify(payload),
      signal: createController(),
    });
  },

  agentState(sessionId: string): Promise<Record<string, unknown>> {
    return requestJson<Record<string, unknown>>(`/api/agent/state/${encodeURIComponent(sessionId)}`);
  },

  // --- Checkpoint endpoints ---

  listCheckpoints(sessionId: string): Promise<CheckpointListResponse> {
    return requestJson<CheckpointListResponse>(`/api/agent/checkpoints/${encodeURIComponent(sessionId)}`);
  },

  getCheckpoint(sessionId: string, attempt: number): Promise<Record<string, unknown>> {
    return requestJson<Record<string, unknown>>(`/api/agent/checkpoint/${encodeURIComponent(sessionId)}/${attempt}`);
  },

  branchFromCheckpoint(payload: BranchRequest): Promise<BranchResponse> {
    return requestJson<BranchResponse>("/api/agent/branch", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // --- Cache stats ---

  cacheStats(): Promise<CacheStats> {
    return requestJson<CacheStats>("/api/agent/cache/stats");
  },
};
