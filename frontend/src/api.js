import axios from 'axios';

/**
 * - Production: set VITE_API_URL to your API origin (e.g. https://api.example.com)
 * - Dev: defaults to http://127.0.0.1:8000 so login works even if the Vite proxy fails
 */
function getApiBase() {
  const env = import.meta.env.VITE_API_URL;
  if (env != null && String(env).trim() !== '') {
    return String(env).replace(/\/$/, '');
  }
  if (import.meta.env.DEV) {
    return 'http://127.0.0.1:8000';
  }
  return '';
}

const api = axios.create({
  baseURL: getApiBase(),
  timeout: 120000,
});

export default api;
