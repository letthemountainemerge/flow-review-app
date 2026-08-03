import axios from 'axios';
import type { TaskInfo, TaskListResponse, ReviewReport } from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000, // 评审启动请求可能稍慢
});

// 任务管理
export async function createTask(formData: FormData): Promise<TaskInfo> {
  const { data } = await api.post('/tasks', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function listTasks(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<TaskListResponse> {
  const { data } = await api.get('/tasks', { params });
  return data;
}

export async function getTask(id: string): Promise<TaskInfo> {
  const { data } = await api.get(`/tasks/${id}`);
  return data;
}

export async function deleteTask(id: string): Promise<void> {
  await api.delete(`/tasks/${id}`);
}

export async function getReport(taskId: string): Promise<ReviewReport> {
  const { data } = await api.get(`/tasks/${taskId}/report`);
  return data;
}

export async function startReview(taskId: string): Promise<TaskInfo> {
  const { data } = await api.post(`/tasks/${taskId}/review`);
  return data;
}

export async function getTaskStatus(taskId: string): Promise<TaskInfo> {
  const { data } = await api.get(`/tasks/${taskId}`);
  return data;
}

export async function submitFeedback(
  taskId: string,
  feedback: {
    finding_id: string;
    dimension_id: number;
    correction_type: string;
    expert_comment: string;
    ai_conclusion: string;
  }
): Promise<void> {
  await api.post(`/tasks/${taskId}/feedback`, feedback);
}
