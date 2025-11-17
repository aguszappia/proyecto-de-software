<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
const FAVORITES_PER_PAGE = 3
const favoritesPage = ref(0)
const favoritesIsMobile = ref(false)
const REVIEWS_PER_PAGE = 1
const reviewsPage = ref(0)
const reviewsIsMobile = ref(false)
let favoritesMediaQuery
let favoritesMediaHandler

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
  href: site.id ? { name: 'site-detail', params: { id: site.id } } : null,
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

const loadFavoriteSites = async () => {
  if (!auth.isAuthenticated) {
    favoriteSites.value = []
    favoritesError.value = ''
    favoritesLoading.value = false
    return
  }

  favoritesLoading.value = true
  favoritesError.value = ''
  const params = new URLSearchParams({
    filter: 'favorites',
    per_page: '50',
    page: '1',
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

const favoriteTotalPages = computed(() =>
  favoriteCards.value.length ? Math.ceil(favoriteCards.value.length / FAVORITES_PER_PAGE) : 0,
)
const favoriteNeedsCarousel = computed(
  () => !favoritesIsMobile.value && favoriteTotalPages.value > 1,
)
const favoriteShowPrev = computed(
  () => favoriteNeedsCarousel.value && favoritesPage.value > 0,
)
const favoriteShowNext = computed(
  () => favoriteNeedsCarousel.value && favoritesPage.value < favoriteTotalPages.value - 1,
)
const favoritePageItems = computed(() => {
  const start = favoritesPage.value * FAVORITES_PER_PAGE
  return favoriteCards.value.slice(start, start + FAVORITES_PER_PAGE)
})
const favoriteVisibleCards = computed(() =>
  favoritesIsMobile.value ? favoriteCards.value : favoritePageItems.value,
)

const reviewsTotalPages = computed(() =>
  userReviewList.value.length ? Math.ceil(userReviewList.value.length / REVIEWS_PER_PAGE) : 0,
)
const reviewsNeedsCarousel = computed(
  () => !reviewsIsMobile.value && reviewsTotalPages.value > 1,
)
const reviewsShowPrev = computed(() => reviewsNeedsCarousel.value && reviewsPage.value > 0)
const reviewsShowNext = computed(
  () => reviewsNeedsCarousel.value && reviewsPage.value < reviewsTotalPages.value - 1,
)
const reviewsPageItems = computed(() => {
  const start = reviewsPage.value * REVIEWS_PER_PAGE
  return userReviewList.value.slice(start, start + REVIEWS_PER_PAGE)
})
const reviewVisibleCards = computed(() =>
  reviewsIsMobile.value ? userReviewList.value : reviewsPageItems.value,
)

const handleReviewsPrev = () => {
  if (reviewsPage.value > 0) {
    reviewsPage.value -= 1
  }
}

const handleReviewsNext = () => {
  if (reviewsPage.value < reviewsTotalPages.value - 1) {
    reviewsPage.value += 1
  }
}

const handleFavoritesPrev = () => {
  if (favoritesPage.value > 0) {
    favoritesPage.value -= 1
  }
}

const handleFavoritesNext = () => {
  if (favoritesPage.value < favoriteTotalPages.value - 1) {
    favoritesPage.value += 1
  }
}

const loadUserReviews = async () => {
  if (!auth.isAuthenticated) {
    userReviews.value = []
    userReviewsError.value = ''
    userReviewsLoading.value = false
    return
  }

  userReviewsLoading.value = true
  userReviewsError.value = ''
  try {
    const response = await fetch(`${API_BASE_URL}/me/reviews`, {
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
    loadFavoriteSites()
  }
}

const handleRefreshUserReviews = () => {
  if (!userReviewsLoading.value) {
    loadUserReviews()
  }
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
    }
  },
)

onMounted(() => {
  if (auth.isAuthenticated) {
    loadFavoriteSites()
    loadUserReviews()
  }
  if (typeof window !== 'undefined' && window.matchMedia) {
    favoritesMediaQuery = window.matchMedia('(max-width: 640px)')
    favoritesIsMobile.value = favoritesMediaQuery.matches
    reviewsIsMobile.value = favoritesMediaQuery.matches
    favoritesMediaHandler = (event) => {
      favoritesIsMobile.value = event.matches
      reviewsIsMobile.value = event.matches
      favoritesPage.value = 0
      reviewsPage.value = 0
    }
    if (favoritesMediaQuery.addEventListener) {
      favoritesMediaQuery.addEventListener('change', favoritesMediaHandler)
    } else if (favoritesMediaQuery.addListener) {
      favoritesMediaQuery.addListener(favoritesMediaHandler)
    }
  }
})

onBeforeUnmount(() => {
  if (!favoritesMediaQuery || !favoritesMediaHandler) return
  if (favoritesMediaQuery.removeEventListener) {
    favoritesMediaQuery.removeEventListener('change', favoritesMediaHandler)
  } else if (favoritesMediaQuery.removeListener) {
    favoritesMediaQuery.removeListener(favoritesMediaHandler)
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

watch(
  () => favoriteCards.value.length,
  () => {
    favoritesPage.value = 0
  },
)

watch(
  () => userReviewList.value.length,
  () => {
    reviewsPage.value = 0
  },
)
</script>

<template>
  <section class="view-panel profile-view">
    <div class="view-panel__card">
      <p class="view-panel__subtitle">Tu espacio</p>
      <h1>Mi perfil</h1>
      <p>Pronto vas a poder gestionar tus favoritos y postulaciones desde aquí.</p>
    </div>

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
      <dl class="profile-meta">
        <div>
          <dt>Estado</dt>
          <dd>Sesión activa</dd>
        </div>
        <div>
          <dt>Última actividad</dt>
          <dd>Disponible pronto</dd>
        </div>
      </dl>
      <p class="profile-note">
        Estamos trabajando para habilitar reseñas, favoritos y más acciones dentro de tu perfil.
      </p>
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
      <div v-else class="featured__grid-wrapper profile-favorites__carousel">
        <button
          v-if="favoriteShowPrev"
          type="button"
          class="featured__arrow featured__arrow--left"
          @click="handleFavoritesPrev"
          aria-label="Ver favoritos anteriores"
        >
          ‹
        </button>
        <div class="featured__grid">
          <div
            v-for="(site, index) in favoriteVisibleCards"
            :key="site?.id ?? `favorite-slot-${index}`"
            class="featured__slot"
          >
            <SiteCard v-if="site" :site="site" />
            <div v-else class="site-card site-card--placeholder"></div>
          </div>
        </div>
        <button
          v-if="favoriteShowNext"
          type="button"
          class="featured__arrow featured__arrow--right"
          @click="handleFavoritesNext"
          aria-label="Ver más favoritos"
        >
          ›
        </button>
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
      <div v-else class="profile-reviews__carousel">
        <button
          v-if="reviewsShowPrev"
          type="button"
          class="featured__arrow featured__arrow--left"
          @click="handleReviewsPrev"
          aria-label="Ver reseñas anteriores"
        >
          ‹
        </button>
        <ul class="review-list profile-reviews__list">
          <li
            v-for="(review, index) in reviewVisibleCards"
            :key="review.id || `my-review-${index}`"
            class="review-card profile-review-card"
          >
            <header class="profile-review-card__header">
              <div>
                <p class="profile-review-card__site">
                  <RouterLink
                    v-if="review.siteId"
                    :to="{ name: 'site-detail', params: { id: review.siteId } }"
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
        <button
          v-if="reviewsShowNext"
          type="button"
          class="featured__arrow featured__arrow--right"
          @click="handleReviewsNext"
          aria-label="Ver más reseñas"
        >
          ›
        </button>
      </div>
    </div>
  </section>
</template>
