const normalizeImageSource = (value) => {
  if (!value) return null
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length ? trimmed : null
  }
  if (typeof value === 'object') {
    if (typeof value.url === 'string' && value.url.trim().length) {
      return value.url
    }
    if (typeof value.src === 'string' && value.src.trim().length) {
      return value.src
    }
  }
  return null
}

export const resolveSiteImageSrc = (site, fallback) => {
  if (!site || typeof site !== 'object') {
    return fallback
  }
  const candidates = [
    site.cover_image_url,
    site.coverImageUrl,
    site.cover_image,
    site.coverImage,
    site.image_url,
    site.imageUrl,
  ]

  if (Array.isArray(site.images)) {
    site.images.forEach((image) => {
      candidates.push(image)
      if (image && typeof image === 'object') {
        candidates.push(image.url, image.src)
      }
    })
  }

  const match = candidates.map(normalizeImageSource).find(Boolean)
  return match || fallback
}

export const resolveSiteImageAlt = (site, fallback = 'Sitio histórico') =>
  (site?.cover_image_title || site?.coverImageTitle || site?.name || fallback).trim()

export default {
  resolveSiteImageSrc,
  resolveSiteImageAlt,
}
