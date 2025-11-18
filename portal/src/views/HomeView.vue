<script setup>
import { computed, reactive, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import FeaturedSection from '@/components/FeaturedSection.vue'
import HeroBanner from '@/components/HeroBanner.vue'
import API_BASE_URL from '@/constants/api'
import { resolveSiteImageAlt, resolveSiteImageSrc } from '@/siteMedia'
import { useAuthStore } from '@/stores/auth'
import { useFavoritesStore } from '@/stores/favorites'

const router = useRouter()
const auth = useAuthStore()
const favoritesStore = useFavoritesStore()

const isAuthenticated = computed(() => auth.isAuthenticated)

const sectionsConfig = [
  {
    key: 'mostVisited',
    title: 'Más visitados',
    subtitle: 'Tendencias entre los usuarios.',
    ctaParams: { sort_by: 'visits', sort_dir: 'desc' },
    emptyMessage: 'Todavía no registramos sitios populares aquí.',
    skeletonItems: 3,
    orderBy: 'visits',
  },
  {
    key: 'topRated',
    title: 'Mejor puntuados',
    subtitle: 'Los sitios con mejores valoraciones.',
    ctaParams: { sort_by: 'rating', sort_dir: 'desc' },
    emptyMessage: 'Aún no hay calificaciones cargadas.',
    skeletonItems: 3,
    orderBy: 'rating-5-1',
  },
  {
    key: 'recent',
    title: 'Recientemente agregados',
    subtitle: 'Nuevos sitios que acaban de sumarse al portal.',
    ctaParams: { sort: 'recent' },
    emptyMessage: 'Pronto verás novedades aquí.',
    skeletonItems: 3,
    orderBy: 'latest',
  },
  {
    key: 'favorites',
    title: 'Favoritos',
    subtitle: 'Mi lista personal de favoritos.',
    ctaParams: { filter: 'favorites', favorites: '1' },
    emptyMessage: 'Todavia no tienes sitios favoritos.',
    requiresAuth: true,
    skeletonItems: 3,
    orderBy: 'latest',
    filter: 'favorites',
  },
]

const sectionsState = reactive(
  sectionsConfig.reduce((acc, config) => {
    acc[config.key] = {
      items: [],
      loading: false,
      loaded: false,
      error: null,
    }
    return acc
  }, {}),
)

const visibleSections = computed(() =>
  sectionsConfig.filter((section) => !section.requiresAuth || isAuthenticated.value),
)

const heroCopy = {
  eyebrow: 'Portal público',
  title: 'SITIOS HISTORICOS',
  description: 'Explorá sitios históricos y descubrí las maravillas que guarda el pasado.',
  hint: 'Tip: buscá por ciudad, por sitio o por palabra clave.',
  backdrop:
    'https://images.unsplash.com/photo-1577801599718-f4e3ad3fc794?q=80&w=1740&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D',
    // 'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=2000&q=60',
  scrollLabel: 'Ver destacados',
}

const buildCtaTo = (params = {}) => ({
  name: 'sites',
  query: params,
})

const GENERIC_SITE_IMAGE_URL =
  'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1200&q=60'

const formatStateLabel = (value) => {
  if (!value) return 'Estado sin datos'
  const normalized = String(value).replace(/_/g, ' ').toLowerCase()
  return normalized.charAt(0).toUpperCase() + normalized.slice(1)
}

const formatUpdatedAtLabel = (value) => {
  if (!value) return 'hace poco'
  const parsedDate = new Date(value)
  if (Number.isNaN(parsedDate.getTime())) {
    return 'hace poco'
  }

  const now = new Date()
  const diffMs = Math.max(0, now.getTime() - parsedDate.getTime())
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMinutes < 60) {
    return diffMinutes <= 1 ? 'hace un minuto' : `hace ${diffMinutes} minutos`
  }
  if (diffHours < 24) {
    return diffHours === 1 ? 'hace 1 hora' : `hace ${diffHours} horas`
  }
  if (diffDays < 7) {
    return diffDays === 1 ? 'hace 1 día' : `hace ${diffDays} días`
  }
  return parsedDate.toLocaleDateString('es-AR', {
    day: 'numeric',
    month: 'long',
  })
}

const mapSiteToCard = (site) => ({
  id: site.id,
  name: site.name,
  city: site.city,
  province: site.province,
  state: formatStateLabel(
    site.state_of_conservation ??
      site.conservation_status ??
      site.conservationStatus ??
      null,
  ),
  rating:
    typeof site.rating === 'number'
      ? site.rating
      : site.average_rating ?? site.averageRating ?? null,
  updatedAt: formatUpdatedAtLabel(site.updated_at || site.updatedAt),
  image: resolveSiteImageSrc(site, GENERIC_SITE_IMAGE_URL),
  imageAlt: resolveSiteImageAlt(site),
  tags: Array.isArray(site.tags) ? site.tags.slice(0, 5) : [],
  href: site.id ? { name: 'site-detail', params: { id: site.id }, query: { from: 'home' } } : null,
  is_favorite: site.is_favorite ?? site.isFavorite ?? false,
})

const resolveNumericRating = (site) => {
  const candidates = [
    site.rating,
    site.average_rating,
    site.averageRating,
    site.score,
  ]
  for (const value of candidates) {
    const number = typeof value === 'string' ? Number.parseFloat(value) : value
    if (Number.isFinite(number)) return number
  }
  return null
}

const fetchSitesForSection = async (sectionKey) => {
  const config = sectionsConfig.find((section) => section.key === sectionKey)
  if (config?.highlightEndpoint) {
    const limit = config.highlightLimit ?? config.skeletonItems ?? 3
    const response = await fetch(
      `${API_BASE_URL}${config.highlightEndpoint}?limit=${encodeURIComponent(limit)}`,
      { credentials: 'include' },
    )
    if (!response.ok) {
      throw new Error('No se pudieron cargar los sitios destacados.')
    }
    const payload = await response.json()
    return Array.isArray(payload?.data) ? payload.data : []
  }

  const perPage = config?.perPage ?? 100
  const params = new URLSearchParams({
    page: '1',
    per_page: String(perPage),
  })
  params.set('order_by', config?.orderBy || 'latest')
  if (config?.filter) {
    params.set('filter', config.filter)
  }
  const response = await fetch(`${API_BASE_URL}/sites?${params.toString()}`, {
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error('No se pudieron cargar los sitios.')
  }
  const payload = await response.json()
  return Array.isArray(payload?.data) ? payload.data : []
}

const loadSection = async (sectionKey, { force = false } = {}) => {
  const state = sectionsState[sectionKey]
  if (!state || (!force && (state.loading || state.loaded))) {
    return
  }

  state.loading = true
  state.error = null

  try {
    const rawItems = await fetchSitesForSection(sectionKey)
    if (sectionKey === 'topRated') {
      rawItems.sort((a, b) => (resolveNumericRating(b) ?? 0) - (resolveNumericRating(a) ?? 0))
    }
    favoritesStore.hydrateFromSites(rawItems)
    state.items = rawItems.map(mapSiteToCard)
    state.loaded = true
  } catch (error) {
    state.items = []
    state.error = error.message || 'Hubo un inconveniente al cargar esta sección.'
  } finally {
    state.loading = false
  }
}

const handleHeroSearch = (term) => {
  router.push({
    name: 'sites',
    query: term ? { q: term } : {},
  })
}

watch(
  visibleSections,
  (sections) => {
    sections.forEach((section) => loadSection(section.key))
  },
  { immediate: true },
)

watch(
  isAuthenticated,
  (loggedIn) => {
    if (loggedIn) {
      loadSection('favorites', { force: true })
    }
  },
)

const stopFavoritesActionHook = favoritesStore.$onAction(({ name, after }) => {
  if (name !== 'setFavorite') {
    return
  }
  after(() => {
    if (!isAuthenticated.value) {
      return
    }
    loadSection('favorites', { force: true })
  })
})

onBeforeUnmount(() => {
  if (typeof stopFavoritesActionHook === 'function') {
    stopFavoritesActionHook()
  }
})
</script>

<template>
  <section class="home">
    <HeroBanner
      :eyebrow="heroCopy.eyebrow"
      :title="heroCopy.title"
      :description="heroCopy.description"
      :hint="heroCopy.hint"
      :background-image="heroCopy.backdrop"
      :search-placeholder="heroCopy.searchPlaceholder"
      :scroll-label="heroCopy.scrollLabel"
      scroll-target="home-sections"
      variant="map"
      @search="handleHeroSearch"
    />

    <div id="home-sections" class="home__sections">
      <FeaturedSection
        v-for="section in visibleSections"
        :key="section.key"
        :title="section.title"
        :subtitle="section.subtitle"
        :items="sectionsState[section.key]?.items"
        :loading="sectionsState[section.key]?.loading"
        :cta-label="section.ctaLabel || 'Ver todos'"
        :cta-to="buildCtaTo(section.ctaParams)"
        :empty-message="section.emptyMessage"
        :skeleton-items="section.skeletonItems || 3"
      />
    </div>
  </section>
</template>
