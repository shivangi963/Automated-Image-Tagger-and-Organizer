export default function getErrorMessage(err) {
  const data = err?.response?.data;

  // 1) New normalized shape: { message, errors: [...] }
  if (data && typeof data === 'object') {
    if (data.message) return data.message;
    // try errors array of objects
    if (Array.isArray(data.errors) && data.errors.length) {
      const msgs = data.errors.map(e => e?.msg || e?.message || JSON.stringify(e)).filter(Boolean);
      if (msgs.length) return msgs.join('; ');
    }
    // FastAPI default shape: { detail: "..." } or [{...}, ...]
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail) && data.detail.length) {
      const msgs = data.detail.map(d => d?.msg || d?.message || JSON.stringify(d)).filter(Boolean);
      if (msgs.length) return msgs.join('; ');
    }
    // flatten other possible structures
    const vals = Object.values(data).flatMap(v => (typeof v === 'string' ? v : (v?.msg || v?.message || JSON.stringify(v))));
    if (vals.length) return vals.join('; ');
  }

  // fallback: axios / network message
  return err?.message || 'An unexpected error occurred';
}