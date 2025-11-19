<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import SiteCard from './SiteCard.vue'

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
  items: {
    type: Array,
    default: () => [],
  },
  ctaLabel: {
    type: String,
    default: 'Ver todos',
  },
  ctaTo: {
    type: [String, Object, null],
    default: null,
  },
  emptyMessage: {
    type: String,
    default: 'No hay información disponible para esta sección en este momento.',
  },
  loading: {
    type: Boolean,
    default: false,
  },
  refreshing: {
    type: Boolean,
    default: false,
  },
  skeletonItems: {
    type: Number,
    default: 3,
  },
  pagination: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['request-prev-page', 'request-next-page'])

const ITEMS_PER_PAGE = 3
const PLACEHOLDER_COUNT = ITEMS_PER_PAGE
const currentPage = ref(0)
const isMobile = ref(false)
let mediaQuery

const showSkeletons = computed(
  () => props.loading && (!props.items || props.items.length === 0),
)
const hasItems = computed(() => props.items && props.items.length > 0)
const totalPages = computed(() =>
  !props.items || props.items.length === 0 ? 0 : Math.ceil(props.items.length / ITEMS_PER_PAGE),
)
const needsCarousel = computed(() => totalPages.value > 1)
const showPrevButton = computed(() => !isMobile.value && needsCarousel.value && currentPage.value > 0)
const showNextButton = computed(
  () => !isMobile.value && needsCarousel.value && currentPage.value < totalPages.value - 1,
)

const showRemotePagination = computed(() => {
  const data = props.pagination
  return Boolean(data && data.pages && data.pages > 1)
})

const canRemotePrev = computed(() => {
  if (!showRemotePagination.value) {
    return false
  }
  return (props.pagination?.page || 1) > 1
})

const canRemoteNext = computed(() => {
  if (!showRemotePagination.value) {
    return false
  }
  return (props.pagination?.page || 1) < (props.pagination?.pages || 1)
})

const paginationLabel = computed(() => {
  if (!showRemotePagination.value) {
    return ''
  }
  return (
    props.pagination?.label ||
    `Página ${props.pagination?.page || 1} de ${props.pagination?.pages || 1}`
  )
})

const pageItems = computed(() => {
  const items = props.items || []
  const start = currentPage.value * ITEMS_PER_PAGE
  const slice = items.slice(start, start + ITEMS_PER_PAGE)
  return slice
})

const visibleItems = computed(() => {
  if (isMobile.value) {
    return props.items || []
  }
  return pageItems.value
})

watch(
  () => props.items,
  () => {
    currentPage.value = 0
  },
)

const handleMediaChange = (event) => {
  isMobile.value = event.matches
}

onMounted(() => {
  if (typeof window === 'undefined' || !window.matchMedia) {
    return
  }
  mediaQuery = window.matchMedia('(max-width: 640px)')
  isMobile.value = mediaQuery.matches
  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener('change', handleMediaChange)
  } else if (mediaQuery.addListener) {
    mediaQuery.addListener(handleMediaChange)
  }
})

onBeforeUnmount(() => {
  if (!mediaQuery) {
    return
  }
  if (mediaQuery.removeEventListener) {
    mediaQuery.removeEventListener('change', handleMediaChange)
  } else if (mediaQuery.removeListener) {
    mediaQuery.removeListener(handleMediaChange)
  }
})

const goToPrevPage = () => {
  if (currentPage.value === 0) return
  currentPage.value -= 1
}

const goToNextPage = () => {
  if (currentPage.value >= totalPages.value - 1) return
  currentPage.value += 1
}
</script>

<template>
  <section class="featured">
    <header class="featured__header">
      <div>
        <h2 class="featured__title">
          {{ title }}
        </h2>
        <p v-if="subtitle" class="featured__subtitle">
          {{ subtitle }}
        </p>
      </div>

      <RouterLink v-if="ctaTo" class="featured__cta" :to="ctaTo">
        {{ ctaLabel }}
      </RouterLink>
    </header>

    <div v-if="showSkeletons" class="featured__grid">
      <article v-for="index in skeletonItems" :key="index" class="featured__skeleton" />
    </div>

    <div
      v-else-if="hasItems"
      class="featured__grid-wrapper"
      :class="{ 'featured__grid-wrapper--refreshing': refreshing }"
    >
      <button
        v-if="showPrevButton"
        type="button"
        class="featured__arrow featured__arrow--left"
        @click="goToPrevPage"
        aria-label="Ver tarjetas anteriores"
      >
        ‹
      </button>
      <div class="featured__grid">
        <div
          v-for="(site, index) in visibleItems"
          :key="site?.id ?? `placeholder-${index}`"
          class="featured__slot"
        >
          <SiteCard v-if="site" :site="site" />
          <div v-else class="site-card site-card--placeholder"></div>
        </div>
      </div>
      <div v-if="refreshing" class="featured__overlay" aria-live="polite">
        Actualizando…
      </div>
      <button
        v-if="showNextButton"
        type="button"
        class="featured__arrow featured__arrow--right"
        @click="goToNextPage"
        aria-label="Ver más tarjetas"
      >
        ›
      </button>
    </div>

    <div v-if="showRemotePagination" class="featured__pagination">
      <button
        class="secondary-button"
        type="button"
        :disabled="!canRemotePrev || loading"
        @click="emit('request-prev-page')"
      >
        Anteriores
      </button>
      <span class="featured__pagination-info">
        {{ paginationLabel }}
      </span>
      <button
        class="secondary-button"
        type="button"
        :disabled="!canRemoteNext || loading"
        @click="emit('request-next-page')"
      >
        Siguientes
      </button>
    </div>

    <p v-else class="featured__empty">
      {{ emptyMessage }}
    </p>
  </section>
</template>
