<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import API_BASE_URL from '@/constants/api'
import { useAuthStore } from '@/stores/auth'

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

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const handleLoginClick = () => {
  const origin = window.location.origin
  const fullPath = route.fullPath || '/'
  const nextUrl = `${origin}${fullPath}`
  auth.loginWithGoogle(nextUrl)
}

const handleLogoutClick = async () => {
  await auth.logout()
  router.push('/')
}

onMounted(() => {
  auth.fetchCurrentUser()
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

        <div class="public-auth-area">
          <button
            v-if="!auth.isAuthenticated"
            class="public-cta"
            type="button"
            @click="handleLoginClick"
          >
            Ingresar con Google
          </button>
          <div v-else class="public-user-info">
            <img
              v-if="auth.user?.avatar"
              :src="auth.user.avatar"
              alt="Avatar"
              class="public-user-avatar"
              referrerpolicy="no-referrer"
            />
            <div class="public-user-details">
              <span class="public-user-name">{{ auth.user?.name }}</span>
              <button class="public-logout-button" type="button" @click="handleLogoutClick">
                Cerrar sesión
              </button>
            </div>
          </div>
        </div>
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
