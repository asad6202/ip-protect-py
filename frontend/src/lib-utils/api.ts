import axios from 'axios'

// In Replit environment, use the window location origin to automatically detect the correct URL
const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || (typeof window !== 'undefined' ? `${window.location.origin}/api` : 'http://localhost:8000/api')

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // If the request data is FormData, delete the Content-Type header
    // to let Axios automatically set it with the correct boundary
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // Pass the original axios error through so we can access response data
    return Promise.reject(error)
  }
)

export default api
