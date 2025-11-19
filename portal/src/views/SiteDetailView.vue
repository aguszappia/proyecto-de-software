<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LMap, LMarker, LPopup, LTileLayer, LTooltip } from '@vue-leaflet/vue-leaflet'
import 'leaflet/dist/leaflet.css'
import API_BASE_URL from '@/constants/api'
import { useFavoritesStore } from '@/stores/favorites'
import { useAuthStore } from '@/stores/auth'
import { useFeatureFlagsStore } from '@/stores/featureFlags'
import { resolveCsrfToken } from '@/utils/csrf'

const route = useRoute()
const router = useRouter()

const site = ref(null)
const loading = ref(false)
const error = ref(null)
const descriptionExpanded = ref(false)
const galleryIndex = ref(0)
const DEFAULT_SITE_IMAGE =
  'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1200&q=60'

const normalizeSite = (payload) => {
  if (!payload) return null
  const tags = Array.isArray(payload.tags) ? payload.tags.filter(Boolean) : []
  const images = Array.isArray(payload.images) ? payload.images : []
  const normalizeImageEntry = (entry) => {
    if (!entry) return null
    if (typeof entry === 'string') {
      return { src: entry, alt: payload.name || 'Sitio histórico' }
    }
    if (typeof entry === 'object') {
      const src = entry.src || entry.url || entry.image_url || entry.imageUrl
      if (!src) {
        return null
      }
      return { src, alt: entry.alt || entry.title || payload.name || 'Sitio histórico' }
    }
    return null
  }

  const galleryImages = images.map(normalizeImageEntry).filter(Boolean)
  const coverImageSrc =
    payload.cover_image_url ||
    payload.coverImageUrl ||
    (typeof payload.cover_image === 'string' ? payload.cover_image : payload.cover_image?.url)
  if (coverImageSrc) {
    galleryImages.unshift({
      src: coverImageSrc,
      alt: payload.cover_image_title || payload.name || 'Sitio histórico',
    })
  }

  return {
    id: payload.id,
    name: payload.name,
    city: payload.city,
    province: payload.province,
    state: payload.state_of_conservation || payload.conservation_status || null,
    shortDescription: payload.short_description || '',
    fullDescription:
      payload.description || payload.full_description || payload.short_description || '',
    tags,
    latitude: typeof payload.lat === 'number' ? payload.lat : payload.latitude ?? null,
    longitude: typeof payload.long === 'number' ? payload.long : payload.longitude ?? null,
    updatedAt: payload.updated_at || payload.inserted_at || null,
    images: galleryImages,
    isFavorite: payload.is_favorite ?? payload.isFavorite ?? false,
  }
}

const favoritesStore = useFavoritesStore()
const auth = useAuthStore()
const featureFlags = useFeatureFlagsStore()
featureFlags.ensurePublicFlags()

const reviewsLoading = ref(false)
const reviewsError = ref('')
const reviews = ref([])
const reviewStats = ref({ average: null, total: 0 })
const userReview = ref(null)
const reviewForm = reactive({
  rating: '',
  comment: '',
})
const reviewErrors = ref({})
const reviewMessage = ref('')
const reviewMessageType = ref('success')
const reviewSubmitting = ref(false)
const reviewDeleting = ref(false)
const reviewDeleteConfirmVisible = ref(false)
const reviewHoverRating = ref(null)

const fromProfileView = computed(() => route.query.from === 'profile')
const fromHomeView = computed(() => route.query.from === 'home')
const backButtonLabel = computed(() => {
  if (fromProfileView.value) return '← Volver a mi perfil'
  if (fromHomeView.value) return '← Volver al home'
  return '← Volver al listado'
})

const REVIEW_MIN_LENGTH = 20
const REVIEW_MAX_LENGTH = 1000
const REVIEW_SCORE_OPTIONS = [1, 2, 3, 4, 5]

const normalizeReviewStatus = (value) => {
  if (!value) return ''
  const normalized = value.toString().trim().toLowerCase()
  if (normalized.includes('aproba') || normalized.includes('approved')) {
    return 'approved'
  }
  if (normalized.includes('pend')) {
    return 'pending'
  }
  if (normalized.includes('rechaz') || normalized.includes('reject')) {
    return 'rejected'
  }
  return normalized
}

const isApprovedStatus = (status) => normalizeReviewStatus(status) === 'approved'

const normalizeReviewEntry = (entry) => {
  if (!entry || typeof entry !== 'object') return null
  const rating = Number(entry.rating ?? entry.score)
  return {
    id: entry.id ?? entry.review_id ?? null,
    rating: Number.isFinite(rating) ? rating : null,
    comment: entry.comment ?? entry.text ?? '',
    status: normalizeReviewStatus(entry.status),
    authorName:
      entry.author_name ||
      entry.authorName ||
      entry.user_name ||
      entry.userName ||
      entry.user ||
      'Visitante',
    createdAt: entry.created_at || entry.createdAt || entry.updated_at || entry.inserted_at || null,
    rejectionReason: entry.rejection_reason || entry.rejectionReason || null,
  }
}

const toFiniteNumber = (value) => {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}
const selectedRatingValue = computed(() => {
  const parsed = toFiniteNumber(reviewForm.rating)
  return typeof parsed === 'number' ? parsed : 0
})

const displayedRatingValue = computed(() => {
  const hoverValue = toFiniteNumber(reviewHoverRating.value)
  if (typeof hoverValue === 'number') return hoverValue
  return selectedRatingValue.value
})

const handleRatingSelect = (score) => {
  reviewForm.rating = String(score)
  reviewHoverRating.value = null
  if (reviewErrors.value.rating) {
    const nextErrors = { ...reviewErrors.value }
    delete nextErrors.rating
    reviewErrors.value = nextErrors
  }
}

const handleRatingHover = (score) => {
  reviewHoverRating.value = score
}

const handleRatingLeave = () => {
  reviewHoverRating.value = null
}

const resetReviewForm = () => {
  reviewForm.rating = ''
  reviewForm.comment = ''
  reviewHoverRating.value = null
}

const syncReviewForm = () => {
  if (userReview.value) {
    reviewForm.rating = userReview.value.rating ? String(userReview.value.rating) : ''
    reviewForm.comment = userReview.value.comment || ''
  } else {
    resetReviewForm()
  }
}

watch(
  () => userReview.value,
  () => {
    syncReviewForm()
  },
  { immediate: true },
)

const formattedAverage = computed(() => {
  const value = reviewStats.value.average
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toFixed(1)
  }
  return null
})

const hasReviews = computed(() => reviews.value.length > 0)
const reviewsDisabled = computed(() => !featureFlags.reviewsEnabled)
const showReviewsDisabledNotice = computed(() => reviewsDisabled.value && auth.isAuthenticated)
const reviewsDisabledMessageLines = computed(() => {
  const message = featureFlags.reviewsDisabledMessage || ''
  return message.split(/\n+/).map((entry) => entry.trim()).filter(Boolean)
})

const pendingReviewNotice = computed(() => {
  const status = normalizeReviewStatus(userReview.value?.status)
  if (status === 'pending') {
    return 'Tu reseña está pendiente de aprobación. La mostraremos cuando finalice la revisión.'
  }
  return ''
})

const rejectedReviewNotice = computed(() => {
  const status = normalizeReviewStatus(userReview.value?.status)
  if (status !== 'rejected') {
    return ''
  }
  const reason = userReview.value?.rejectionReason || userReview.value?.rejection_reason
  return `Tu reseña fue rechazada: ${reason}. Editala para enviarla nuevamente a revisión.`
})

const formatReviewDate = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toLocaleDateString('es-AR', { day: 'numeric', month: 'short', year: 'numeric' })
}

const handleReviewLogin = () => {
  const nextUrl = typeof window !== 'undefined' ? window.location.href : '/'
  auth.requestLoginPrompt(nextUrl)
}

const fetchSiteReviews = async (siteId) => {
  if (!siteId) return
  reviewsLoading.value = true
  reviewsError.value = ''
  try {
    const response = await fetch(`${API_BASE_URL}/sites/${siteId}/reviews`, {
      credentials: 'include',
      headers: {
        Accept: 'application/json',
      },
    })
    if (!response.ok) {
      throw new Error('reviews_failed')
    }
    const payload = await response.json()
    const data = payload?.data ?? payload ?? {}
    const rawList =
      (Array.isArray(data.reviews) && data.reviews) ||
      (Array.isArray(payload?.reviews) && payload.reviews) ||
      (Array.isArray(data.data) && data.data) ||
      []

    const normalizedList = rawList
      .map((entry) => normalizeReviewEntry(entry))
      .filter((entry) => entry && isApprovedStatus(entry.status))

    reviews.value = normalizedList

    const statsSource = data.stats || data.meta || payload?.stats || payload?.meta || {}
    const rawAverage =
      statsSource.average_rating ?? statsSource.average ?? data.average_rating ?? payload?.average_rating ?? null
    const parsedAverage = toFiniteNumber(rawAverage)
    const rawTotal =
      statsSource.total_reviews ??
      statsSource.count ??
      data.total_reviews ??
      payload?.total_reviews ??
      normalizedList.length
    const parsedTotal = toFiniteNumber(rawTotal)

    reviewStats.value = {
      average: parsedAverage,
      total: typeof parsedTotal === 'number' ? parsedTotal : normalizedList.length,
    }

    const userEntry =
      data.user_review || data.userReview || payload?.user_review || payload?.userReview || null

    userReview.value = userEntry ? normalizeReviewEntry(userEntry) : null
    reviewErrors.value = {}
  } catch (error) {
    console.error('Error al cargar reseñas del sitio', error)
    reviewsError.value = 'No pudimos cargar las reseñas en este momento.'
    reviews.value = []
    reviewStats.value = { average: null, total: 0 }
    userReview.value = null
  } finally {
    reviewsLoading.value = false
  }
}

const handleReviewRetry = () => {
  const currentId = route.params.id
  if (currentId) {
    fetchSiteReviews(currentId)
  }
}

const validateReviewForm = () => {
  const errors = {}
  const ratingNumber = Number(reviewForm.rating)
  if (!Number.isInteger(ratingNumber) || ratingNumber < 1 || ratingNumber > 5) {
    errors.rating = 'Elegí un puntaje entre 1 y 5.'
  }
  const cleanComment = (reviewForm.comment || '').trim()
  if (!cleanComment) {
    errors.comment = `Escribí una reseña de al menos ${REVIEW_MIN_LENGTH} caracteres.`
  } else if (cleanComment.length < REVIEW_MIN_LENGTH) {
    errors.comment = `Tu reseña debe tener al menos ${REVIEW_MIN_LENGTH} caracteres.`
  } else if (cleanComment.length > REVIEW_MAX_LENGTH) {
    errors.comment = `La reseña no puede superar los ${REVIEW_MAX_LENGTH} caracteres.`
  }
  reviewErrors.value = errors
  return {
    isValid: Object.keys(errors).length === 0,
    ratingNumber,
    cleanComment,
  }
}

const mapServerErrors = (payload) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return {}
  }
  const mapped = {}
  Object.entries(payload).forEach(([field, detail]) => {
    if (Array.isArray(detail) && detail.length) {
      mapped[field] = detail[0]
    } else if (typeof detail === 'string') {
      mapped[field] = detail
    }
  })
  return mapped
}

const handleReviewSubmit = async () => {
  if (!site.value?.id) return
  if (!auth.isAuthenticated) {
    handleReviewLogin()
    return
  }
  const { isValid, ratingNumber, cleanComment } = validateReviewForm()
  if (!isValid) {
    return
  }
  reviewSubmitting.value = true
  reviewMessage.value = ''
  reviewMessageType.value = 'success'
  reviewErrors.value = {}
  try {
    const headers = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    }
    const csrfToken = resolveCsrfToken()
    if (csrfToken) {
      headers['X-CSRF-TOKEN'] = csrfToken
      headers['X-CSRFToken'] = csrfToken
    }
    const reviewId = userReview.value?.id
    const response = await fetch(
      reviewId
        ? `${API_BASE_URL}/sites/${site.value.id}/reviews/${reviewId}`
        : `${API_BASE_URL}/sites/${site.value.id}/reviews`,
      {
        method: reviewId ? 'PUT' : 'POST',
        credentials: 'include',
        headers,
        body: JSON.stringify({
          rating: ratingNumber,
          comment: cleanComment,
        }),
      },
    )
    if (response.status === 401) {
      handleReviewLogin()
      throw new Error('unauthorized')
    }
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => null)
      const mapped = mapServerErrors(errorPayload?.errors || errorPayload?.detail || errorPayload)
      if (Object.keys(mapped).length) {
        reviewErrors.value = mapped
        if (mapped.general) {
          reviewMessage.value = mapped.general
          reviewMessageType.value = 'error'
        }
      }
      throw new Error('review_failed')
    }
    const successMessage = userReview.value?.id
      ? 'Guardamos los cambios de tu reseña. Volverá a mostrarse cuando finalice la revisión.'
      : 'Gracias por compartir tu reseña. La publicaremos cuando sea aprobada.'
    reviewMessage.value = successMessage
    reviewMessageType.value = 'success'
    await fetchSiteReviews(site.value.id)
  } catch (error) {
    console.error('Error al guardar reseña', error)
    if (!reviewMessage.value) {
      reviewMessage.value = 'No pudimos guardar la reseña. Intentá nuevamente en unos minutos.'
      reviewMessageType.value = 'error'
    }
  } finally {
    reviewSubmitting.value = false
  }
}

const performReviewDelete = async () => {
  if (!site.value?.id || !userReview.value?.id) return
  reviewDeleting.value = true
  reviewMessage.value = ''
  reviewMessageType.value = 'success'
  try {
    const headers = {
      Accept: 'application/json',
    }
    const csrfToken = resolveCsrfToken()
    if (csrfToken) {
      headers['X-CSRF-TOKEN'] = csrfToken
      headers['X-CSRFToken'] = csrfToken
    }
    const response = await fetch(
      `${API_BASE_URL}/sites/${site.value.id}/reviews/${userReview.value.id}`,
      {
        method: 'DELETE',
        credentials: 'include',
        headers,
      },
    )
    if (response.status === 401) {
      handleReviewLogin()
      throw new Error('unauthorized')
    }
    if (!response.ok && response.status !== 204) {
      throw new Error('delete_failed')
    }
    reviewMessage.value = 'Eliminamos tu reseña.'
    reviewMessageType.value = 'success'
    await fetchSiteReviews(site.value.id)
  } catch (error) {
    console.error('Error al eliminar reseña', error)
    reviewMessage.value = 'No pudimos eliminar la reseña. Intentá nuevamente.'
    reviewMessageType.value = 'error'
  } finally {
    reviewDeleting.value = false
  }
}

const openReviewDeleteConfirm = () => {
  if (!site.value?.id || !userReview.value?.id) return
  reviewDeleteConfirmVisible.value = true
}

const closeReviewDeleteConfirm = () => {
  if (reviewDeleting.value) return
  reviewDeleteConfirmVisible.value = false
}

const confirmReviewDelete = async () => {
  if (!reviewDeleteConfirmVisible.value) return
  reviewDeleteConfirmVisible.value = false
  await performReviewDelete()
}

const fetchSiteDetails = async (id) => {
  if (!id) return
  loading.value = true
  error.value = null
  site.value = null
  descriptionExpanded.value = false
  galleryIndex.value = 0
  try {
    const response = await fetch(`${API_BASE_URL}/sites/${id}`, {
      credentials: 'include',
    })
    if (response.status === 404) {
      throw new Error('not_found')
    }
    if (!response.ok) {
      throw new Error('server_error')
    }
    const payload = await response.json()
    site.value = normalizeSite(payload)
    if (site.value?.id) {
      favoritesStore.applyFavorite(site.value.id, Boolean(site.value.isFavorite))
    }
  } catch (err) {
    error.value = err.message === 'not_found' ? 'El sitio no existe o no es público.' : null
    if (!error.value) {
      error.value = 'No pudimos cargar la información. Intentá nuevamente en unos minutos.'
    }
  } finally {
    loading.value = false
  }
}

watch(
  () => route.params.id,
  (newId) => {
    if (newId) {
      fetchSiteDetails(newId)
    }
  },
  { immediate: true },
)

watch(
  () => route.params.id,
  (newId) => {
    if (newId) {
      fetchSiteReviews(newId)
    }
  },
  { immediate: true },
)

watch(
  () => auth.isAuthenticated,
  () => {
    if (site.value?.id) {
      fetchSiteReviews(site.value.id)
    }
  },
)

const galleryImages = computed(() => {
  if (!site.value) return []
  const pool = Array.isArray(site.value.images) ? site.value.images : []
  if (!pool.length) {
    return [
      {
        src: DEFAULT_SITE_IMAGE,
        alt: `Vista referencial de ${site.value.name || 'sitio histórico'}`,
      },
    ]
  }
  return pool
})

watch(galleryImages, () => {
  galleryIndex.value = 0
})

const selectedImage = computed(() => galleryImages.value[galleryIndex.value] || null)

const formatStateLabel = (value) => {
  if (!value) return 'Estado sin datos'
  const normalized = String(value)
    .replace(/_/g, ' ')
    .toLowerCase()
  return normalized.charAt(0).toUpperCase() + normalized.slice(1)
}

const stateLabel = computed(() => formatStateLabel(site.value?.state))

const stateChipClass = computed(() => {
  const value = (site.value?.state || '').toString().toLowerCase()
  if (value.includes('excelente') || value.includes('bueno')) return 'detail-chip--good'
  if (value.includes('regular')) return 'detail-chip--warning'
  if (value.includes('malo') || value.includes('bad')) return 'detail-chip--bad'
  return 'detail-chip--neutral'
})

const locationLabel = computed(() => {
  const city = site.value?.city
  const province = site.value?.province
  if (city && province) return `${city}, ${province}`
  return city || province || 'Ubicación pendiente'
})

const hasDescription = computed(
  () => Boolean(site.value?.shortDescription) || Boolean(site.value?.fullDescription),
)

const DESCRIPTION_COLLAPSE_AT = 420

const longDescription = computed(() => site.value?.fullDescription || '')

const displayedDescription = computed(() => {
  const description = longDescription.value
  if (!description) return ''
  if (descriptionExpanded.value || description.length <= DESCRIPTION_COLLAPSE_AT) {
    return description
  }
  return `${description.slice(0, DESCRIPTION_COLLAPSE_AT)}…`
})

const canToggleDescription = computed(
  () => (longDescription.value?.length || 0) > DESCRIPTION_COLLAPSE_AT,
)

const coordinates = computed(() => {
  const lat = site.value?.latitude
  const lon = site.value?.longitude
  if (typeof lat !== 'number' || typeof lon !== 'number') {
    return null
  }
  return [lat, lon]
})

const MAP_DEFAULT_ZOOM = 8
const mapZoom = computed(() => {
  if (!coordinates.value) return 5
  if (site.value?.city) return MAP_DEFAULT_ZOOM
  return 11
})

const popupDescription = computed(() => {
  if (site.value?.shortDescription) {
    return site.value.shortDescription
  }
  if (site.value?.fullDescription) {
    return site.value.fullDescription.slice(0, 120)
  }
  return 'Pronto sumaremos la descripción de este sitio.'
})

const handleGalleryNav = (direction) => {
  if (!galleryImages.value.length) return
  const total = galleryImages.value.length
  galleryIndex.value = (galleryIndex.value + direction + total) % total
}

const isFavorite = computed(() => {
  if (!site.value?.id) return false
  return favoritesStore.isFavorite(site.value.id)
})

const favoritePending = computed(() => {
  if (!site.value?.id) return false
  return favoritesStore.isPending(site.value.id)
})

const handleFavoriteToggle = async () => {
  if (!site.value?.id || favoritePending.value) return
  if (!auth.isAuthenticated) {
    const nextUrl = typeof window !== 'undefined' ? window.location.href : '/'
    auth.requestLoginPrompt(nextUrl)
    return
  }
  await favoritesStore.toggleFavorite(site.value.id)
  site.value = {
    ...site.value,
    isFavorite: favoritesStore.isFavorite(site.value.id),
  }
}

const handleBackClick = () => {
  if (fromProfileView.value) {
    router.push({ name: 'profile' })
    return
  }
  if (fromHomeView.value) {
    router.push({ name: 'home' })
    return
  }
  const nextQuery = { ...route.query }
  delete nextQuery.from
  router.push({
    name: 'sites',
    query: nextQuery,
  })
}

const handleTagClick = (tag) => {
  if (!tag) return
  router.push({
    name: 'sites',
    query: {
      ...route.query,
      tags: tag,
    },
  })
}

const handleRetry = () => {
  fetchSiteDetails(route.params.id)
}
</script>

<template>
  <section class="site-detail view-panel">
    <button class="site-detail__back secondary-button" type="button" @click="handleBackClick">
      {{ backButtonLabel }}
    </button>

    <div v-if="loading" class="view-panel__card detail__content">
      <p>Cargando información del sitio…</p>
    </div>

    <div v-else-if="error" class="view-panel__card detail__content">
      <p class="detail__note">{{ error }}</p>
      <div class="view-panel__actions">
        <button class="primary-button" type="button" @click="handleRetry">Reintentar</button>
      </div>
    </div>

    <template v-else-if="site">
      <article class="site-detail__hero view-panel__card">
        <header class="site-detail__header">
          <p class="view-panel__subtitle">Sitio seleccionado</p>
          <h1>{{ site.name }}</h1>
          <p class="site-detail__location">{{ locationLabel }}</p>
          <button
            v-if="site.id"
            class="detail-favorite-icon"
            type="button"
            :class="{ 'detail-favorite-icon--active': isFavorite }"
            :aria-pressed="isFavorite"
            :disabled="favoritePending"
            @click="handleFavoriteToggle"
            title="Marcar como favorito"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
              />
            </svg>
          </button>
        </header>

        <div class="site-detail__meta">
          <span class="detail-chip" :class="stateChipClass">{{ stateLabel }}</span>
          <p v-if="site.updatedAt" class="site-detail__updated">
            Última actualización: {{ new Date(site.updatedAt).toLocaleDateString('es-AR') }}
          </p>
        </div>
      </article>

      <article v-if="selectedImage" class="site-detail__gallery view-panel__card">
        <figure class="gallery__image">
          <img :src="selectedImage.src" :alt="selectedImage.alt" loading="lazy" />
        </figure>
        <div v-if="galleryImages.length > 1" class="gallery__controls">
          <button
            type="button"
            class="gallery__arrow"
            aria-label="Ver imagen anterior"
            @click="handleGalleryNav(-1)"
          >
            ‹
          </button>
          <div class="gallery__indicators" role="tablist" aria-label="Seleccionar imagen">
            <button
              v-for="(image, index) in galleryImages"
              :key="image.src"
              class="gallery__indicator"
              :class="{ 'gallery__indicator--active': galleryIndex === index }"
              type="button"
              :aria-label="`Ver imagen ${index + 1}`"
              @click="galleryIndex = index"
            />
          </div>
          <button
            type="button"
            class="gallery__arrow"
            aria-label="Ver imagen siguiente"
            @click="handleGalleryNav(1)"
          >
            ›
          </button>
        </div>
      </article>

      <article v-if="hasDescription" class="site-detail__description view-panel__card">
        <p v-if="site.shortDescription" class="site-detail__summary">{{ site.shortDescription }}</p>
        <p v-if="longDescription" class="site-detail__full">{{ displayedDescription }}</p>
        <button
          v-if="canToggleDescription"
          class="secondary-button description__toggle"
          type="button"
          @click="descriptionExpanded = !descriptionExpanded"
        >
          {{ descriptionExpanded ? 'Ver menos' : 'Ver más' }}
        </button>
      </article>

      <article v-if="site.tags?.length" class="site-detail__tags view-panel__card">
        <p class="view-panel__subtitle">Etiquetas</p>
        <ul class="site-detail__tag-list">
          <li v-for="tag in site.tags" :key="tag">
            <button class="tag-pill" type="button" @click="handleTagClick(tag)">#{{ tag }}</button>
          </li>
        </ul>
      </article>

      <article class="site-detail__reviews view-panel__card">
        <header class="reviews-header">
          <div>
            <p class="view-panel__subtitle">Reseñas</p>
            <h2>Experiencias de la comunidad</h2>
          </div>
          <div class="reviews-summary">
            <p v-if="formattedAverage" class="reviews-summary__average">
              {{ formattedAverage }}
              <span>promedio</span>
            </p>
          </div>
        </header>

        <div v-if="reviewsLoading" class="reviews-empty">
          Cargando reseñas…
        </div>
        <div v-else-if="reviewsError" class="reviews-empty">
          <p>{{ reviewsError }}</p>
          <button class="secondary-button" type="button" @click="handleReviewRetry">Reintentar</button>
        </div>
        <ul v-else-if="hasReviews" class="review-list">
          <li
            v-for="(reviewItem, index) in reviews"
            :key="reviewItem.id || `review-${index}`"
            class="review-card"
          >
            <div class="review-card__heading">
              <div class="review-card__rating" :aria-label="`Puntuación ${reviewItem.rating} de 5`">
                <span
                  v-for="star in 5"
                  :key="`star-${reviewItem.id || index}-${star}`"
                  class="review-star"
                  :class="{ 'review-star--filled': star <= (reviewItem.rating || 0) }"
                  aria-hidden="true"
                >
                  <svg viewBox="0 0 24 24">
                    <path
                      d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
                    />
                  </svg>
                </span>
                <strong>{{ reviewItem.rating ?? '-' }}/5</strong>
              </div>
              <div class="review-card__meta">
                <p class="review-card__author">{{ reviewItem.authorName }}</p>
                <time v-if="formatReviewDate(reviewItem.createdAt)" class="review-card__date">
                  {{ formatReviewDate(reviewItem.createdAt) }}
                </time>
              </div>
            </div>
            <p class="review-card__comment">{{ reviewItem.comment }}</p>
          </li>
        </ul>
        <p v-else class="reviews-empty">
          Aún no hay reseñas aprobadas para mostrar.
        </p>

        <div class="review-separator" aria-hidden="true"></div>

        <div
          v-if="showReviewsDisabledNotice"
          class="reviews-auth-hint reviews-disabled-hint"
          role="status"
        >
          <p v-for="(line, index) in reviewsDisabledMessageLines" :key="`reviews-disabled-${index}`">
            {{ line }}
          </p>
        </div>
        <div v-else-if="auth.isAuthenticated" class="review-form">
          <h3>{{ userReview ? 'Editar mi reseña' : 'Escribir una reseña' }}</h3>
          <p v-if="pendingReviewNotice" class="review-form__notice">
            {{ pendingReviewNotice }}
          </p>
          <p v-if="rejectedReviewNotice" class="review-form__notice review-form__notice--error">
            {{ rejectedReviewNotice }}
          </p>
          <p v-if="reviewMessage" :class="['review-alert', `review-alert--${reviewMessageType}`]">
            {{ reviewMessage }}
          </p>
          <form class="review-form__grid" @submit.prevent="handleReviewSubmit">
            <label>
              Puntuación
              <div class="rating-input">
                <div
                  class="rating-input__stars"
                  role="radiogroup"
                  aria-label="Seleccionar una puntuación entre 1 y 5 estrellas"
                  @mouseleave="handleRatingLeave"
                >
                  <button
                    v-for="score in REVIEW_SCORE_OPTIONS"
                    :key="score"
                    class="rating-input__star"
                    type="button"
                    role="radio"
                    :aria-checked="selectedRatingValue === score"
                    :aria-label="`${score} ${score === 1 ? 'estrella' : 'estrellas'}`"
                    :class="{ 'rating-input__star--filled': score <= displayedRatingValue }"
                    @mouseenter="handleRatingHover(score)"
                    @focus="handleRatingHover(score)"
                    @mouseleave="handleRatingLeave"
                    @blur="handleRatingLeave"
                    @click="handleRatingSelect(score)"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path
                        d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
                      />
                    </svg>
                  </button>
                </div>
                <span class="rating-input__value" aria-live="polite">
                  {{ selectedRatingValue ? `${selectedRatingValue} / 5` : 'Sin seleccionar' }}
                </span>
              </div>
              <small v-if="reviewErrors.rating" class="review-error">{{ reviewErrors.rating }}</small>
            </label>
            <label>
              Comentario
              <textarea
                v-model="reviewForm.comment"
                rows="4"
                maxlength="1000"
                placeholder="Contanos tu experiencia para ayudar a otros visitantes"
              ></textarea>
              <small v-if="reviewErrors.comment" class="review-error">{{ reviewErrors.comment }}</small>
            </label>
            <div class="review-form__actions">
              <button class="primary-button" type="submit" :disabled="reviewSubmitting">
                {{
                  reviewSubmitting
                    ? 'Guardando…'
                    : userReview
                      ? 'Actualizar reseña'
                      : 'Enviar reseña'
                }}
              </button>
              <button
                v-if="userReview"
                class="secondary-button"
                type="button"
                :disabled="reviewDeleting || reviewSubmitting"
                @click="openReviewDeleteConfirm"
              >
                {{ reviewDeleting ? 'Eliminando…' : 'Eliminar reseña' }}
              </button>
            </div>
            <p class="review-form__hint">
              Solo listamos reseñas aprobadas. Si editás la tuya vuelve a estado pendiente.
            </p>
          </form>
        </div>
        <div v-else class="reviews-auth-hint">
          <p>Iniciá sesión para compartir tu reseña sobre este sitio.</p>
          <p class="review-form__hint">
            Mostramos una reseña por usuario. Si ya escribiste una, la podrás editar después de ingresar.
          </p>
          <button class="primary-button" type="button" @click="handleReviewLogin">Ingresar con Google</button>
        </div>
      </article>

      <article class="site-detail__map view-panel__card">
        <p class="view-panel__subtitle">Ubicación</p>
        <p v-if="!coordinates" class="detail__note">
          Este sitio todavía no tiene coordenadas para mostrar en el mapa.
        </p>
        <div v-else class="site-detail__map-canvas">
          <l-map class="site-detail__leaflet" :zoom="mapZoom" :center="coordinates" :zoom-control="false">
            <l-tile-layer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <l-marker :lat-lng="coordinates">
              <l-popup>
                <strong>{{ site.name }}</strong>
                <p>{{ popupDescription }}</p>
              </l-popup>
              <l-tooltip sticky>{{ site.name }}</l-tooltip>
            </l-marker>
          </l-map>
        </div>
      </article>
    </template>
  </section>
  <div
    v-if="reviewDeleteConfirmVisible"
    class="public-modal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="review-delete-title"
  >
    <div class="public-modal__backdrop"></div>
    <div class="public-modal__card" role="document">
      <h2 id="review-delete-title">Eliminar reseña</h2>
      <p>Esta acción no se puede deshacer. ¿Querés eliminar tu reseña?</p>
      <div class="public-modal__actions">
        <button class="public-modal__button" type="button" @click="closeReviewDeleteConfirm" :disabled="reviewDeleting">
          Cancelar
        </button>
        <button
          class="public-modal__button public-modal__button--danger"
          type="button"
          :disabled="reviewDeleting"
          @click="confirmReviewDelete"
        >
          {{ reviewDeleting ? 'Eliminando…' : 'Eliminar' }}
        </button>
      </div>
    </div>
  </div>
</template>
