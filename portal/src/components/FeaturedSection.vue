<script setup>
import { computed, ref, watch } from 'vue'
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
  skeletonItems: {
    type: Number,
    default: 3,
  },
})

const ITEMS_PER_PAGE = 3
const PLACEHOLDER_COUNT = ITEMS_PER_PAGE
const currentPage = ref(0)

const showSkeletons = computed(() => props.loading)
const hasItems = computed(() => props.items && props.items.length > 0)
const totalPages = computed(() =>
  !props.items || props.items.length === 0 ? 0 : Math.ceil(props.items.length / ITEMS_PER_PAGE),
)
const needsCarousel = computed(() => totalPages.value > 1)

const pageItems = computed(() => {
  const items = props.items || []
  const start = currentPage.value * ITEMS_PER_PAGE
  const slice = items.slice(start, start + ITEMS_PER_PAGE)
  return slice
})

watch(
  () => props.items,
  () => {
    currentPage.value = 0
  },
)

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

    <div v-else-if="hasItems" class="featured__grid-wrapper">
      <button
        v-if="needsCarousel && currentPage > 0"
        type="button"
        class="featured__arrow featured__arrow--left"
        @click="goToPrevPage"
        aria-label="Ver tarjetas anteriores"
      >
        ‹
      </button>
      <div class="featured__grid">
        <div
          v-for="(site, index) in pageItems"
          :key="site?.id ?? `placeholder-${index}`"
          class="featured__slot"
        >
          <SiteCard v-if="site" :site="site" />
          <div v-else class="site-card site-card--placeholder"></div>
        </div>
      </div>
      <button
        v-if="needsCarousel && currentPage < totalPages - 1"
        type="button"
        class="featured__arrow featured__arrow--right"
        @click="goToNextPage"
        aria-label="Ver más tarjetas"
      >
        ›
      </button>
    </div>

    <p v-else class="featured__empty">
      {{ emptyMessage }}
    </p>
  </section>
</template>
