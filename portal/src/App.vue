<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { refreshMaintenanceStatus, useMaintenanceState } from '@/stores/maintenance'

const maintenanceState = useMaintenanceState()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const showLogoutPrompt = ref(false)
const accountMenuOpen = ref(false)
const accountMenuRef = ref(null)

const handleLoginClick = () => {
  const origin = window.location.origin
  const fullPath = route.fullPath || '/'
  const nextUrl = `${origin}${fullPath}`
  auth.loginWithGoogle(nextUrl)
}

const handleLogoutRequest = () => {
  accountMenuOpen.value = false
  showLogoutPrompt.value = true
}

const handleLogoutCancel = () => {
  showLogoutPrompt.value = false
}

const handleLogoutConfirm = async () => {
  showLogoutPrompt.value = false
  await auth.logout()
  router.push('/')
}

const handleAccountMenuToggle = () => {
  accountMenuOpen.value = !accountMenuOpen.value
}

const handleViewProfile = () => {
  accountMenuOpen.value = false
  router.push({ name: 'profile' })
}

const handleAccountMenuClickOutside = (event) => {
  if (!accountMenuRef.value) return
  if (!accountMenuRef.value.contains(event.target)) {
    accountMenuOpen.value = false
  }
}

const handleLoginPromptCancel = () => {
  auth.cancelLoginPrompt()
}

const handleLoginPromptConfirm = () => {
  auth.confirmLoginPrompt()
}

watch(
  () => auth.isAuthenticated,
  (loggedIn) => {
    if (!loggedIn) {
      accountMenuOpen.value = false
    }
  },
)

onMounted(() => {
  auth.fetchCurrentUser()
  refreshMaintenanceStatus()
  document.addEventListener('click', handleAccountMenuClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleAccountMenuClickOutside)
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

        <div class="public-menu-row">
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
            <span class="public-cta__icon" aria-hidden="true">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 48 48"
                role="presentation"
              >
                <path
                  fill="#4285f4"
                  d="M24 9.5c3.17 0 5.36 1.37 6.6 2.51l4.82-4.7C31.99 4.46 28.3 3 24 3 14.96 3 7.46 8.46 4.32 16.02l5.94 4.6C11.59 14.59 17.29 9.5 24 9.5z"
                />
                <path
                  fill="#34a853"
                  d="M46.13 24.5c0-1.62-.15-2.8-.48-4H24v7.6h12.56c-.25 1.88-1.6 4.72-4.59 6.63l6.65 5.16C42.79 36.51 46.13 31.05 46.13 24.5z"
                />
                <path
                  fill="#fbbc05"
                  d="M10.26 28.02a14.5 14.5 0 0 1 0-8l-5.94-4.6a24 24 0 0 0 0 17.2z"
                />
                <path
                  fill="#ea4335"
                  d="M24 45c6.48 0 11.92-2.13 15.88-5.1l-6.65-5.16c-1.78 1.2-4.17 2.04-7.61 2.04-5.57 0-10.3-3.75-11.99-8.94l-5.94 4.6C7.81 41.54 15.32 45 24 45z"
                />
                <path fill="none" d="M0 0h48v48H0z" />
              </svg>
            </span>
            <span>Ingresar con Google</span>
          </button>
          <div v-else class="public-account" ref="accountMenuRef">
            <button
              class="public-account__button"
              type="button"
              aria-haspopup="menu"
              :aria-expanded="accountMenuOpen"
              @click.stop="handleAccountMenuToggle"
            >
              <span>Mi cuenta</span>
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
            <div v-if="accountMenuOpen" class="public-account__menu" role="menu">
              <button type="button" role="menuitem" @click="handleViewProfile">
                Ver perfil
              </button>
              <button type="button" role="menuitem" @click="handleLogoutRequest">
                Cerrar sesión
              </button>
            </div>
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

    <div
      v-if="showLogoutPrompt"
      class="public-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="logout-dialog-title"
    >
      <div class="public-modal__backdrop"></div>
      <div class="public-modal__card" role="document">
        <h2 id="logout-dialog-title">Cerrar sesión</h2>
        <p>¿Seguro que querés cerrar sesión? Perderás el acceso hasta volver a iniciar.</p>
        <div class="public-modal__actions">
          <button class="public-modal__button" type="button" @click="handleLogoutCancel">
            Cancelar
          </button>
          <button
            class="public-modal__button public-modal__button--danger"
            type="button"
            @click="handleLogoutConfirm"
          >
            Salir
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="auth.loginPromptVisible"
      class="public-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="login-dialog-title"
    >
      <div class="public-modal__backdrop" @click="handleLoginPromptCancel"></div>
      <div class="public-modal__card" role="document">
        <h2 id="login-dialog-title">Iniciá sesión para continuar</h2>
        <p>
          Debés iniciar sesión para guardar sitios como favoritos. ¿Querés hacerlo ahora?
        </p>
        <div class="public-modal__actions">
          <button class="public-modal__button" type="button" @click="handleLoginPromptCancel">
            Ahora no
          </button>
          <button
            class="public-modal__button public-modal__button--primary"
            type="button"
            @click="handleLoginPromptConfirm"
          >
            Ingresar con Google
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
