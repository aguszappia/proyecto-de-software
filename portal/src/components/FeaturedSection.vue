<script setup>
import { computed } from 'vue'
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

const showSkeletons = computed(() => props.loading)
const hasItems = computed(() => props.items && props.items.length > 0)
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

    <div v-else-if="hasItems" class="featured__grid">
      <SiteCard v-for="site in items" :key="site.id" :site="site" />
    </div>

    <p v-else class="featured__empty">
      {{ emptyMessage }}
    </p>
  </section>
</template>
