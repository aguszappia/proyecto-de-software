<script setup>
import { ref } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
  eyebrow: {
    type: String,
    default: '',
  },
  searchPlaceholder: {
    type: String,
    default: 'Buscar sitios',
  },
  ctaLabel: {
    type: String,
    default: 'Buscar',
  },
  hint: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['search'])

const searchTerm = ref('')

const handleSubmit = () => {
  emit('search', searchTerm.value.trim())
}
</script>

<template>
  <section class="hero">
    <div class="hero__content">
      <p v-if="eyebrow" class="hero__eyebrow">
        {{ eyebrow }}
      </p>
      <h1 class="hero__title">
        {{ title }}
      </h1>
      <p v-if="description" class="hero__description">
        {{ description }}
      </p>

      <form class="hero__search" @submit.prevent="handleSubmit">
        <input
          v-model="searchTerm"
          class="hero__input"
          type="search"
          :placeholder="searchPlaceholder"
        />
        <button class="hero__button" type="submit">
          {{ ctaLabel }}
        </button>
      </form>

      <p v-if="hint" class="hero__hint">
        {{ hint }}
      </p>
    </div>
  </section>
</template>

<style scoped>
.hero {
  margin: 0 auto;
  padding: clamp(2rem, 5vw, 3.5rem);
  border-radius: 32px;
  background: linear-gradient(135deg, #112044, #1f3e63 60%, #2563eb);
  color: #fff;
  box-shadow: 0 35px 80px rgba(8, 15, 52, 0.45);
  position: relative;
  overflow: hidden;
}

.hero::after {
  content: '';
  position: absolute;
  inset: 1.5rem;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  opacity: 0.35;
  pointer-events: none;
}

.hero__content {
  position: relative;
  z-index: 1;
  max-width: 720px;
}

.hero__eyebrow {
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.2em;
  color: rgba(255, 255, 255, 0.75);
  margin-bottom: 0.75rem;
}

.hero__title {
  font-size: clamp(2.2rem, 5vw, 3.4rem);
  margin: 0 0 1rem;
  line-height: 1.1;
}

.hero__description {
  margin: 0 0 1.5rem;
  color: rgba(255, 255, 255, 0.85);
  font-size: 1rem;
}

.hero__search {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(14px);
}

.hero__input {
  width: 100%;
  padding: 0.9rem 1.25rem;
  border: none;
  border-radius: 999px;
  font-size: 1rem;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.9);
  color: #0f172a;
}

.hero__input:focus {
  outline: 2px solid rgba(255, 255, 255, 0.6);
}

.hero__button {
  padding: 0.9rem 1.5rem;
  border-radius: 999px;
  border: none;
  font-weight: 600;
  font-size: 1rem;
  background: linear-gradient(135deg, #fbbf24, #f97316);
  color: #111827;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.hero__button:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 30px rgba(8, 15, 52, 0.35);
}

.hero__hint {
  margin-top: 0.75rem;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.78);
}

@media (min-width: 640px) {
  .hero__search {
    flex-direction: row;
    align-items: center;
  }

  .hero__input {
    flex: 1;
  }

  .hero__button {
    min-width: 140px;
  }
}
</style>
