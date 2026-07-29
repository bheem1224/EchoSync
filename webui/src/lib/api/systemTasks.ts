import apiClient from '../../api/client';

export interface ProcessOwner {
  owner_id: string;
  owner_type: 'core' | 'plugin' | 'system_job' | string;
  pid?: number | null;
  thread_id?: number | null;
  task_name: string;
  started_at: string;
  metadata?: Record<string, any>;
  registration_id?: string;
}

export interface JobInfo {
  name: string;
  category: string;
  state: string;
  enabled: boolean;
  running: boolean;
  next_run?: number | null;
  interval_seconds?: number | null;
  tags?: string[];
  plugin?: string | null;
  total_successes?: number;
  total_failures?: number;
  last_error?: string | null;
}

export interface TaskQueueSummaryResponse {
  stats: {
    total: number;
    running: number;
    pending: number;
    blocked: number;
  };
  running_jobs: JobInfo[];
  pending_jobs: JobInfo[];
  blocked_jobs: JobInfo[];
}

export interface ProcessListResponse {
  total: number;
  processes: ProcessOwner[];
}

export interface ProcessTerminateResponse {
  status: string;
  registration_id: string;
  message: string;
}

export interface PluginStatusInfo {
  state: 'unconfigured' | 'initializing' | 'ready' | 'degraded' | 'error' | string;
  message?: string | null;
  last_health_check?: string | null;
}

export interface SystemHealthResponse {
  status: 'healthy' | 'degraded' | 'error' | string;
  timestamp: string;
  health_checks: Record<string, any>;
  plugin_states: Record<string, PluginStatusInfo>;
}

export async function fetchSystemHealth(): Promise<SystemHealthResponse> {
  const response = await apiClient.get<SystemHealthResponse>('/v1/system/health');
  return response.data;
}

export async function fetchTaskQueue(): Promise<TaskQueueSummaryResponse> {
  const response = await apiClient.get<TaskQueueSummaryResponse>('/v1/tasks/queue');
  return response.data;
}

export async function fetchProcesses(): Promise<ProcessListResponse> {
  const response = await apiClient.get<ProcessListResponse>('/v1/tasks/processes');
  return response.data;
}

export async function terminateProcess(registrationId: string): Promise<ProcessTerminateResponse> {
  const response = await apiClient.post<ProcessTerminateResponse>(
    `/v1/tasks/processes/${encodeURIComponent(registrationId)}/terminate`
  );
  return response.data;
}
