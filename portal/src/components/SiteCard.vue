<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

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

const imageUrl = computed(() => props.site?.image || 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=600&q=60')

const locationLabel = computed(() => {
  const city = props.site?.city
  const province = props.site?.province

  if (city && province) return `${city}, ${province}`
  return city || province || 'Ubicación por confirmar'
})

const ratingLabel = computed(() => {
  const rating = props.site?.rating
  if (typeof rating === 'number') {
    return rating.toFixed(1)
  }
  return rating || null
})
</script>

<template>
  <RouterLink class="site-card" :to="destination">
    <div class="site-card__media">
      <img :src="imageUrl" :alt="site.name" loading="lazy" />
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
    </div>
    <div class="site-card__body">
      <h3>{{ site.name }}</h3>
      <p>{{ locationLabel }}</p>
      <div class="site-card__meta">
        <span v-if="site.category">{{ site.category }}</span>
        <span v-if="site.updatedAt">Actualizado {{ site.updatedAt }}</span>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.site-card {
  display: block;
  border-radius: 1.35rem;
  overflow: hidden;
  background: rgba(248, 250, 252, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.35);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.12);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  color: inherit;
}

.site-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 25px 60px rgba(15, 23, 42, 0.16);
}

.site-card__media {
  position: relative;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.site-card__media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.site-card:hover img {
  transform: scale(1.05);
}

.site-card__badge {
  position: absolute;
  top: 0.75rem;
  left: 0.75rem;
  background-color: #fff;
  color: #1e3a8a;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.site-card__rating {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background-color: rgba(15, 23, 42, 0.8);
  color: #fff;
  padding: 0.25rem 0.45rem;
  border-radius: 0.6rem;
  font-weight: 600;
  font-size: 0.85rem;
}

.site-card__rating svg {
  width: 16px;
  height: 16px;
  fill: currentColor;
}

.site-card__body {
  padding: 1.1rem 1.35rem 1.3rem;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.95));
}

.site-card__body h3 {
  margin: 0 0 0.4rem;
  font-size: 1rem;
  color: #111827;
}

.site-card__body p {
  margin: 0 0 0.65rem;
  color: #6b7280;
  font-size: 0.95rem;
}

.site-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: #4b5563;
}
</style>
