import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 min for generation requests
});

export interface Target {
  id: string;
  name: string;
  role: string;
  category: string;
  description: string;
}

export interface Narrative {
  id: string;
  title: string;
  description: string;
  category: string;
  icon: string;
}

export interface PromptResponse {
  prompt: string;
  target: Target;
  narrative: Narrative;
}

export interface ImageResponse {
  image_url: string;
  filename: string;
}

export interface VideoResponse {
  operation_id: string;
  status: string;
}

export interface VideoStatusResponse {
  status: 'pending' | 'complete' | 'failed';
  video_url?: string;
  filename?: string;
  error?: string;
}

export async function fetchTargets(): Promise<Target[]> {
  const res = await api.get('/api/targets');
  return res.data.targets;
}

export async function fetchNarratives(): Promise<Narrative[]> {
  const res = await api.get('/api/narratives');
  return res.data.narratives;
}

export async function generatePrompt(
  targetId: string,
  narrativeId: string,
  generationType: 'image' | 'video'
): Promise<PromptResponse> {
  const res = await api.post('/api/generate-prompt', {
    target_id: targetId,
    narrative_id: narrativeId,
    generation_type: generationType,
  });
  return res.data;
}

export async function generateImage(prompt: string): Promise<ImageResponse> {
  const res = await api.post('/api/generate-image', { prompt });
  return res.data;
}

export async function generateVideo(prompt: string): Promise<VideoResponse> {
  const res = await api.post('/api/generate-video', { prompt });
  return res.data;
}

export async function checkVideoStatus(operationId: string): Promise<VideoStatusResponse> {
  const res = await api.get(`/api/video-status/${operationId}`);
  return res.data;
}

export function getMediaUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export function getDownloadUrl(filename: string): string {
  return `${API_BASE}/api/download/${filename}`;
}
