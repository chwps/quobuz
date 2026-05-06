import { useState, useEffect } from 'react'

/**
 * API client — typed helpers for backend communication.
 */

const BASE = ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(text || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export const api = {
  // Auth
  login: () => request<{ success: boolean }>('/api/auth/login', { method: 'POST' }),
  getUser: () => request<Record<string, unknown>>('/api/auth/user'),
  refreshCredentials: () => request<{ success: boolean; app_id?: string; app_secret?: string }>('/api/auth/refresh-credentials', { method: 'POST' }),

  // Playlists
  getPlaylists: () => request<Playlist[]>('/api/playlists'),
  getPlaylistTracks: (id: string) => request<{ total: number; tracks: TrackItem[] }>(`/api/playlists/${id}/tracks`),
  subscribePlaylist: (id: string) => request<{ success: boolean }>(`/api/playlists/${id}/subscribe`, { method: 'POST' }),
  unsubscribePlaylist: (id: string) => request<{ success: boolean }>(`/api/playlists/${id}/unsubscribe`, { method: 'POST' }),
  downloadPlaylist: (id: string) => request<{ job_id: number }>(`/api/playlists/${id}/download`, { method: 'POST' }),
  addPlaylist: (params: Record<string, string | number>) => {
    const qs = new URLSearchParams(params as any).toString()
    return request<{ success: boolean; id: number }>(`/api/playlists/add?${qs}`, { method: 'POST' })
  },

  // Subscriptions
  getSubscriptions: () => request<Subscription[]>('/api/subscriptions'),

  // Jobs
  getActiveJobs: () => request<Job[]>('/api/jobs/active'),
  getRecentJobs: (limit = 50) => request<Job[]>(`/api/jobs/recent?limit=${limit}`),
  getJob: (id: number) => request<Job>(`/api/jobs/${id}`),
  cancelDownload: () => request<{ cancelled: boolean }>('/api/jobs/cancel', { method: 'POST' }),

  // Settings
  getSettings: () => request<Record<string, string>>('/api/settings'),
  updateSettings: (settings: Record<string, string>) => request<{ success: boolean }>('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  }),

  // Logs
  getLogs: (limit = 200) => request<LogEntry[]>(`/api/logs?limit=${limit}`),
  clearLogs: (days = 7) => request<{ success: boolean }>(`/api/logs?days=${days}`, { method: 'DELETE' }),
}

// --- SSE Connection ---
export function useSSE(): { connected: boolean; lastEvent: { event: string; data: any } | null } {
  const [connected, setConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState<{ event: string; data: any } | null>(null)

  useEffect(() => {
    const eventSource = new EventSource('/api/stream')

    eventSource.onopen = () => setConnected(true)
    eventSource.onerror = () => setConnected(false)

    eventSource.addEventListener('progress', (e) => {
      setLastEvent({ event: 'progress', data: JSON.parse(e.data) })
    })
    eventSource.addEventListener('log', (e) => {
      setLastEvent({ event: 'log', data: JSON.parse(e.data) })
    })
    eventSource.addEventListener('job_complete', (e) => {
      setLastEvent({ event: 'job_complete', data: JSON.parse(e.data) })
    })

    return () => eventSource.close()
  }, [])

  return { connected, lastEvent }
}

// --- Types ---
export interface Playlist {
  id: number
  qobuz_id: string
  title: string
  description: string
  image: string
  image_large: string
  track_count: number
  duration: number
  duration_formatted: string
  is_public: boolean
  follower_count: number
  creator: string
  is_subscribed: boolean
}

export interface TrackItem {
  id: number
  title: string
  duration: number
  duration_formatted: string
  track_number: number
  disc_number: number
  artist: string
  album: string
  album_image: string
}

export interface Subscription {
  id: number
  playlist_qobuz_id: string
  title: string
  active: number
  last_downloaded: string | null
  download_count: number
  created_at: string
}

export interface Job {
  id: number
  playlist_qobuz_id: string
  status: string
  total_tracks: number
  downloaded: number
  skipped: number
  failed: number
  progress: number
  current_track: string
  error: string
  started_at: string | null
  completed_at: string | null
}

export interface LogEntry {
  id: number
  timestamp: string
  level: string
  message: string
  job_id: number | null
}
