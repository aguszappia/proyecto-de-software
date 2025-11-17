export const resolveCsrfToken = () => {
  if (typeof document === 'undefined') {
    return null
  }
  const match = document.cookie.match(/(?:^|;\s*)(csrf_token|XSRF-TOKEN)=([^;]+)/i)
  return match ? decodeURIComponent(match[2]) : null
}

export default resolveCsrfToken
