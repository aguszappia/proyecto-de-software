<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const activeFilters = computed(() => ({
  search: route.query.search || null,
  sort: route.query.sort || 'visits',
  filter: route.query.filter || null,
}))
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
      <div class="listing__filters">
        <span v-if="activeFilters.search">Búsqueda: “{{ activeFilters.search }}”</span>
        <span v-if="activeFilters.sort">Orden: {{ activeFilters.sort }}</span>
        <span v-if="activeFilters.filter">Filtro: {{ activeFilters.filter }}</span>
      </div>
    </div>

    <div class="view-panel__card listing__placeholder">
      <h2>Integración pendiente</h2>
      <p>Acá mostraremos el grid de resultados conectados a la API privada del proyecto.</p>
      <p class="listing__note">
        Estado actual: preparando endpoints de sitios y favoritos para poblar esta vista.
      </p>
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

.listing__placeholder {
  text-align: center;
  background: rgba(255, 255, 255, 0.9);
}

.listing__note {
  margin-top: 0.75rem;
  color: #6b7280;
  font-size: 0.9rem;
}
</style>
