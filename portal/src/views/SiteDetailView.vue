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
