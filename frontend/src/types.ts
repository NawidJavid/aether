export type JobStatus =
  | 'pending'
  | 'generating_script'
  | 'generating_assets'
  | 'assembling'
  | 'completed'
  | 'failed';

export interface ScheduledShape {
  concept: string;
  point_cloud_url: string;
  point_count: number;
  trigger_time_ms: number;
  morph_duration_ms: number;
  subtitle: string;
}

export interface Manifest {
  manifest_id: string;
  topic: string;
  audio_url: string;
  audio_duration_ms: number;
  shapes: ScheduledShape[];
  full_text: string;
  created_at: string;
}

export interface Job {
  job_id: string;
  topic: string;
  status: JobStatus;
  progress_message: string;
  manifest: Manifest | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}
