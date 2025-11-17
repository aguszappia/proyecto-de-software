<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <section class="maintenance-view not-found-view" role="alert">
    <div class="maintenance-view__icon" aria-hidden="true">🔎</div>
    <h1>Página no encontrada</h1>
    <p>No pudimos encontrar la página que estabas buscando.</p>
    <p class="maintenance-view__note">
      Verificá la dirección o navegá nuevamente desde la página principal.
    </p>
    <RouterLink class="primary-button not-found-view__cta" to="/">Volver al inicio</RouterLink>
  </section>
</template>

<style scoped>
.not-found-view__cta {
  margin-top: 16px;
}
</style>
