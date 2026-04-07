import type { Job } from './types';

const BASE = '';

export async function generateExplanation(topic: string): Promise<{ job_id: string }> {
  const resp = await fetch(`${BASE}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  });
  if (!resp.ok) throw new Error(`Generate failed: ${resp.status}`);
  return resp.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const resp = await fetch(`${BASE}/api/jobs/${jobId}`);
  if (!resp.ok) throw new Error(`Job fetch failed: ${resp.status}`);
  return resp.json();
}
