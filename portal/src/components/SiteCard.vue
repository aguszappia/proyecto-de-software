<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { resolveSiteImageAlt, resolveSiteImageSrc } from '@/siteMedia'
import { useFavoritesStore } from '@/stores/favorites'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  site: {
    type: Object,
    required: true,
  },
})

const destination = computed(() => {
  if (props.site?.href) {
    return props.site.href
  }

  if (props.site?.id) {
    return {
      name: 'site-detail',
      params: { id: props.site.id },
    }
  }

  return '#'
})

const FALLBACK_CARD_IMAGE =
  'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=600&q=60'

const imageUrl = computed(() => props.site?.image || resolveSiteImageSrc(props.site, FALLBACK_CARD_IMAGE))
const imageAlt = computed(() => props.site?.imageAlt || resolveSiteImageAlt(props.site))

const cityLabel = computed(() => props.site?.city || 'Ciudad sin datos')
const provinceLabel = computed(() => props.site?.province || 'Provincia sin datos')

const ratingLabel = computed(() => {
  const rating = props.site?.rating
  if (typeof rating === 'number') {
    return rating.toFixed(1)
  }
  return rating || null
})

const tags = computed(() => {
  const siteTags = props.site?.tags
  if (!Array.isArray(siteTags)) return []
  return siteTags.slice(0, 5)
})

const favoritesStore = useFavoritesStore()
const auth = useAuthStore()

const siteId = computed(() => props.site?.id ?? null)

const isFavorite = computed(() => {
  if (!siteId.value) return false
  return favoritesStore.isFavorite(siteId.value)
})

const isPending = computed(() => {
  if (!siteId.value) return false
  return favoritesStore.isPending(siteId.value)
})

const showFavoriteButton = computed(() => Boolean(siteId.value))

const handleFavoriteClick = async (event) => {
  event.preventDefault()
  event.stopPropagation()
  if (!siteId.value) return
  if (isPending.value) return
  if (!auth.isAuthenticated) {
    const nextUrl = typeof window !== 'undefined' ? window.location.href : '/'
    auth.requestLoginPrompt(nextUrl)
    return
  }
  try {
    await favoritesStore.toggleFavorite(siteId.value)
  } catch (error) {
    console.error('No se pudo actualizar el favorito', error)
  }
}
</script>

<template>
  <RouterLink class="site-card" :to="destination">
    <div class="site-card__media">
      <img :src="imageUrl" :alt="imageAlt" loading="lazy" />
      <span v-if="site.badge" class="site-card__badge">
        {{ site.badge }}
      </span>
      <span v-if="ratingLabel" class="site-card__rating">
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path
            d="M12 2l2.7 6 6.3.5-4.8 4.2 1.5 6.2-5.7-3.4-5.7 3.4 1.5-6.2-4.8-4.2 6.3-.5z"
          />
        </svg>
        {{ ratingLabel }}
      </span>
      <button
        v-if="showFavoriteButton"
        class="site-card__favorite"
        type="button"
        :class="{ 'site-card__favorite--active': isFavorite }"
        :aria-pressed="isFavorite"
        :disabled="isPending"
        :title="isFavorite ? 'Quitar de favoritos' : 'Agregar a favoritos'"
        @click="handleFavoriteClick"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
          />
        </svg>
      </button>
    </div>
    <div class="site-card__body">
      <h3>{{ site.name }}</h3>
      <ul class="site-card__info">
        <li>
          <span class="site-card__label">Ciudad:</span>
          <span class="site-card__value">{{ cityLabel }}</span>
        </li>
        <li>
          <span class="site-card__label">Provincia:</span>
          <span class="site-card__value">{{ provinceLabel }}</span>
        </li>
        <li v-if="site.state">
          <span class="site-card__label">Estado:</span>
          <span class="site-card__value">{{ site.state }}</span>
        </li>
      </ul>
      <ul v-if="tags.length" class="site-card__tags">
        <li v-for="tag in tags" :key="`${site.id || site.name}-${tag}`">#{{ tag }}</li>
      </ul>
    </div>
  </RouterLink>
</template>
