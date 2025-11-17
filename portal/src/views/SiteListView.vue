<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LMap, LMarker, LPopup, LTileLayer } from '@vue-leaflet/vue-leaflet'
import 'leaflet/dist/leaflet.css'
import SiteCard from '@/components/SiteCard.vue'
import API_BASE_URL from '@/constants/api'
import { resolveSiteImageAlt, resolveSiteImageSrc } from '@/siteMedia'
import { useFavoritesStore } from '@/stores/favorites'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const favoritesStore = useFavoritesStore()
const auth = useAuthStore()

const PROVINCES = [
  'Buenos Aires',
  'CABA',
  'Catamarca',
  'Chaco',
  'Chubut',
  'Córdoba',
  'Corrientes',
  'Entre Ríos',
  'Formosa',
  'Jujuy',
  'La Pampa',
  'La Rioja',
  'Mendoza',
  'Misiones',
  'Neuquén',
  'Río Negro',
  'Salta',
  'San Juan',
  'San Luis',
  'Santa Cruz',
  'Santa Fe',
  'Santiago del Estero',
  'Tierra del Fuego',
  'Tucumán',
]

const CONSERVATION_STATUSES = [
  'Bueno',
  'Regular',
  'Malo',
]

const activeFilters = computed(() => ({
  q: route.query.q || route.query.search || '',
  city: route.query.city || '',
  province: route.query.province || '',
  conservation_status: route.query.conservation_status || '',
  favorites:
    auth.isAuthenticated &&
    ['1', 'true', 'yes', 'on'].includes(String(route.query.favorites || '').toLowerCase()),
  sort_by: ['created_at', 'name', 'rating', 'visits'].includes(route.query.sort_by)
    ? route.query.sort_by
    : 'created_at',
  sort_dir: route.query.sort_dir === 'asc' ? 'asc' : 'desc',
  tags: Array.isArray(route.query.tags)
    ? route.query.tags.filter(Boolean)
    : route.query.tags
      ? [route.query.tags]
      : [],
}))

const sites = ref([])
const loading = ref(false)
const error = ref(null)
const availableTags = ref([])
const tagsDropdownOpen = ref(false)
const tagsDropdownRef = ref(null)
const showingMap = ref(route.query.view === 'map')
const showAuthPrompt = ref(false)

const formFilters = ref({
  q: '',
  city: '',
  province: '',
  conservation_status: '',
  favorites: false,
  sort_by: 'created_at',
  sort_dir: 'desc',
  tags: [],
})

watch(
  activeFilters,
  (value) => {
    formFilters.value = {
      ...value,
      tags: [...value.tags],
    }
  },
  { immediate: true },
)

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

const preparedSites = computed(() =>
  sites.value.map((site) => ({
    id: site.id,
    name: site.name,
    city: site.city,
    province: site.province,
    category: site.category || null,
    state: formatStateLabel(site.state_of_conservation),
    badge: site.badge || null,
    rating:
      typeof site.rating === 'number'
        ? site.rating
        : site.average_rating ?? site.averageRating ?? null,
    updatedAt: formatUpdatedAtLabel(site.updated_at || site.updatedAt),
    image: resolveSiteImageSrc(site, GENERIC_SITE_IMAGE_URL),
    imageAlt: resolveSiteImageAlt(site),
    tags: Array.isArray(site.tags) ? site.tags.slice(0, 5) : [],
    href: site.id
      ? {
          name: 'site-detail',
          params: { id: site.id },
          query: { ...route.query },
        }
      : null,
  })),
)

const buildQueryString = (filters) => {
  const params = new URLSearchParams()
  if (filters.city) params.set('city', filters.city)
  if (filters.province) params.set('province', filters.province)
  if (filters.conservation_status) params.set('conservation_status', filters.conservation_status)
  if (filters.q) params.set('q', filters.q)
  if (filters.sort_by) params.set('sort_by', filters.sort_by)
  if (filters.sort_dir) params.set('sort_dir', filters.sort_dir)
  if (filters.favorites) params.set('favorites', '1')
  filters.tags?.forEach((tag) => {
    if (tag) params.append('tags', tag)
  })
  params.set('page', '1')
  params.set('per_page', '20')
  return params.toString()
}

watchEffect(async () => {
  const filters = activeFilters.value
  loading.value = true
  error.value = null
  try {
    const query = buildQueryString(filters)
    const response = await fetch(`${API_BASE_URL}/sites?${query}`, {
      credentials: 'include',
    })
    if (!response.ok) {
      throw new Error(`Error ${response.status}`)
    }
    const payload = await response.json()
    const normalizedSearch = (filters.q || '').toString().trim().toLowerCase()
    const normalizedCity = filters.city.trim().toLowerCase()
    const normalizedProvince = filters.province.trim().toLowerCase()
    const normalizedStatus = filters.conservation_status.trim().toLowerCase()
    const desiredTags = (filters.tags || []).map((tag) => tag.trim().toLowerCase()).filter(Boolean)
    const favoritesOnly = filters.favorites && auth.isAuthenticated
    const rawItems = Array.isArray(payload?.data) ? payload.data : []

    const filteredItems = rawItems.filter((site) => {
      const shortDescription =
        site.short_description ?? site.shortDescription ?? site.shortDesc ?? ''
      const fullDescription =
        site.full_description ?? site.fullDescription ?? site.description ?? ''
      const siteTags = (site.tags || []).map((tag) => (tag || '').toLowerCase())
      const siteStatus = (
        site.state_of_conservation ??
        site.conservation_status ??
        site.conservationStatus ??
        ''
      )
        .toString()
        .toLowerCase()

      const matchesSearch =
        !normalizedSearch ||
        [site.name, site.city, site.province, shortDescription, fullDescription].some(
          (value) => typeof value === 'string' && value.toLowerCase().includes(normalizedSearch),
        )

      const matchesCity =
        !normalizedCity || (site.city || '').toString().toLowerCase() === normalizedCity
      const matchesProvince =
        !normalizedProvince || (site.province || '').toString().toLowerCase() === normalizedProvince
      const matchesStatus = !normalizedStatus || siteStatus === normalizedStatus
      const matchesTags =
        !desiredTags.length ||
        desiredTags.every((tag) => siteTags.includes(tag))
      const siteFavoriteFlag =
        site.is_favorite === true ||
        site.isFavorite === true ||
        favoritesStore.isFavorite(site.id)
      const matchesFavorites = !favoritesOnly || siteFavoriteFlag

      return (
        matchesSearch &&
        matchesCity &&
        matchesProvince &&
        matchesStatus &&
        matchesTags &&
        matchesFavorites
      )
    })

    favoritesStore.hydrateFromSites(filteredItems)
    const mappedItems = filteredItems.map((site) => ({
      ...site,
      state_of_conservation:
        site.state_of_conservation ??
        site.conservation_status ??
        site.conservationStatus ??
        null,
      category: site.category ?? site.category_name ?? site.categoryName ?? null,
      inaguration_year:
        site.inaguration_year ?? site.inauguration_year ?? site.inaugYear ?? null,
      is_favorite: site.is_favorite ?? site.isFavorite ?? false,
    }))
    sites.value = mappedItems
  } catch (err) {
    error.value = err.message || 'No se pudo obtener la información'
  } finally {
    loading.value = false
  }
})

const serializeFilters = (filters) => {
  const query = {}
  if (filters.q) query.q = filters.q
  if (filters.city) query.city = filters.city
  if (filters.province) query.province = filters.province
  if (filters.conservation_status) query.conservation_status = filters.conservation_status
  if (filters.sort_by && filters.sort_by !== 'created_at') query.sort_by = filters.sort_by
  if (filters.sort_dir && filters.sort_dir !== 'desc') query.sort_dir = filters.sort_dir
  if (filters.favorites) query.favorites = '1'
  if (filters.tags?.length) query.tags = filters.tags
  return query
}

const handleFiltersSubmit = () => {
  const nextQuery = serializeFilters(formFilters.value)
  if (showingMap.value) {
    nextQuery.view = 'map'
  }
  router.push({
    name: 'sites',
    query: nextQuery,
  })
}

const handleFiltersReset = () => {
  const query = showingMap.value ? { view: 'map' } : {}
  router.push({ name: 'sites', query })
}

const toggleTag = (tag) => {
  const current = new Set(formFilters.value.tags)
  if (current.has(tag)) {
    current.delete(tag)
  } else {
    current.add(tag)
  }
  formFilters.value.tags = Array.from(current)
}

const toggleTagDropdown = () => {
  if (!availableTags.value.length) {
    return
  }
  tagsDropdownOpen.value = !tagsDropdownOpen.value
}

const closeTagDropdown = () => {
  tagsDropdownOpen.value = false
}

const handleClickOutside = (event) => {
  if (!tagsDropdownRef.value) {
    return
  }
  if (!tagsDropdownRef.value.contains(event.target)) {
    closeTagDropdown()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  loadAvailableTags()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})

watch(
  () => route.query.view,
  (value) => {
    showingMap.value = value === 'map'
  },
  { immediate: true },
)

const DEFAULT_MAP_CENTER = [-34.6037, -58.3816]

const loadAvailableTags = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/tags`)
    if (!response.ok) {
      throw new Error('Failed to fetch tags')
    }
    const payload = await response.json()
    const mapped = Array.isArray(payload?.data) ? payload.data : []
    availableTags.value = mapped
      .map((tag) => (typeof tag?.name === 'string' ? tag.name.trim() : ''))
      .filter(Boolean)
  } catch (error) {
    availableTags.value = []
  }
}

const resolveCoordinate = (source, keys) => {
  for (const key of keys) {
    if (!(key in source)) continue
    const value = source[key]
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value
    }
    if (typeof value === 'string' && value.trim().length) {
      const parsed = Number(value)
      if (Number.isFinite(parsed)) {
        return parsed
      }
    }
  }
  return null
}

const mapSites = computed(() =>
  sites.value
    .map((site) => {
      const latitude = resolveCoordinate(site, ['lat', 'latitude', 'latitud'])
      const longitude = resolveCoordinate(site, ['long', 'lon', 'longitude', 'longitud'])
      return {
        id: site.id,
        name: site.name,
        city: site.city,
        province: site.province,
        latitude,
        longitude,
        summary:
          site.short_description ??
          site.shortDescription ??
          site.full_description ??
          site.fullDescription ??
          '',
      }
    })
    .filter((site) => typeof site.latitude === 'number' && typeof site.longitude === 'number'),
)

const mapCenter = computed(() => {
  if (mapSites.value.length === 1) {
    return [mapSites.value[0].latitude, mapSites.value[0].longitude]
  }
  if (mapSites.value.length > 1) {
    const latitudes = mapSites.value.map((site) => site.latitude)
    const longitudes = mapSites.value.map((site) => site.longitude)
    return [
      (Math.min(...latitudes) + Math.max(...latitudes)) / 2,
      (Math.min(...longitudes) + Math.max(...longitudes)) / 2,
    ]
  }
  return DEFAULT_MAP_CENTER
})

const mapBounds = computed(() => {
  if (mapSites.value.length < 2) {
    return null
  }
  const latitudes = mapSites.value.map((site) => site.latitude)
  const longitudes = mapSites.value.map((site) => site.longitude)
  return [
    [Math.min(...latitudes), Math.min(...longitudes)],
    [Math.max(...latitudes), Math.max(...longitudes)],
  ]
})

const mapZoom = computed(() => (mapSites.value.length > 1 ? 6 : 13))

const synchronizeViewQuery = (mode) => {
  const nextQuery = { ...route.query }
  if (mode === 'map') {
    if (nextQuery.view === 'map') return
    nextQuery.view = 'map'
  } else {
    if (!nextQuery.view) return
    delete nextQuery.view
  }
  router.push({
    name: 'sites',
    query: nextQuery,
  })
}

const toggleMapMode = (enabled) => {
  if (enabled && !mapSites.value.length) return
  synchronizeViewQuery(enabled ? 'map' : 'list')
}

const buildAbsoluteUrl = (routeLocation) => {
  const resolved = router.resolve(routeLocation)
  const origin =
    typeof window !== 'undefined' && window.location?.origin ? window.location.origin : ''
  return `${origin}${resolved.href}`
}

const handleProposeSiteClick = () => {
  const targetLocation = { name: 'site-create' }
  if (auth.isAuthenticated) {
    router.push(targetLocation)
    return
  }
  showAuthPrompt.value = true
}

const handleAuthPromptClose = () => {
  showAuthPrompt.value = false
}

const handleAuthPromptLogin = () => {
  showAuthPrompt.value = false
  const nextUrl = buildAbsoluteUrl({ name: 'site-create' })
  auth.loginWithGoogle(nextUrl)
}

watch(
  mapSites,
  (value) => {
    if (!value.length && showingMap.value && !loading.value) {
      synchronizeViewQuery('list')
    }
  },
  { flush: 'post' },
)
</script>

<template>
  <section class="view-panel">
    <div class="view-panel__card">
      <p class="view-panel__subtitle">Explorar</p>
      <h1>Listado de sitios</h1>
      <p>
        Aplicá filtros avanzados para encontrar rápidamente los sitios que te interesan.
      </p>
      <div class="view-panel__actions">
        <button class="primary-button" type="button" @click="handleProposeSiteClick">
          Proponer un sitio
        </button>
      </div>

      <form class="filters-panel" @submit.prevent="handleFiltersSubmit">
        <div class="filters-row">
          <label class="filter-group">
            <span>Ciudad</span>
            <input v-model="formFilters.city" type="text" placeholder="Buscar por ciudad" />
          </label>
          <label class="filter-group">
            <span>Provincia</span>
            <select v-model="formFilters.province">
              <option value="">Todas</option>
              <option v-for="province in PROVINCES" :key="province" :value="province">
                {{ province }}
              </option>
            </select>
          </label>
          <label class="filter-group">
            <span>Búsqueda libre</span>
            <input
              v-model="formFilters.q"
              type="text"
              placeholder="Nombre, descripción, ciudad o provincia"
            />
          </label>
        </div>

        <div class="filters-row filters-row--ordering">
          <label class="filter-group">
            <span>Estado de conservación</span>
            <select v-model="formFilters.conservation_status">
              <option value="">Todos</option>
              <option v-for="status in CONSERVATION_STATUSES" :key="status" :value="status">
                {{ status }}
              </option>
            </select>
          </label>
          <label class="filter-group">
            <span>Ordenar por</span>
            <select v-model="formFilters.sort_by">
              <option value="created_at">Fecha de registro</option>
              <option value="visits">Visitas</option>
              <option value="rating">Puntuación</option>
              <option value="name">Nombre</option>
            </select>
          </label>
          <label class="filter-group">
            <span>Orden</span>
            <select v-model="formFilters.sort_dir">
              <option value="desc">Descendente</option>
              <option value="asc">Ascendente</option>
            </select>
          </label>
        </div>

        <div class="filters-row filters-row--tags">
          <div class="filter-group filter-group--tags">
            <span>Tags</span>
            <div class="tag-dropdown" ref="tagsDropdownRef">
              <button
                type="button"
                class="tag-dropdown__toggle"
                :disabled="!availableTags.length"
                @click.stop="toggleTagDropdown"
              >
                <span v-if="formFilters.tags.length">
                  {{ formFilters.tags.length }} seleccionada{{ formFilters.tags.length === 1 ? '' : 's' }}
                </span>
                <span v-else>
                  {{ availableTags.length ? 'Seleccionar etiquetas' : 'No hay etiquetas disponibles' }}
                </span>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M6 9l6 6 6-6"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </button>
              <div v-if="tagsDropdownOpen" class="tag-dropdown__panel">
                <label
                  v-for="tag in availableTags"
                  :key="tag"
                  class="tag-dropdown__option"
                >
                  <input
                    type="checkbox"
                    :value="tag"
                    :checked="formFilters.tags.includes(tag)"
                    @change="toggleTag(tag)"
                  />
                  <span>{{ tag }}</span>
                </label>
                <p v-if="!availableTags.length" class="tag-placeholder">
                  Cargaremos etiquetas cuando haya sitios disponibles.
                </p>
                <button
                  type="button"
                  class="secondary-button tag-dropdown__close"
                  @click="closeTagDropdown"
                >
                  Listo
                </button>
              </div>
            </div>
            <div v-if="formFilters.tags.length" class="tag-selected-summary">
              <span v-for="tag in formFilters.tags" :key="tag" class="tag-pill">
                {{ tag }}
                <button type="button" @click="toggleTag(tag)" aria-label="Quitar tag">
                  ×
                </button>
              </span>
            </div>
          </div>
          <label
            v-if="auth.isAuthenticated"
            class="filter-group filter-group--favorites-checkbox"
          >
            <div class="filter-inline-checkbox">
              <input
                id="favorites-filter"
                v-model="formFilters.favorites"
                type="checkbox"
              />
              <span>Favoritos</span>
            </div>
          </label>
        </div>

        <div class="filters-actions">
          <button type="submit" class="primary-button">Aplicar filtros</button>
          <button type="button" class="secondary-button filters-actions__reset" @click="handleFiltersReset">
            Limpiar filtros
          </button>
        </div>
      </form>
    </div>

    <div class="view-panel__card listing__placeholder">
      <div v-if="!loading && !error && preparedSites.length" class="listing__header">
        <div>
          <h2>{{ showingMap ? 'Mapa de sitios' : 'Resultados' }}</h2>
          <p class="listing__note">
            {{
              showingMap
                ? 'Mostramos únicamente los sitios que cuentan con coordenadas para los filtros activos.'
                : 'Visualizá los resultados como tarjetas o usá el mapa para ubicarlos geográficamente.'
            }}
          </p>
        </div>
        <button
          v-if="!showingMap"
          type="button"
          class="secondary-button listing__toggle-button"
          :disabled="!mapSites.length"
          @click="toggleMapMode(true)"
        >
          Ver mapa
        </button>
        <button
          v-else
          type="button"
          class="secondary-button listing__toggle-button"
          @click="toggleMapMode(false)"
        >
          Volver al listado
        </button>
      </div>

      <template v-if="loading && !preparedSites.length">
        <h2>Cargando sitios...</h2>
        <p>Buscando resultados con los filtros seleccionados.</p>
      </template>
      <template v-else-if="error">
        <h2>Ups, hubo un problema</h2>
        <p class="listing__note">{{ error }}</p>
      </template>
      <template v-else>
        <div v-if="loading" class="listing__status" role="status" aria-live="polite">
          <span class="listing__spinner" aria-hidden="true"></span>
          Actualizando resultados…
        </div>
        <template v-if="showingMap">
          <p v-if="!mapSites.length" class="listing__note">
            No hay sitios con coordenadas para estos filtros. Volvé al listado para explorar otras opciones.
          </p>
          <div v-else class="listing__map-card">
            <l-map
              :key="`map-${mapSites.length}`"
              class="listing__leaflet"
              :center="mapCenter"
              :zoom="mapZoom"
              :bounds="mapBounds || undefined"
              style="width: 100%; min-height: 320px;"
            >
              <l-tile-layer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <l-marker
                v-for="site in mapSites"
                :key="site.id || site.name"
                :lat-lng="[site.latitude, site.longitude]"
              >
                <l-popup>
                  <strong>{{ site.name }}</strong>
                  <p>{{ site.city ? `${site.city}, ${site.province}` : site.province }}</p>
                  <p v-if="site.summary">{{ site.summary }}</p>
                  <RouterLink
                    v-if="site.id"
                    class="map-popup__link"
                    :to="{ name: 'site-detail', params: { id: site.id } }"
                  >
                    Ver detalle
                  </RouterLink>
                </l-popup>
              </l-marker>
            </l-map>
          </div>
        </template>
        <template v-else>
          <h2 v-if="preparedSites.length === 0">Sin resultados</h2>
          <p v-if="preparedSites.length === 0" class="listing__note">
            Ajustá los criterios o probá con otras palabras clave.
          </p>
          <div v-else class="listing__cards">
            <SiteCard
              v-for="site in preparedSites"
              :key="site.id || site.name"
              :site="site"
            />
          </div>
        </template>
      </template>
    </div>
  </section>

  <div
    v-if="showAuthPrompt"
    class="public-modal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="auth-dialog-title"
  >
    <div class="public-modal__backdrop" @click="handleAuthPromptClose"></div>
    <div class="public-modal__card" role="document">
      <h2 id="auth-dialog-title">Iniciá sesión para continuar</h2>
      <p>
        Necesitás estar autenticado para proponer un nuevo sitio histórico en el portal público.
      </p>
      <div class="public-modal__actions">
        <button class="public-modal__button" type="button" @click="handleAuthPromptClose">
          Ahora no
        </button>
        <button
          class="public-modal__button public-modal__button--primary"
          type="button"
          @click="handleAuthPromptLogin"
        >
          Ingresar con Google
        </button>
      </div>
    </div>
  </div>
</template>
