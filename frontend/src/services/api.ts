import axios from "axios";
import {
  BaselineData,
  HistoryRecord,
  BurnoutAnalysisResult,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error(
      "API Error:",
      error.response?.status,
      error.response?.data || error.message
    );
    return Promise.reject(error);
  }
);

export const audioApi = {
  analyzeAudio: async (
    file: File,
    userId?: string,
    sessionId?: string
  ) => {
    const formData = new FormData();
    formData.append("file", file);

    if (userId) formData.append("user_id", userId);
    if (sessionId) formData.append("session_id", sessionId);

    const response = await api.post("/audio/analyze", formData);
    return response.data;
  },

  analyzeWithBaseline: async (
    file: File,
    baseline?: BaselineData,
    history?: HistoryRecord[],
    userId?: string
  ): Promise<{
    status: string;
    analysis: BurnoutAnalysisResult;
    current_result: any;
    baseline_used: BaselineData;
    metadata: any;
    processing_time_ms: number;
  }> => {
    const formData = new FormData();
    formData.append("file", file);

    if (baseline) {
      formData.append("baseline_data", JSON.stringify(baseline));
    }

    if (history) {
      formData.append("history_data", JSON.stringify(history));
    }

    if (userId) {
      formData.append("user_id", userId);
    }

    const response = await api.post(
      "/audio/analyze-with-baseline",
      formData
    );

    return response.data;
  },

  healthCheck: async () => {
    const response = await api.get("/health/ping");
    return response.data;
  },

  getTaskStatus: async (taskId: string) => {
    const response = await api.get(`/audio/status/${taskId}`);
    return response.data;
  },
};

export default api;