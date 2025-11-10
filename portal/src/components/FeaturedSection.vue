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

<style scoped>
.featured {
  padding: 1.25rem;
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
}

.featured__header {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.featured__title {
  font-size: 1.4rem;
  margin: 0;
  color: #0f172a;
}

.featured__subtitle {
  color: #374151;
  margin: 0.2rem 0 0;
}

.featured__cta {
  align-self: flex-start;
  font-weight: 600;
  color: var(--color-primary);
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  border: 1px solid rgba(37, 99, 235, 0.2);
  background: rgba(37, 99, 235, 0.08);
}

.featured__grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}

.featured__empty {
  padding: 1.25rem;
  background-color: #f9fafb;
  border: 1px dashed #d1d5db;
  border-radius: 0.75rem;
  color: #475569;
  text-align: center;
}

.featured__skeleton {
  min-height: 190px;
  border-radius: 1rem;
  background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 37%, #f3f4f6 63%);
  background-size: 400% 100%;
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}

@media (min-width: 768px) {
  .featured__header {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}
</style>
