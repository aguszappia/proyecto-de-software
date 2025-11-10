<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <section class="view-panel">
    <div class="view-panel__card">
      <p class="view-panel__subtitle">Sitio seleccionado</p>
      <h1>{{ route.params.id }}</h1>
      <p>
        Aquí construiremos la ficha completa con galería, reseñas y horarios obtenidos desde la API
        privada. Por ahora mostramos la maquetación y la jerarquía visual para mantener consistencia
        con los templates del admin.
      </p>
    </div>

    <div class="view-panel__card detail__content">
      <p>
        Información, fotografías, horarios y calificaciones se verán en esta sección. También
        sumaremos acciones rápidas para compartir el sitio o iniciar trámites según corresponda.
      </p>
      <p class="detail__note">Estado: pendiente de definir estructura final.</p>
    </div>
  </section>
</template>

<style scoped>
.detail__content {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.3);
}

.detail__note {
  margin-top: 0.75rem;
  font-size: 0.9rem;
  color: #6b7280;
}
</style>
