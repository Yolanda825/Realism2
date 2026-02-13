import axios from 'axios'

// Post image to backend /enhance and return parsed JSON result
export async function postEnhance(file) {
  const form = new FormData()
  form.append('file', file)
  const resp = await axios.post('/enhance', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return resp.data
}

// Track event helper
export function trackEvent(eventName, data = {}) {
  fetch('/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event: eventName, data }),
  }).catch(() => {})
}
