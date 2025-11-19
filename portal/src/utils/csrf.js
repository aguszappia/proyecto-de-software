export const resolveCsrfToken = () => {
  if (typeof document === 'undefined') {
    return null
  }
  const candidates = ['csrf_access_token', 'csrf_refresh_token', 'csrf_token', 'XSRF-TOKEN']
  const cookieString = document.cookie || ''
  for (const name of candidates) {
    const match = cookieString.match(new RegExp(`(?:^|;\\s*)${name}=([^;]+)`, 'i'))
    if (match) {
      return decodeURIComponent(match[1])
    }
  }
  return null
}

export default resolveCsrfToken
