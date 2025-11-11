<script setup>
import { computed, ref, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
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

const formatState = (value) => {
  if (!value) return 'Sin dato'
  const normalized = String(value).replace(/_/g, ' ').toLowerCase()
  return normalized.charAt(0).toUpperCase() + normalized.slice(1)
}

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
        <h2 v-if="sites.length === 0">Sin resultados</h2>
        <p v-if="sites.length === 0" class="listing__note">
          Probá modificando los filtros para encontrar otros sitios históricos.
        </p>
        <ul v-else class="listing__grid">
          <li v-for="site in sites" :key="site.id" class="listing__item">
            <h3>{{ site.name }}</h3>
            <p class="listing__location">
              {{ site.city }}, {{ site.province }}
              <template v-if="site.country">({{ site.country }})</template>
            </p>
            <p class="listing__description">{{ site.short_description }}</p>
            <div class="listing__details">
              <p><span>Ciudad:</span> {{ site.city }}, {{ site.province }}</p>
              <p><span>Estado:</span> {{ formatState(site.state_of_conservation) }}</p>
              <p><span>Categoría:</span> {{ site.category || 'Sin dato' }}</p>
              <p>
                <span>Año de inauguración:</span>
                {{ site.inaguration_year ?? 'Sin dato' }}
              </p>
            </div>
            <p class="listing__full">{{ site.description || site.full_description }}</p>
            <ul class="listing__tags" v-if="(site.tags || []).length">
              <li v-for="tag in site.tags" :key="`${site.id}-${tag}`">#{{ tag }}</li>
            </ul>
          </li>
        </ul>
      </template>
    </div>
  </section>
</template>

<style scoped>
.listing__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.85rem;
  color: #374151;
  margin-top: 1rem;
}

.view-panel__actions {
  margin-top: 1.25rem;
}

.listing__placeholder {
  text-align: center;
  background: rgba(255, 255, 255, 0.9);
}

.listing__note {
  margin-top: 0.75rem;
  color: #6b7280;
  font-size: 0.9rem;
}

.listing__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
  list-style: none;
  margin: 1rem 0 0;
  padding: 0;
  text-align: left;
}

.listing__item {
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  padding: 1rem;
  background: #fff;
  box-shadow: 0 5px 15px rgba(15, 23, 42, 0.08);
}

.listing__location {
  font-size: 0.85rem;
  color: #6b7280;
}

.listing__description {
  margin: 0.75rem 0;
  font-size: 0.95rem;
  color: #374151;
}

.listing__details {
  text-align: left;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
  color: #4b5563;
}

.listing__details span {
  font-weight: 600;
  color: #1f2937;
}

.listing__full {
  font-size: 0.95rem;
  color: #1f2937;
  margin-bottom: 0.75rem;
}

.listing__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  list-style: none;
  padding: 0;
  margin: 0.75rem 0 0;
}

.listing__tags li {
  background: #f3f4f6;
  border-radius: 999px;
  padding: 0.2rem 0.75rem;
  font-size: 0.75rem;
  color: #1f2937;
}
</style>
