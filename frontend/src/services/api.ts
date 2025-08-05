import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Document {
  id: number;
  filename: string;
  upload_timestamp: string;
  processing_status: string;
  ocr_confidence?: number;
  extraction_confidence?: number;
  requires_review: boolean;
  review_completed: boolean;
}

export interface DocumentDetail extends Document {
  extracted_fields: Record<string, any>;
  field_extractions: FieldExtraction[];
}

export interface FieldExtraction {
  field_name: string;
  field_value: string;
  confidence_score: number;
  is_required: boolean;
}

export interface ReviewDocument {
  document_id: number;
  filename: string;
  ocr_text: string;
  required_fields: Record<string, { value: string; confidence: number }>;
  optional_fields: Record<string, { value: string; confidence: number }>;
  overall_confidence: number;
}

export interface LLMProvider {
  models: string[];
  default_model?: string;
}

export interface LLMConfig {
  providers: Record<string, LLMProvider>;
  default_provider: string;
}

export const documentApi = {
  // Upload document
  uploadDocument: async (file: File): Promise<{ document_id: number; filename: string; status: string; message: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },

  // Get documents list
  getDocuments: async (skip = 0, limit = 100, status?: string): Promise<Document[]> => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });
    
    if (status) {
      params.append('status', status);
    }
    
    const response = await api.get(`/documents?${params}`);
    return response.data;
  },

  // Get document details
  getDocument: async (documentId: number): Promise<DocumentDetail> => {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  },

  // Get document for review
  getDocumentForReview: async (documentId: number): Promise<ReviewDocument> => {
    const response = await api.get(`/documents/${documentId}/review`);
    return response.data;
  },

  // Get LLM configuration
  getLLMConfig: async (): Promise<LLMConfig> => {
    const response = await api.get('/config/llm-providers');
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<{ status: string; timestamp: string; services: any }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

// Error handling interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.detail || error.response.data?.message || 'An error occurred';
      throw new Error(message);
    } else if (error.request) {
      // Request was made but no response received
      throw new Error('Unable to connect to server. Please check your connection.');
    } else {
      // Something else happened
      throw new Error('An unexpected error occurred');
    }
  }
);

export default api;