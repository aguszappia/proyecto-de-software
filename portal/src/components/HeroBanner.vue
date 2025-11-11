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
