const API_BASE_URL =
  import.meta.env.VITE_PUBLIC_API_BASE_URL ||
  (window.location.origin.includes('localhost:5173')
    ? 'http://localhost:5050/api'
    : 'https://admin-grupo28.proyecto2025.linti.unlp.edu.ar/api')

const AUTH_BASE_URL =
  import.meta.env.VITE_PUBLIC_AUTH_BASE_URL ||
  API_BASE_URL.replace(/\/api\/?$/, '')

export { AUTH_BASE_URL }
export default API_BASE_URL
