<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SiteCard from '@/components/SiteCard.vue'
import API_BASE_URL from '@/constants/api'

const route = useRoute()
const router = useRouter()

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
  sort_by: ['created_at', 'name', 'city'].includes(route.query.sort_by)
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

const formFilters = ref({
  q: '',
  city: '',
  province: '',
  conservation_status: '',
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
    image: GENERIC_SITE_IMAGE_URL,
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
  params.set('sort_by', filters.sort_by || 'created_at')
  params.set('sort_dir', filters.sort_dir || 'desc')
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
  sites.value = []
  try {
    const query = buildQueryString(filters)
    const response = await fetch(`${API_BASE_URL}/sites?${query}`)
    if (!response.ok) {
      throw new Error(`Error ${response.status}`)
    }
    const payload = await response.json()
    const normalizedSearch = (filters.q || '').toString().trim().toLowerCase()
    const normalizedCity = filters.city.trim().toLowerCase()
    const normalizedProvince = filters.province.trim().toLowerCase()
    const normalizedStatus = filters.conservation_status.trim().toLowerCase()
    const desiredTags = (filters.tags || []).map((tag) => tag.trim().toLowerCase()).filter(Boolean)
    const rawItems = Array.isArray(payload?.data) ? payload.data : []

    availableTags.value = Array.from(
      new Set(
        rawItems
          .flatMap((site) => site.tags || [])
          .filter((tag) => typeof tag === 'string' && tag.trim().length),
      ),
    )

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

      return matchesSearch && matchesCity && matchesProvince && matchesStatus && matchesTags
    })

    sites.value = filteredItems.map((site) => ({
      ...site,
      state_of_conservation:
        site.state_of_conservation ??
        site.conservation_status ??
        site.conservationStatus ??
        null,
      category: site.category ?? site.category_name ?? site.categoryName ?? null,
      inaguration_year:
        site.inaguration_year ?? site.inauguration_year ?? site.inaugYear ?? null,
    }))
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
  if (filters.tags?.length) query.tags = filters.tags
  return query
}

const handleFiltersSubmit = () => {
  router.push({
    name: 'sites',
    query: serializeFilters(formFilters.value),
  })
}

const handleFiltersReset = () => {
  router.push({ name: 'sites' })
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
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
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
        <RouterLink class="primary-button" to="/sitios/nuevo">Proponer un sitio</RouterLink>
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

        <div class="filters-row">
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
              <option value="name">Nombre</option>
              <option value="city">Ciudad</option>
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
                <span v-else>Seleccionar etiquetas</span>
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
      <template v-if="loading">
        <h2>Cargando sitios...</h2>
        <p>Buscando resultados con los filtros seleccionados.</p>
      </template>
      <template v-else-if="error">
        <h2>Ups, hubo un problema</h2>
        <p class="listing__note">{{ error }}</p>
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
    </div>
  </section>
</template>
