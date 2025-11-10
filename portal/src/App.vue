<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="public-shell">
    <div class="public-shell__glow public-shell__glow--one" aria-hidden="true"></div>
    <div class="public-shell__glow public-shell__glow--two" aria-hidden="true"></div>

    <div class="public-shell__inner">
      <header class="public-header">
        <RouterLink class="public-brand" to="/">
          <img alt="Logo Sitios Históricos" src="@/assets/logo.svg" />
          <div>
            <span>Sitios Históricos</span>
            <p>Portal público</p>
          </div>
        </RouterLink>

        <nav class="public-nav" aria-label="Navegación principal">
          <RouterLink to="/">Inicio</RouterLink>
          <RouterLink to="/sitios">Sitios</RouterLink>
          <RouterLink to="/map">Mapa</RouterLink>
          <RouterLink to="/about">Nosotros</RouterLink>
        </nav>

        <button class="public-cta" type="button">
          Ingresar
        </button>
      </header>

      <main class="public-main">
        <RouterView />
      </main>

      <footer class="public-footer">
        <p>© {{ new Date().getFullYear() }} Sitios Históricos.</p>
        <nav aria-label="Navegación secundaria">
          <RouterLink to="/sitios">Sitios</RouterLink>
          <RouterLink to="/map">Mapa interactivo</RouterLink>
          <RouterLink to="/about">Nosotros</RouterLink>
        </nav>
      </footer>
    </div>
  </div>
</template>
