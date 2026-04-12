import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const chatAPI = {

  // POST /api/chat/start — aucun body attendu en v2
  startSession: async () => {
    const response = await axios.post(`${API_BASE}/chat/start`);
    return response.data;
  },

  // POST /api/chat/message
  sendMessage: async (sessionId, message) => {
    const response = await axios.post(`${API_BASE}/chat/message`, {
      session_id: sessionId,
      message: message,
    });
    return response.data;
  },

  // GET /api/chat/history/{session_id}
  getHistory: async (sessionId) => {
    const response = await axios.get(`${API_BASE}/chat/history/${sessionId}`);
    return response.data;
  },

  // POST /api/reports/generate
  generateReport: async (sessionId) => {
    const response = await axios.post(`${API_BASE}/reports/generate`, {
      session_id: sessionId,
    });
    return response.data;
  },
};
