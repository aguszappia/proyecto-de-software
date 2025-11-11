<script setup>
import { computed, ref, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import SiteCard from '@/components/SiteCard.vue'
import API_BASE_URL from '@/constants/api'

const route = useRoute()

const activeFilters = computed(() => ({
  search: route.query.search || null,
  sort: route.query.sort || 'latest',
  filter: route.query.filter || null,
}))

const sites = ref([])
const loading = ref(false)
const error = ref(null)

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
    href: site.id ? { name: 'site-detail', params: { id: site.id } } : null,
  })),
)

const buildQueryString = (filters) => {
  const params = new URLSearchParams()
  if (filters.search) {
    params.set('name', filters.search)
    params.set('description', filters.search)
  }
  if (filters.sort) {
    const allowedSort = ['rating-5-1', 'rating-1-5', 'latest', 'oldest']
    params.set('order_by', allowedSort.includes(filters.sort) ? filters.sort : 'latest')
  }
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
    sites.value = (payload?.data || []).map((site) => ({
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
</script>

<template>
  <section class="view-panel">
    <div class="view-panel__card">
      <p class="view-panel__subtitle">Explorar</p>
      <h1>Listado de sitios</h1>
      <p>
        Esta pantalla reutilizará el componente de tarjetas públicas y aplicará los filtros que
        definas desde el buscador o las secciones destacadas.
      </p>
      <div class="view-panel__actions">
        <RouterLink class="primary-button" to="/sitios/nuevo">Proponer un sitio</RouterLink>
      </div>
      <div class="listing__filters">
        <span v-if="activeFilters.search">Búsqueda: “{{ activeFilters.search }}”</span>
        <span v-if="activeFilters.sort">Orden: {{ activeFilters.sort }}</span>
        <span v-if="activeFilters.filter">Filtro: {{ activeFilters.filter }}</span>
      </div>
    </div>

    <div class="view-panel__card listing__placeholder">
      <template v-if="loading">
        <h2>Cargando sitios...</h2>
        <p>Buscando resultados en la API pública.</p>
      </template>
      <template v-else-if="error">
        <h2>Ups, hubo un problema</h2>
        <p class="listing__note">{{ error }}</p>
      </template>
      <template v-else>
        <h2 v-if="preparedSites.length === 0">Sin resultados</h2>
        <p v-if="preparedSites.length === 0" class="listing__note">
          Probá modificando los filtros para encontrar otros sitios históricos.
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
