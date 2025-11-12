<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LMap, LMarker, LPopup, LTileLayer, LTooltip } from '@vue-leaflet/vue-leaflet'
import 'leaflet/dist/leaflet.css'
import API_BASE_URL from '@/constants/api'

const route = useRoute()
const router = useRouter()

const site = ref(null)
const loading = ref(false)
const error = ref(null)
const descriptionExpanded = ref(false)
const galleryIndex = ref(0)
const DEFAULT_SITE_IMAGE =
  'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1200&q=60'

const normalizeSite = (payload) => {
  if (!payload) return null
  const tags = Array.isArray(payload.tags) ? payload.tags.filter(Boolean) : []
  const images = Array.isArray(payload.images) ? payload.images : []
  const normalizeImageEntry = (entry) => {
    if (!entry) return null
    if (typeof entry === 'string') {
      return { src: entry, alt: payload.name || 'Sitio histórico' }
    }
    if (typeof entry === 'object') {
      const src = entry.src || entry.url || entry.image_url || entry.imageUrl
      if (!src) {
        return null
      }
      return { src, alt: entry.alt || entry.title || payload.name || 'Sitio histórico' }
    }
    return null
  }

  const galleryImages = images.map(normalizeImageEntry).filter(Boolean)
  const coverImageSrc =
    payload.cover_image_url ||
    payload.coverImageUrl ||
    (typeof payload.cover_image === 'string' ? payload.cover_image : payload.cover_image?.url)
  if (coverImageSrc) {
    galleryImages.unshift({
      src: coverImageSrc,
      alt: payload.cover_image_title || payload.name || 'Sitio histórico',
    })
  }

  return {
    id: payload.id,
    name: payload.name,
    city: payload.city,
    province: payload.province,
    state: payload.state_of_conservation || payload.conservation_status || null,
    shortDescription: payload.short_description || '',
    fullDescription:
      payload.description || payload.full_description || payload.short_description || '',
    tags,
    latitude: typeof payload.lat === 'number' ? payload.lat : payload.latitude ?? null,
    longitude: typeof payload.long === 'number' ? payload.long : payload.longitude ?? null,
    updatedAt: payload.updated_at || payload.inserted_at || null,
    images: galleryImages,
  }
}

const fetchSiteDetails = async (id) => {
  if (!id) return
  loading.value = true
  error.value = null
  site.value = null
  descriptionExpanded.value = false
  galleryIndex.value = 0
  try {
    const response = await fetch(`${API_BASE_URL}/sites/${id}`)
    if (response.status === 404) {
      throw new Error('not_found')
    }
    if (!response.ok) {
      throw new Error('server_error')
    }
    const payload = await response.json()
    site.value = normalizeSite(payload)
  } catch (err) {
    error.value = err.message === 'not_found' ? 'El sitio no existe o no es público.' : null
    if (!error.value) {
      error.value = 'No pudimos cargar la información. Intentá nuevamente en unos minutos.'
    }
  } finally {
    loading.value = false
  }
}

watch(
  () => route.params.id,
  (newId) => {
    if (newId) {
      fetchSiteDetails(newId)
    }
  },
  { immediate: true },
)

const galleryImages = computed(() => {
  if (!site.value) return []
  const pool = Array.isArray(site.value.images) ? site.value.images : []
  if (!pool.length) {
    return [
      {
        src: DEFAULT_SITE_IMAGE,
        alt: `Vista referencial de ${site.value.name || 'sitio histórico'}`,
      },
    ]
  }
  return pool
})

watch(galleryImages, () => {
  galleryIndex.value = 0
})

const selectedImage = computed(() => galleryImages.value[galleryIndex.value] || null)

const formatStateLabel = (value) => {
  if (!value) return 'Estado sin datos'
  const normalized = String(value)
    .replace(/_/g, ' ')
    .toLowerCase()
  return normalized.charAt(0).toUpperCase() + normalized.slice(1)
}

const stateLabel = computed(() => formatStateLabel(site.value?.state))

const stateChipClass = computed(() => {
  const value = (site.value?.state || '').toString().toLowerCase()
  if (value.includes('excelente') || value.includes('bueno')) return 'detail-chip--good'
  if (value.includes('regular')) return 'detail-chip--warning'
  if (value.includes('malo') || value.includes('bad')) return 'detail-chip--bad'
  return 'detail-chip--neutral'
})

const locationLabel = computed(() => {
  const city = site.value?.city
  const province = site.value?.province
  if (city && province) return `${city}, ${province}`
  return city || province || 'Ubicación pendiente'
})

const hasDescription = computed(
  () => Boolean(site.value?.shortDescription) || Boolean(site.value?.fullDescription),
)

const DESCRIPTION_COLLAPSE_AT = 420

const longDescription = computed(() => site.value?.fullDescription || '')

const displayedDescription = computed(() => {
  const description = longDescription.value
  if (!description) return ''
  if (descriptionExpanded.value || description.length <= DESCRIPTION_COLLAPSE_AT) {
    return description
  }
  return `${description.slice(0, DESCRIPTION_COLLAPSE_AT)}…`
})

const canToggleDescription = computed(
  () => (longDescription.value?.length || 0) > DESCRIPTION_COLLAPSE_AT,
)

const coordinates = computed(() => {
  const lat = site.value?.latitude
  const lon = site.value?.longitude
  if (typeof lat !== 'number' || typeof lon !== 'number') {
    return null
  }
  return [lat, lon]
})

const MAP_DEFAULT_ZOOM = 8
const mapZoom = computed(() => {
  if (!coordinates.value) return 5
  if (site.value?.city) return MAP_DEFAULT_ZOOM
  return 11
})

const popupDescription = computed(() => {
  if (site.value?.shortDescription) {
    return site.value.shortDescription
  }
  if (site.value?.fullDescription) {
    return site.value.fullDescription.slice(0, 120)
  }
  return 'Pronto sumaremos la descripción de este sitio.'
})

const handleGalleryNav = (direction) => {
  if (!galleryImages.value.length) return
  const total = galleryImages.value.length
  galleryIndex.value = (galleryIndex.value + direction + total) % total
}

const handleBackClick = () => {
  router.push({
    name: 'sites',
    query: { ...route.query },
  })
}

const handleTagClick = (tag) => {
  if (!tag) return
  router.push({
    name: 'sites',
    query: {
      ...route.query,
      tags: tag,
    },
  })
}

const handleRetry = () => {
  fetchSiteDetails(route.params.id)
}
</script>

<template>
  <section class="site-detail view-panel">
    <button class="site-detail__back secondary-button" type="button" @click="handleBackClick">
      ← Volver al listado
    </button>

    <div v-if="loading" class="view-panel__card detail__content">
      <p>Cargando información del sitio…</p>
    </div>

    <div v-else-if="error" class="view-panel__card detail__content">
      <p class="detail__note">{{ error }}</p>
      <div class="view-panel__actions">
        <button class="primary-button" type="button" @click="handleRetry">Reintentar</button>
      </div>
    </div>

    <template v-else-if="site">
      <article class="site-detail__hero view-panel__card">
        <header>
          <p class="view-panel__subtitle">Sitio seleccionado</p>
          <h1>{{ site.name }}</h1>
          <p class="site-detail__location">{{ locationLabel }}</p>
        </header>

        <div class="site-detail__meta">
          <span class="detail-chip" :class="stateChipClass">{{ stateLabel }}</span>
          <p v-if="site.updatedAt" class="site-detail__updated">
            Última actualización: {{ new Date(site.updatedAt).toLocaleDateString('es-AR') }}
          </p>
        </div>
      </article>

      <article v-if="selectedImage" class="site-detail__gallery view-panel__card">
        <figure class="gallery__image">
          <img :src="selectedImage.src" :alt="selectedImage.alt" loading="lazy" />
        </figure>
        <div v-if="galleryImages.length > 1" class="gallery__controls">
          <button
            type="button"
            class="gallery__arrow"
            aria-label="Ver imagen anterior"
            @click="handleGalleryNav(-1)"
          >
            ‹
          </button>
          <div class="gallery__indicators" role="tablist" aria-label="Seleccionar imagen">
            <button
              v-for="(image, index) in galleryImages"
              :key="image.src"
              class="gallery__indicator"
              :class="{ 'gallery__indicator--active': galleryIndex === index }"
              type="button"
              :aria-label="`Ver imagen ${index + 1}`"
              @click="galleryIndex = index"
            />
          </div>
          <button
            type="button"
            class="gallery__arrow"
            aria-label="Ver imagen siguiente"
            @click="handleGalleryNav(1)"
          >
            ›
          </button>
        </div>
      </article>

      <article v-if="hasDescription" class="site-detail__description view-panel__card">
        <p v-if="site.shortDescription" class="site-detail__summary">{{ site.shortDescription }}</p>
        <p v-if="longDescription" class="site-detail__full">{{ displayedDescription }}</p>
        <button
          v-if="canToggleDescription"
          class="secondary-button description__toggle"
          type="button"
          @click="descriptionExpanded = !descriptionExpanded"
        >
          {{ descriptionExpanded ? 'Ver menos' : 'Ver más' }}
        </button>
      </article>

      <article v-if="site.tags?.length" class="site-detail__tags view-panel__card">
        <p class="view-panel__subtitle">Etiquetas</p>
        <ul class="site-detail__tag-list">
          <li v-for="tag in site.tags" :key="tag">
            <button class="tag-pill" type="button" @click="handleTagClick(tag)">#{{ tag }}</button>
          </li>
        </ul>
      </article>

      <article class="site-detail__map view-panel__card">
        <p class="view-panel__subtitle">Ubicación</p>
        <p v-if="!coordinates" class="detail__note">
          Este sitio todavía no tiene coordenadas para mostrar en el mapa.
        </p>
        <div v-else class="site-detail__map-canvas">
          <l-map class="site-detail__leaflet" :zoom="mapZoom" :center="coordinates" :zoom-control="false">
            <l-tile-layer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <l-marker :lat-lng="coordinates">
              <l-popup>
                <strong>{{ site.name }}</strong>
                <p>{{ popupDescription }}</p>
              </l-popup>
              <l-tooltip sticky>{{ site.name }}</l-tooltip>
            </l-marker>
          </l-map>
        </div>
      </article>
    </template>
  </section>
</template>
