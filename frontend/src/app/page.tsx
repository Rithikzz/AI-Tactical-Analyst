"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createUploadSession,
  completeUpload,
  fetchAnalytics,
  getJob,
  ingestLive,
  ingestYouTube,
  uploadPart,
  type Job,
  type Analytics,
  type AnalyticsEvent,
} from "@/lib/api";

type UploadState =
  | { status: "idle" }
  | { status: "uploading"; progress: number }
  | { status: "completed"; jobId: string }
  | { status: "error"; message: string };

export default function Home() {
  const [tab, setTab] = useState<"upload" | "youtube" | "live">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>({ status: "idle" });
  const [job, setJob] = useState<Job | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [youtubeUrl, setYouTubeUrl] = useState("");
  const [liveUrl, setLiveUrl] = useState("");


  const handleUpload = useCallback(async () => {
    if (!file) {
      setUploadState({ status: "error", message: "Please select a file." });
      return;
    }

    try {
      setUploadState({ status: "uploading", progress: 0 });
      const totalParts = Math.ceil(file.size / (8 * 1024 * 1024));
      const session = await createUploadSession({
        filename: file.name,
        size_bytes: file.size,
        mime_type: file.type || "video/mp4",
        total_parts: totalParts,
      });

      const chunkSize = session.chunk_size_bytes;
      for (let part = 0; part < totalParts; part += 1) {
        const start = part * chunkSize;
        const end = Math.min(start + chunkSize, file.size);
        const blob = file.slice(start, end);
        await uploadPart(session.upload_id, part + 1, blob);
        const progress = Math.round(((part + 1) / totalParts) * 100);
        setUploadState({ status: "uploading", progress });
      }

      const jobResponse = await completeUpload(session.upload_id);
      setJob(jobResponse.job);
      setUploadState({ status: "completed", jobId: jobResponse.job.id });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Upload failed.";
      setUploadState({
        status: "error",
        message,
      });
    }
  }, [file]);

  const handleYouTube = useCallback(async () => {
    if (!youtubeUrl) {
      setUploadState({ status: "error", message: "Enter a YouTube URL." });
      return;
    }
    try {
      setUploadState({ status: "uploading", progress: 0 });
      const jobResponse = await ingestYouTube(youtubeUrl);
      setJob(jobResponse.job);
      setUploadState({ status: "completed", jobId: jobResponse.job.id });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "YouTube ingest failed.";
      setUploadState({
        status: "error",
        message,
      });
    }
  }, [youtubeUrl]);

  const handleLive = useCallback(async () => {
    if (!liveUrl) {
      setUploadState({ status: "error", message: "Enter a live stream URL." });
      return;
    }
    try {
      setUploadState({ status: "uploading", progress: 0 });
      const jobResponse = await ingestLive(liveUrl);
      setJob(jobResponse.job);
      setUploadState({ status: "completed", jobId: jobResponse.job.id });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Live ingest failed.";
      setUploadState({
        status: "error",
        message,
      });
    }
  }, [liveUrl]);

  useEffect(() => {
    if (!job?.id) {
      return;
    }

    let ws: WebSocket | null = null;
    let isActive = true;

    const fetchJob = async () => {
      try {
        const updated = await getJob(job.id);
        if (!isActive) {
          return;
        }
        setJob(updated);
        if (updated.status === "completed" && updated.analytics_path) {
          const analyticsData = await fetchAnalytics(updated.id);
          setAnalytics(analyticsData);
        }
      } catch {
      }
    };

    fetchJob();

    const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
    const wsUrl = apiBase.replace("http", "ws") + `/ws/jobs/${job.id}`;
    ws = new WebSocket(wsUrl);
    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "job") {
          setJob(data.payload);
          if (data.payload.status === "completed") {
            const analyticsData = await fetchAnalytics(data.payload.id);
            setAnalytics(analyticsData);
          }
        }
      } catch {
        // ignore malformed messages
      }
    };

    return () => {
      isActive = false;
      ws?.close();
    };
  }, [job?.id]);

  const summaryStats = useMemo(() => {
    const summary = analytics?.summary || {};
    return [
      { label: "Events", value: analytics?.events_count ?? "-" },
      { label: "Possession", value: summary?.team_stats ? "Calculated" : "-" },
      { label: "Shots", value: summary?.team_stats?.["1"]?.total_shots ?? "-" },
      { label: "Passes", value: summary?.team_stats?.["1"]?.total_passes ?? "-" },
    ];
  }, [analytics]);

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <header className="border-b border-white/10 bg-zinc-950/80">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-emerald-400">
              Football Intelligence
            </p>
            <h1 className="text-2xl font-semibold">Match Analytics Command Center</h1>
          </div>
          <div className="flex items-center gap-3 text-sm text-white/60">
            <span>Realtime pipeline</span>
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[360px_1fr]">
        <section className="flex flex-col gap-6">
          <div className="rounded-2xl border border-white/10 bg-zinc-900/60 p-6">
            <h2 className="text-lg font-semibold">Ingest a match</h2>
            <p className="mt-2 text-sm text-white/60">
              Upload a video or connect a stream. Progress updates appear live.
            </p>

            <div className="mt-4 flex rounded-full bg-white/5 p-1 text-xs">
              {(["upload", "youtube", "live"] as const).map((option) => (
                <button
                  key={option}
                  onClick={() => setTab(option)}
                  className={`flex-1 rounded-full px-3 py-2 transition ${
                    tab === option ? "bg-white text-zinc-900" : "text-white/60"
                  }`}
                >
                  {option === "upload" ? "Upload" : option === "youtube" ? "YouTube" : "Live"}
                </button>
              ))}
            </div>

            {tab === "upload" && (
              <div className="mt-4 space-y-3">
                <input
                  type="file"
                  accept="video/*"
                  className="w-full rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-sm"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
                <button
                  onClick={handleUpload}
                  className="w-full rounded-lg bg-emerald-400 px-4 py-2 text-sm font-medium text-zinc-900"
                >
                  Start Upload
                </button>
              </div>
            )}

            {tab === "youtube" && (
              <div className="mt-4 space-y-3">
                <input
                  value={youtubeUrl}
                  onChange={(event) => setYouTubeUrl(event.target.value)}
                  placeholder="https://youtube.com/..."
                  className="w-full rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-sm"
                />
                <button
                  onClick={handleYouTube}
                  className="w-full rounded-lg bg-emerald-400 px-4 py-2 text-sm font-medium text-zinc-900"
                >
                  Analyze YouTube
                </button>
              </div>
            )}

            {tab === "live" && (
              <div className="mt-4 space-y-3">
                <input
                  value={liveUrl}
                  onChange={(event) => setLiveUrl(event.target.value)}
                  placeholder="rtmp:// or srt://"
                  className="w-full rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-sm"
                />
                <button
                  onClick={handleLive}
                  className="w-full rounded-lg bg-emerald-400 px-4 py-2 text-sm font-medium text-zinc-900"
                >
                  Start Live Capture
                </button>
              </div>
            )}

            <div className="mt-4 rounded-xl border border-white/10 bg-zinc-950 p-4 text-sm">
              {uploadState.status === "idle" && <p className="text-white/60">No active job.</p>}
              {uploadState.status === "uploading" && (
                <div className="space-y-2">
                  <p className="text-white/80">Uploading… {uploadState.progress}%</p>
                  <div className="h-2 w-full rounded-full bg-white/10">
                    <div
                      className="h-2 rounded-full bg-emerald-400"
                      style={{ width: `${uploadState.progress}%` }}
                    />
                  </div>
                </div>
              )}
              {uploadState.status === "completed" && (
                <p className="text-white/80">Job created: {uploadState.jobId}</p>
              )}
              {uploadState.status === "error" && (
                <p className="text-red-400">{uploadState.message}</p>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-zinc-900/60 p-6">
            <h3 className="text-lg font-semibold">Live status</h3>
            {job ? (
              <div className="mt-3 space-y-2 text-sm text-white/70">
                <p>Stage: {job.stage}</p>
                <p>Status: {job.status}</p>
                <p>Progress: {job.progress}%</p>
                {job.error && <p className="text-red-400 text-xs mt-1">Error: {job.error}</p>}
              </div>
            ) : (
              <p className="mt-3 text-sm text-white/60">No job selected.</p>
            )}
          </div>
        </section>

        <section className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            {summaryStats.map((stat) => (
              <div key={stat.label} className="rounded-2xl border border-white/10 bg-zinc-900 p-5">
                <p className="text-xs uppercase tracking-[0.2em] text-white/50">
                  {stat.label}
                </p>
                <p className="mt-3 text-2xl font-semibold">{stat.value}</p>
              </div>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-2xl border border-white/10 bg-zinc-900/60 p-6">
              <h3 className="text-lg font-semibold">Event timeline</h3>
              <div className="mt-4 space-y-3">
                {(analytics?.events || []).slice(0, 8).map((event: AnalyticsEvent, index) => (
                  <div
                    key={`${event.event_type}-${index}`}
                    className="flex items-center justify-between rounded-xl bg-zinc-950/70 px-4 py-3 text-sm"
                  >
                    <div>
                      <p className="font-medium capitalize text-white">{event.event_type}</p>
                      <p className="text-xs text-white/50">
                        {event.timestamp ?? 0}s · Player {event.player_id ?? "—"}
                      </p>
                    </div>
                    <span className="text-xs text-emerald-400">
                      {typeof event.confidence === "number"
                        ? `${Math.round(event.confidence * 100)}%`
                        : "—"}
                    </span>
                  </div>
                ))}
                {!analytics?.events?.length && (
                  <p className="text-sm text-white/60">No events yet.</p>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-zinc-900/60 p-6">
              <h3 className="text-lg font-semibold">Heatmap preview</h3>
              <div className="mt-4 aspect-[4/5] w-full rounded-2xl border border-white/10 bg-gradient-to-b from-emerald-400/10 via-transparent to-zinc-950">
                <div className="h-full w-full rounded-2xl border border-white/5 bg-[radial-gradient(circle_at_center,_rgba(16,185,129,0.25),_transparent_60%)]" />
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-zinc-900/60 p-6">
            <h3 className="text-lg font-semibold">Player & team analytics</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              {["Player speed", "Possession", "Pressing"].map((label) => (
                <div key={label} className="rounded-xl bg-zinc-950/70 px-4 py-4 text-sm">
                  <p className="text-white/60">{label}</p>
                  <p className="mt-3 text-lg font-semibold">—</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
