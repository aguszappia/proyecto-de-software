<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import SiteCard from '@/components/SiteCard.vue'
import { useAuthStore } from '@/stores/auth'
import { useFavoritesStore } from '@/stores/favorites'
import API_BASE_URL from '@/constants/api'
import { resolveSiteImageAlt, resolveSiteImageSrc } from '@/siteMedia'

const auth = useAuthStore()
const router = useRouter()
const favoritesStore = useFavoritesStore()

const favoriteSites = ref([])
const favoritesLoading = ref(false)
const favoritesError = ref('')
let suppressFavoriteWatch = false

const GENERIC_SITE_IMAGE_URL =
  'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1200&q=60'

const normalizeFavoriteSite = (site) => ({
  id: site.id,
  name: site.name,
  city: site.city,
  province: site.province,
  state:
    site.state_of_conservation ??
    site.conservation_status ??
    site.state ??
    null,
  rating:
    typeof site.rating === 'number'
      ? site.rating
      : site.average_rating ?? site.averageRating ?? null,
  tags: Array.isArray(site.tags) ? site.tags.slice(0, 5) : [],
  image: resolveSiteImageSrc(site, GENERIC_SITE_IMAGE_URL),
  imageAlt: resolveSiteImageAlt(site),
  href: site.id ? { name: 'site-detail', params: { id: site.id } } : null,
})

const resolvedProfileRoute = computed(() => {
  if (typeof window === 'undefined') {
    return '/perfil'
  }
  const resolved = router.resolve({ name: 'profile' })
  return `${window.location.origin}${resolved.href}`
})

const handleProfileLogin = () => {
  auth.loginWithGoogle(resolvedProfileRoute.value)
}

const loadFavoriteSites = async () => {
  if (!auth.isAuthenticated) {
    favoriteSites.value = []
    favoritesError.value = ''
    favoritesLoading.value = false
    return
  }

  favoritesLoading.value = true
  favoritesError.value = ''
  const params = new URLSearchParams({
    filter: 'favorites',
    per_page: '50',
    page: '1',
    order_by: 'latest',
  })

  try {
    const response = await fetch(`${API_BASE_URL}/sites?${params.toString()}`, {
      credentials: 'include',
    })
    if (!response.ok) {
      throw new Error('No pudimos cargar tus sitios favoritos. Intentá más tarde.')
    }
    const payload = await response.json()
    const items = Array.isArray(payload?.data) ? payload.data : []
    suppressFavoriteWatch = true
    favoritesStore.hydrateFromSites(items)
    favoriteSites.value = items.map(normalizeFavoriteSite)
  } catch (error) {
    favoritesError.value = error.message || 'No pudimos cargar tus favoritos.'
  } finally {
    suppressFavoriteWatch = false
    favoritesLoading.value = false
  }
}

const favoriteCards = computed(() =>
  favoriteSites.value.filter((site) => favoritesStore.isFavorite(site.id)),
)

const handleRefreshFavorites = () => {
  if (!favoritesLoading.value) {
    loadFavoriteSites()
  }
}

watch(
  () => auth.isAuthenticated,
  (logged) => {
    if (logged) {
      loadFavoriteSites()
    } else {
      favoriteSites.value = []
    }
  },
)

onMounted(() => {
  if (auth.isAuthenticated) {
    loadFavoriteSites()
  }
})

watch(
  () => favoritesStore.favoriteIds.length,
  (newCount, oldCount) => {
    if (!auth.isAuthenticated || suppressFavoriteWatch) return
    if (newCount > oldCount) {
      loadFavoriteSites()
    } else {
      favoriteSites.value = favoriteSites.value.filter((site) =>
        favoritesStore.isFavorite(site.id),
      )
    }
  },
)
</script>

<template>
  <section class="view-panel profile-view">
    <div class="view-panel__card">
      <p class="view-panel__subtitle">Tu espacio</p>
      <h1>Mi perfil</h1>
      <p>Pronto vas a poder gestionar tus favoritos y postulaciones desde aquí.</p>
    </div>

    <div
      v-if="!auth.isAuthenticated"
      class="view-panel__card profile-card view-panel__card--centered"
    >
      <h2>Necesitás iniciar sesión</h2>
      <p>Iniciá sesión para acceder a tu perfil y a tus contenidos guardados.</p>
      <button class="primary-button" type="button" @click="handleProfileLogin">
        Ingresar con Google
      </button>
    </div>

    <div v-else class="view-panel__card profile-card">
      <div class="profile-card__header">
        <div class="profile-avatar" aria-hidden="true">
          <img
            v-if="auth.user?.avatar"
            :src="auth.user.avatar"
            alt="Avatar de perfil"
            referrerpolicy="no-referrer"
          />
          <span v-else>{{ (auth.user?.name || auth.user?.email || 'U')[0].toUpperCase() }}</span>
        </div>
        <div>
          <h2>{{ auth.user?.name || 'Usuario' }}</h2>
          <p>{{ auth.user?.email || 'Correo no disponible' }}</p>
        </div>
      </div>
      <dl class="profile-meta">
        <div>
          <dt>Estado</dt>
          <dd>Sesión activa</dd>
        </div>
        <div>
          <dt>Última actividad</dt>
          <dd>Disponible pronto</dd>
        </div>
      </dl>
      <p class="profile-note">
        Estamos trabajando para habilitar reseñas, favoritos y más acciones dentro de tu perfil.
      </p>
    </div>

    <div
      v-if="auth.isAuthenticated"
      class="view-panel__card profile-favorites"
    >
      <div class="profile-favorites__header">
        <div>
          <p class="view-panel__subtitle">Favoritos</p>
          <h2>Sitios guardados</h2>
        </div>
      </div>
      <div v-if="favoritesLoading" class="profile-favorites__empty">
        Cargando tus favoritos…
      </div>
      <div v-else-if="favoritesError" class="profile-favorites__empty">
        {{ favoritesError }}
      </div>
      <div v-else-if="favoriteCards.length === 0" class="profile-favorites__empty">
        Todavía no marcaste sitios como favoritos.
      </div>
      <div v-else class="profile-favorites__grid">
        <SiteCard v-for="site in favoriteCards" :key="site.id" :site="site" />
      </div>
    </div>
  </section>
</template>
