const API_BASE = '/api';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('diagnos_token') || null;
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('diagnos_token', token);
    } else {
      localStorage.removeItem('diagnos_token');
    }
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const config = {
      ...options,
      headers,
    };

    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        let errorMessage = 'An unexpected error occurred.';
        if (data && data.detail) {
          if (typeof data.detail === 'string') {
            errorMessage = data.detail;
          } else if (Array.isArray(data.detail)) {
            errorMessage = data.detail
              .map((item) => {
                if (typeof item === 'string') return item;
                if (item.msg) {
                  const field = item.loc ? item.loc[item.loc.length - 1] : '';
                  const capitalizedField = field ? field.charAt(0).toUpperCase() + field.slice(1) : '';
                  return capitalizedField ? `${capitalizedField}: ${item.msg}` : item.msg;
                }
                return JSON.stringify(item);
              })
              .join('. ');
          } else if (typeof data.detail === 'object') {
            errorMessage = data.detail.msg || JSON.stringify(data.detail);
          }
        } else if (data && data.message) {
          errorMessage = data.message;
        }
        throw new Error(errorMessage);
      }

      return data;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  }

  // Auth endpoints
  async register(name, email, password) {
    const res = await this.request('/auth/register', {
      method: 'POST',
      body: { name, email, password }
    });
    this.setToken(res.access_token);
    return res.user;
  }

  async login(email, password) {
    const res = await this.request('/auth/login', {
      method: 'POST',
      body: { email, password }
    });
    this.setToken(res.access_token);
    return res.user;
  }

  logout() {
    this.setToken(null);
  }

  async getMe() {
    if (!this.token) return null;
    try {
      return await this.request('/auth/me');
    } catch (e) {
      this.logout();
      return null;
    }
  }

  // Case library endpoints
  async getCases() {
    return await this.request('/cases');
  }

  async getCase(caseId) {
    return await this.request(`/cases/${caseId}`);
  }

  async getSession(sessionId) {
    return await this.request(`/simulation/${sessionId}`);
  }

  // Simulation endpoints
  async startSimulation(caseId) {
    return await this.request('/simulation/start', {
      method: 'POST',
      body: { case_id: caseId }
    });
  }

  async askQuestion(sessionId, question) {
    return await this.request(`/simulation/${sessionId}/question`, {
      method: 'POST',
      body: { question }
    });
  }

  async performExamination(sessionId, examType) {
    return await this.request(`/simulation/${sessionId}/examination`, {
      method: 'POST',
      body: { examination_type: examType }
    });
  }

  async orderInvestigation(sessionId, investigationId) {
    return await this.request(`/simulation/${sessionId}/investigation`, {
      method: 'POST',
      body: { investigation_id: investigationId }
    });
  }

  async updateDiagnosis(sessionId, differentialDiagnoses) {
    return await this.request(`/simulation/${sessionId}/diagnosis`, {
      method: 'POST',
      body: { differential_diagnoses: differentialDiagnoses }
    });
  }

  async submitFinalDiagnosis(sessionId, payload) {
    // payload: { final_diagnosis, immediate_priority, evidence_justification }
    return await this.request(`/simulation/${sessionId}/evaluate`, {
      method: 'POST',
      body: payload
    });
  }

  async getResults(sessionId) {
    return await this.request(`/simulation/${sessionId}/results`);
  }

  // Dashboard endpoints
  async getDashboard() {
    return await this.request('/dashboard');
  }
}

export const api = new ApiClient();
