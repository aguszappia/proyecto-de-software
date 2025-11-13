<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import API_BASE_URL from '@/constants/api'

const maintenanceState = ref({
  pending: true,
  enabled: false,
  message: '',
})

const MAINTENANCE_FALLBACK_MESSAGE =
  'Estamos realizando tareas de mantenimiento. Volvé a intentarlo en unos minutos.'

const loadMaintenanceStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/status`, {
      headers: {
        Accept: 'application/json',
      },
    })
    if (!response.ok) {
      throw new Error('Failed to fetch maintenance status')
    }
    const payload = await response.json()
    const portalState = payload?.maintenance?.portal || {}
    const isEnabled = Boolean(portalState.enabled)
    maintenanceState.value = {
      pending: false,
      enabled: isEnabled,
      message: isEnabled
        ? portalState.message || MAINTENANCE_FALLBACK_MESSAGE
        : '',
    }
  } catch (error) {
    maintenanceState.value = {
      pending: false,
      enabled: false,
      message: '',
    }
  }
}

onMounted(() => {
  loadMaintenanceStatus()
})
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
          <RouterLink to="/sitios">Sitios</RouterLink>
          <RouterLink to="/about">Nosotros</RouterLink>
        </nav>

        <button class="public-cta" type="button">
          Ingresar
        </button>
      </header>

      <main
        v-if="!maintenanceState.pending && !maintenanceState.enabled"
        class="public-main"
      >
        <RouterView />
      </main>

      <section v-else-if="maintenanceState.enabled" class="maintenance-view" role="alert">
        <div class="maintenance-view__icon" aria-hidden="true">⚠️</div>
        <h1>Portal en mantenimiento</h1>
        <p>{{ maintenanceState.message }}</p>
        <p class="maintenance-view__note">Nuestro equipo está trabajando para restablecer el servicio.</p>
      </section>

      <section v-else class="maintenance-loading" aria-busy="true">
        <div class="maintenance-view__icon" aria-hidden="true">⏱️</div>
        <h1>Verificando estado del portal…</h1>
        <p>Por favor aguardá un momento.</p>
      </section>

      <footer class="public-footer">
        <p>© {{ new Date().getFullYear() }} Sitios Históricos.</p>
        <nav aria-label="Navegación secundaria">
          <RouterLink to="/sitios">Sitios</RouterLink>
          <RouterLink to="/about">Nosotros</RouterLink>
        </nav>
      </footer>
    </div>
  </div>
</template>
