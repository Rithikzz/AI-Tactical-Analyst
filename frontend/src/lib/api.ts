export type UploadSession = {
  upload_id: string;
  chunk_size_bytes: number;
  status: string;
};

export type Job = {
  id: string;
  source_type: string;
  source_ref: string;
  status: string;
  stage: string;
  progress: number;
  error?: string | null;
  output_video_path?: string | null;
  analytics_path?: string | null;
};

export type JobResponse = {
  job: Job;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Request failed");
  }
  return (await response.json()) as T;
}

export async function createUploadSession(payload: {
  filename: string;
  size_bytes: number;
  mime_type: string;
  total_parts: number;
}): Promise<UploadSession> {
  return request<UploadSession>("/uploads", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function uploadPart(
  uploadId: string,
  partNumber: number,
  blob: Blob,
): Promise<void> {
  const form = new FormData();
  form.append("file", blob);
  const response = await fetch(
    `${API_BASE}/uploads/${uploadId}/parts?part_number=${partNumber}`,
    {
      method: "POST",
      body: form,
    },
  );
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Upload part failed");
  }
}

export async function completeUpload(uploadId: string): Promise<JobResponse> {
  return request<JobResponse>(`/uploads/${uploadId}/complete`, { method: "POST" });
}

export async function ingestYouTube(url: string): Promise<JobResponse> {
  return request<JobResponse>("/ingest/youtube", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

export async function ingestLive(url: string): Promise<JobResponse> {
  return request<JobResponse>("/ingest/live", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

export async function getJob(jobId: string): Promise<Job> {
  return request<Job>(`/jobs/${jobId}`);
}

export type AnalyticsEvent = {
  event_type: string;
  timestamp?: number;
  player_id?: number;
  confidence?: number;
};

export type AnalyticsSummary = {
  team_stats?: Record<string, { total_shots?: number; total_passes?: number }>;
};

export type Analytics = {
  events?: AnalyticsEvent[];
  events_count?: number;
  summary?: AnalyticsSummary;
};

export async function fetchAnalytics(jobId: string): Promise<Analytics> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/analytics`);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Analytics not available");
  }
  return response.json();
}
