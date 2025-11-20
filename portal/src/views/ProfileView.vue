<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import SiteCard from '@/components/SiteCard.vue'
import { useAuthStore } from '@/stores/auth'
import { useFavoritesStore } from '@/stores/favorites'
import API_BASE_URL from '@/constants/api'
import { resolveSiteImageAlt, resolveSiteImageSrc } from '@/siteMedia'

const auth = useAuthStore()
const router = useRouter()
const favoritesStore = useFavoritesStore()

const favoriteSites = ref([])
const favoritesLoading = ref(false)
const favoritesError = ref('')
const userReviews = ref([])
const userReviewsLoading = ref(false)
const userReviewsError = ref('')
let suppressFavoriteWatch = false
const FAVORITES_PAGE_SIZE = 25
const REVIEWS_PAGE_SIZE = 25
const favoritesPagination = ref({
  page: 1,
  per_page: FAVORITES_PAGE_SIZE,
  total: 0,
  pages: 1,
})
const reviewsPagination = ref({
  page: 1,
  per_page: REVIEWS_PAGE_SIZE,
  total: 0,
  pages: 1,
})

const GENERIC_SITE_IMAGE_URL =
  'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1200&q=60'

const normalizeFavoriteSite = (site) => ({
  id: site.id,
  name: site.name,
  city: site.city,
  province: site.province,
  state:
    site.state_of_conservation ??
    site.conservation_status ??
    site.state ??
    null,
  rating:
    typeof site.rating === 'number'
      ? site.rating
      : site.average_rating ?? site.averageRating ?? null,
  tags: Array.isArray(site.tags) ? site.tags.slice(0, 5) : [],
  image: resolveSiteImageSrc(site, GENERIC_SITE_IMAGE_URL),
  imageAlt: resolveSiteImageAlt(site),
  href: site.id ? { name: 'site-detail', params: { id: site.id }, query: { from: 'profile' } } : null,
})

const normalizeReviewStatus = (value) => {
  if (!value) return ''
  const normalized = value.toString().trim().toLowerCase()
  if (normalized.includes('aproba') || normalized.includes('approved')) {
    return 'approved'
  }
  if (normalized.includes('rechaz') || normalized.includes('reject')) {
    return 'rejected'
  }
  if (normalized.includes('pend')) {
    return 'pending'
  }
  return normalized
}

const resolveReviewStatusVariant = (status) => {
  const normalized = normalizeReviewStatus(status)
  if (normalized === 'approved') return 'approved'
  if (normalized === 'rejected') return 'rejected'
  return 'pending'
}

const resolveReviewStatusLabel = (status) => {
  const variant = resolveReviewStatusVariant(status)
  if (variant === 'approved') return 'Aprobada'
  if (variant === 'rejected') return 'Rechazada'
  return 'En revisión'
}

const toFiniteNumber = (value) => {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

const normalizeUserReview = (review) => {
  if (!review || typeof review !== 'object') return null
  const site = review.site || review.place || review.location || review.site_data || {}
  const rating = toFiniteNumber(review.rating ?? review.score)
  return {
    id: review.id ?? review.review_id ?? null,
    siteId: site.id ?? review.site_id ?? review.siteId ?? null,
    siteName: site.name || review.site_name || review.siteName || 'Sitio histórico',
    siteCity: site.city || review.site_city || review.siteCity || '',
    siteProvince: site.province || review.site_province || review.siteProvince || '',
    rating: typeof rating === 'number' ? rating : null,
    comment: (review.comment || review.text || '').trim(),
    status: normalizeReviewStatus(review.status),
    createdAt: review.created_at || review.createdAt || review.updated_at || review.inserted_at || null,
  }
}

const formatReviewDate = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toLocaleDateString('es-AR', { day: 'numeric', month: 'short', year: 'numeric' })
}

const userReviewList = computed(() => userReviews.value.filter(Boolean))

const resolvedProfileRoute = computed(() => {
  if (typeof window === 'undefined') {
    return '/perfil'
  }
  const resolved = router.resolve({ name: 'profile' })
  return `${window.location.origin}${resolved.href}`
})

const handleProfileLogin = () => {
  auth.loginWithGoogle(resolvedProfileRoute.value)
}

const goToFavoritesPage = (targetPage) => {
  const safePage = Math.max(1, Math.min(targetPage, favoritesPagination.value.pages || targetPage))
  loadFavoriteSites(safePage)
}

const loadFavoriteSites = async (page = 1) => {
  if (!auth.isAuthenticated) {
    favoriteSites.value = []
    favoritesError.value = ''
    favoritesLoading.value = false
    favoritesPagination.value = {
      page: 1,
      per_page: FAVORITES_PAGE_SIZE,
      total: 0,
      pages: 1,
    }
    return
  }

  favoritesLoading.value = true
  favoritesError.value = ''
  const params = new URLSearchParams({
    filter: 'favorites',
    per_page: String(FAVORITES_PAGE_SIZE),
    page: String(page),
    order_by: 'latest',
  })

  try {
    const response = await fetch(`${API_BASE_URL}/sites?${params.toString()}`, {
      credentials: 'include',
    })
    if (!response.ok) {
      throw new Error('No pudimos cargar tus sitios favoritos. Intentá más tarde.')
    }
    const payload = await response.json()
    const items = Array.isArray(payload?.data) ? payload.data : []
    const meta = payload?.meta || {}
    favoritesPagination.value = {
      page: Number(meta.page) || page,
      per_page: Number(meta.per_page) || FAVORITES_PAGE_SIZE,
      total: Number(meta.total) || items.length,
      pages: Number(meta.pages) || Math.max(1, Math.ceil((Number(meta.total) || items.length) / FAVORITES_PAGE_SIZE)),
    }
    suppressFavoriteWatch = true
    favoritesStore.hydrateFromSites(items)
    favoriteSites.value = items.map(normalizeFavoriteSite)
  } catch (error) {
    favoritesError.value = error.message || 'No pudimos cargar tus favoritos.'
  } finally {
    suppressFavoriteWatch = false
    favoritesLoading.value = false
  }
}

const favoriteCards = computed(() =>
  favoriteSites.value.filter((site) => favoritesStore.isFavorite(site.id)),
)

const favoriteCanPrev = computed(() => (favoritesPagination.value.page || 1) > 1)
const favoriteCanNext = computed(
  () => (favoritesPagination.value.page || 1) < (favoritesPagination.value.pages || 1),
)
const favoritePaginationLabel = computed(() => {
  const total = favoritesPagination.value.total || 0
  if (!total) return 'Sin favoritos'
  const page = favoritesPagination.value.page || 1
  const pages = favoritesPagination.value.pages || 1
  return `Mostrando ${page} de ${pages}`
})

const reviewsCanPrev = computed(() => (reviewsPagination.value.page || 1) > 1)
const reviewsCanNext = computed(
  () => (reviewsPagination.value.page || 1) < (reviewsPagination.value.pages || 1),
)
const reviewsPaginationLabel = computed(() => {
  const total = reviewsPagination.value.total || 0
  if (!total) return 'Sin reseñas'
  const page = reviewsPagination.value.page || 1
  const pages = reviewsPagination.value.pages || 1
  return `Mostrando ${page} de ${pages}`
})

const goToReviewsPage = (targetPage) => {
  const safePage = Math.max(1, Math.min(targetPage, reviewsPagination.value.pages || targetPage))
  loadUserReviews(safePage)
}

const loadUserReviews = async (page = 1) => {
  if (!auth.isAuthenticated) {
    userReviews.value = []
    userReviewsError.value = ''
    userReviewsLoading.value = false
    reviewsPagination.value = {
      page: 1,
      per_page: REVIEWS_PAGE_SIZE,
      total: 0,
      pages: 1,
    }
    return
  }

  userReviewsLoading.value = true
  userReviewsError.value = ''
  try {
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(REVIEWS_PAGE_SIZE),
    })
    const response = await fetch(`${API_BASE_URL}/me/reviews?${params.toString()}`, {
      credentials: 'include',
      headers: {
        Accept: 'application/json',
      },
    })
    if (!response.ok) {
      throw new Error('No pudimos cargar tus reseñas. Intentá más tarde.')
    }
    const payload = await response.json()
    const rawList =
      (Array.isArray(payload?.data) && payload.data) ||
      (Array.isArray(payload?.reviews) && payload.reviews) ||
      (Array.isArray(payload) && payload) ||
      []
    userReviews.value = rawList.map((entry) => normalizeUserReview(entry)).filter(Boolean)
    const meta = payload?.meta || {}
    reviewsPagination.value = {
      page: Number(meta.page) || page,
      per_page: Number(meta.per_page) || REVIEWS_PAGE_SIZE,
      total: Number(meta.total) || rawList.length,
      pages:
        Number(meta.pages) ||
        Math.max(1, Math.ceil((Number(meta.total) || rawList.length) / REVIEWS_PAGE_SIZE)),
    }
  } catch (error) {
    console.error('Error al cargar reseñas del perfil', error)
    userReviewsError.value = error.message || 'No pudimos cargar tus reseñas.'
    userReviews.value = []
  } finally {
    userReviewsLoading.value = false
  }
}

const handleRefreshFavorites = () => {
  if (!favoritesLoading.value) {
    loadFavoriteSites(favoritesPagination.value.page || 1)
  }
}

const handleRefreshUserReviews = () => {
  if (!userReviewsLoading.value) {
    loadUserReviews(reviewsPagination.value.page || 1)
  }
}

const handleFavoritesPrev = () => {
  if (!favoriteCanPrev.value) return
  goToFavoritesPage((favoritesPagination.value.page || 1) - 1)
}

const handleFavoritesNext = () => {
  if (!favoriteCanNext.value) return
  goToFavoritesPage((favoritesPagination.value.page || 1) + 1)
}

const handleReviewsPrev = () => {
  if (!reviewsCanPrev.value) return
  goToReviewsPage((reviewsPagination.value.page || 1) - 1)
}

const handleReviewsNext = () => {
  if (!reviewsCanNext.value) return
  goToReviewsPage((reviewsPagination.value.page || 1) + 1)
}

watch(
  () => auth.isAuthenticated,
  (logged) => {
    if (logged) {
      loadFavoriteSites()
      loadUserReviews()
    } else {
      favoriteSites.value = []
      userReviews.value = []
      favoritesPagination.value = {
        page: 1,
        per_page: FAVORITES_PAGE_SIZE,
        total: 0,
        pages: 1,
      }
      reviewsPagination.value = {
        page: 1,
        per_page: REVIEWS_PAGE_SIZE,
        total: 0,
        pages: 1,
      }
    }
  },
)

onMounted(() => {
  if (auth.isAuthenticated) {
    loadFavoriteSites()
    loadUserReviews()
  }
})

watch(
  () => favoritesStore.favoriteIds.length,
  (newCount, oldCount) => {
    if (!auth.isAuthenticated || suppressFavoriteWatch) return
    if (newCount > oldCount) {
      loadFavoriteSites()
    } else {
      favoriteSites.value = favoriteSites.value.filter((site) =>
        favoritesStore.isFavorite(site.id),
      )
    }
  },
)
</script>

<template>
  <section class="view-panel profile-view">
    <div
      v-if="!auth.isAuthenticated"
      class="view-panel__card profile-card view-panel__card--centered"
    >
      <h2>Necesitás iniciar sesión</h2>
      <p>Iniciá sesión para acceder a tu perfil y a tus contenidos guardados.</p>
      <button class="primary-button" type="button" @click="handleProfileLogin">
        Ingresar con Google
      </button>
    </div>

    <div v-else class="view-panel__card profile-card">
      <div class="profile-card__header">
        <div class="profile-avatar" aria-hidden="true">
          <img
            v-if="auth.user?.avatar"
            :src="auth.user.avatar"
            alt="Avatar de perfil"
            referrerpolicy="no-referrer"
          />
          <span v-else>{{ (auth.user?.name || auth.user?.email || 'U')[0].toUpperCase() }}</span>
        </div>
        <div>
          <h2>{{ auth.user?.name || 'Usuario' }}</h2>
          <p>{{ auth.user?.email || 'Correo no disponible' }}</p>
        </div>
      </div>
    </div>

    <div
      v-if="auth.isAuthenticated"
      class="view-panel__card profile-favorites"
    >
      <div class="profile-favorites__header">
        <div>
          <p class="view-panel__subtitle">Favoritos</p>
          <h2>Sitios guardados</h2>
        </div>
      </div>
      <div v-if="favoritesLoading" class="profile-favorites__empty">
        Cargando tus favoritos…
      </div>
      <div v-else-if="favoritesError" class="profile-favorites__empty">
        {{ favoritesError }}
      </div>
      <div v-else-if="favoriteCards.length === 0" class="profile-favorites__empty">
        Todavía no marcaste sitios como favoritos.
      </div>
      <div v-else>
        <div class="featured__grid">
          <div
            v-for="(site, index) in favoriteCards"
            :key="site?.id ?? `favorite-slot-${index}`"
            class="featured__slot"
          >
            <SiteCard v-if="site" :site="site" />
            <div v-else class="site-card site-card--placeholder"></div>
          </div>
        </div>
        <div class="profile-pagination" role="navigation" aria-label="Paginación de favoritos">
          <button
            class="secondary-button"
            type="button"
            :disabled="favoritesLoading || !favoriteCanPrev"
            @click="handleFavoritesPrev"
          >
            Anterior
          </button>
          <span class="profile-pagination__info">
            {{ favoritePaginationLabel }} (página {{ favoritesPagination.page }} de {{ favoritesPagination.pages }})
          </span>
          <button
            class="secondary-button"
            type="button"
            :disabled="favoritesLoading || !favoriteCanNext"
            @click="handleFavoritesNext"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="auth.isAuthenticated"
      class="view-panel__card profile-reviews"
    >
      <div class="profile-reviews__header">
        <div>
          <p class="view-panel__subtitle">Reseñas</p>
          <h2>Mis reseñas</h2>
        </div>
      </div>

      <div v-if="userReviewsLoading" class="profile-favorites__empty">
        Cargando tus reseñas…
      </div>
      <div v-else-if="userReviewsError" class="profile-favorites__empty">
        <p>{{ userReviewsError }}</p>
        <button class="primary-button" type="button" @click="handleRefreshUserReviews">
          Reintentar
        </button>
      </div>
      <div v-else-if="userReviewList.length === 0" class="profile-favorites__empty">
        Todavía no escribiste reseñas. Compartí tu experiencia en la ficha de cada sitio y aparecerán acá.
      </div>
      <div v-else class="profile-reviews__list-wrapper">
        <ul class="review-list profile-reviews__list">
          <li
            v-for="(review, index) in userReviewList"
            :key="review.id || `my-review-${index}`"
            class="review-card profile-review-card"
          >
            <header class="profile-review-card__header">
              <div>
                <p class="profile-review-card__site">
                  <RouterLink
                    v-if="review.siteId"
                    :to="{ name: 'site-detail', params: { id: review.siteId }, query: { from: 'profile' } }"
                  >
                    {{ review.siteName }}
                  </RouterLink>
                  <span v-else>{{ review.siteName }}</span>
                </p>
                <p
                  v-if="review.siteCity || review.siteProvince"
                  class="profile-review-card__location"
                >
                  {{ [review.siteCity, review.siteProvince].filter(Boolean).join(', ') }}
                </p>
              </div>
              <span
                class="profile-review-card__status"
                :class="`profile-review-card__status--${resolveReviewStatusVariant(review.status)}`"
              >
                {{ resolveReviewStatusLabel(review.status) }}
              </span>
            </header>
            <div v-if="review.rating" class="profile-review-card__rating review-card__rating">
              <span
                v-for="star in 5"
                :key="`my-review-star-${review.id || index}-${star}`"
                class="review-star"
                :class="{ 'review-star--filled': star <= review.rating }"
                aria-hidden="true"
              >
                <svg viewBox="0 0 24 24">
                  <path
                    d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
                  />
                </svg>
              </span>
              <strong>{{ review.rating }}/5</strong>
            </div>
            <p class="review-card__comment profile-review-card__comment">
              {{ review.comment || 'Sin comentario.' }}
            </p>
            <p v-if="formatReviewDate(review.createdAt)" class="profile-review-card__date">
              Actualizada el {{ formatReviewDate(review.createdAt) }}
            </p>
          </li>
        </ul>
        <div class="profile-pagination" role="navigation" aria-label="Paginación de reseñas">
          <button
            class="secondary-button"
            type="button"
            :disabled="userReviewsLoading || !reviewsCanPrev"
            @click="handleReviewsPrev"
          >
            Anterior
          </button>
          <span class="profile-pagination__info">
            {{ reviewsPaginationLabel }} (página {{ reviewsPagination.page }} de {{ reviewsPagination.pages }})
          </span>
          <button
            class="secondary-button"
            type="button"
            :disabled="userReviewsLoading || !reviewsCanNext"
            @click="handleReviewsNext"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
