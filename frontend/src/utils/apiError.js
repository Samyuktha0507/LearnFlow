/** Normalize FastAPI / axios error payloads for display */
export function formatApiError(err) {
  if (!err?.response) {
    if (err?.code === 'ECONNABORTED') {
      return 'Request timed out. If you were generating a plan, wait and try again.';
    }
    return (
      'Cannot reach the API. Start it from the project folder: ' +
      'python -m uvicorn main:app --host 127.0.0.1 --port 8000'
    );
  }
  const d = err.response.data?.detail;
  if (d == null) {
    return err.response.statusText || err.message || 'Request failed';
  }
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    return d.map((e) => (typeof e === 'object' && e.msg ? e.msg : JSON.stringify(e))).join('. ');
  }
  return String(d);
}
