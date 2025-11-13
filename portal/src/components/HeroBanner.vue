<script setup>
import { computed, onMounted, ref } from 'vue'

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
  variant: {
    type: String,
    default: 'default',
  },
  backgroundImage: {
    type: String,
    default: '',
  },
  scrollLabel: {
    type: String,
    default: 'Ver destacados',
  },
  scrollTarget: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['search'])
const HISTORY_KEY = 'portal_search_history'

const searchTerm = ref('')
const searchHistory = ref([])
const showHistory = ref(false)
const hideTimeout = ref(null)

const handleSubmit = () => {
  const term = searchTerm.value.trim()
  if (!term) {
    if (searchHistory.value.length) {
      showHistory.value = true
    }
    return
  }
  saveTerm(term)
  emit('search', term)
  showHistory.value = false
}

const saveTerm = (term) => {
  const history = [term, ...searchHistory.value.filter((item) => item.toLowerCase() !== term.toLowerCase())].slice(0, 6)
  searchHistory.value = history
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history))
}

const heroClasses = computed(() => ['hero', props.variant ? `hero--${props.variant}` : null])

const filteredHistory = computed(() => {
  if (!searchTerm.value) {
    return searchHistory.value
  }
  const needle = searchTerm.value.toLowerCase()
  return searchHistory.value.filter((item) => item.toLowerCase().includes(needle))
})

const heroStyle = computed(() =>
  props.backgroundImage
    ? {
        backgroundImage: `linear-gradient(120deg, rgba(5, 6, 12, 0.75), rgba(4, 16, 39, 0.75)), url(${props.backgroundImage})`,
      }
    : {},
)

const handleScroll = () => {
  if (!props.scrollTarget) return
  const el = document.getElementById(props.scrollTarget)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  }
}

const handleFocus = () => {
  if (hideTimeout.value) {
    clearTimeout(hideTimeout.value)
    hideTimeout.value = null
  }
  if (searchHistory.value.length) {
    showHistory.value = true
  }
}

const handleBlur = () => {
  hideTimeout.value = window.setTimeout(() => {
    showHistory.value = false
  }, 120)
}

const handleSelectHistory = (term) => {
  searchTerm.value = term
  showHistory.value = false
  emit('search', term)
}

onMounted(() => {
  try {
    const stored = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
    if (Array.isArray(stored)) {
      searchHistory.value = stored.slice(0, 6)
    }
  } catch (error) {
    searchHistory.value = []
  }
})
</script>

<template>
  <section :class="heroClasses" :style="heroStyle">
    <div class="hero__content">
      <div class="hero__copy">
        <p v-if="eyebrow" class="hero__eyebrow">
          {{ eyebrow }}
        </p>
        <h1 class="hero__title">
          {{ title }}
        </h1>
        <p v-if="description" class="hero__description">
          {{ description }}
        </p>
      </div>

      <div class="hero__search">
        <form class="hero__search-bar" @submit.prevent="handleSubmit">
          <input
            id="hero-search-input"
            v-model="searchTerm"
            class="hero__input"
            type="search"
            :placeholder="searchPlaceholder"
            aria-label="Buscar sitios históricos"
            autocomplete="off"
            @focus="handleFocus"
            @blur="handleBlur"
          />
          <button class="hero__button" type="submit" aria-label="Buscar">
            <svg viewBox="0 0 24 24" focusable="false">
              <path
                d="M15.5 14h-.79l-.28-.27A6 6 0 0 0 16 9a6 6 0 1 0-6 6 6 6 0 0 0 3.73-1.3l.27.28v.79L20 20.49 21.49 19 15.5 14zM10 14a4 4 0 1 1 0-8 4 4 0 0 1 0 8z"
                fill="currentColor"
              />
            </svg>
          </button>
          <ul v-if="showHistory && filteredHistory.length" class="hero__history" data-testid="search-history">
            <li v-for="term in filteredHistory" :key="term" @mousedown.prevent="handleSelectHistory(term)">
              {{ term }}
            </li>
          </ul>
        </form>
        <p v-if="hint" class="hero__hint">
          {{ hint }}
        </p>
      </div>

      <button v-if="scrollTarget" class="hero__scroll" type="button" @click="handleScroll">
        {{ scrollLabel }}
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 16.5 5 9.75l1.4-1.4L12 13.75l5.6-5.4 1.4 1.4Z" fill="currentColor" />
        </svg>
      </button>
    </div>
  </section>
</template>
