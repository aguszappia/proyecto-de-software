import { defineStore } from 'pinia'
import API_BASE_URL from '@/constants/api'

const REVIEWS_DISABLED_FALLBACK_MESSAGE =
  'La creación de reseñas está deshabilitada temporalmente.\n\nEstamos trabajando para habilitarlas nuevamente pronto.'

const defaultFlagsState = () => ({
  reviews: {
    enabled: true,
    message: '',
  },
})

export const useFeatureFlagsStore = defineStore('featureFlags', {
  state: () => ({
    flags: defaultFlagsState(),
    loading: false,
    loaded: false,
    error: '',
  }),
  getters: {
    reviewsEnabled: (state) => {
      const reviewsFlag = state.flags?.reviews
      if (!reviewsFlag) {
        return true
      }
      return reviewsFlag.enabled !== false
    },
    reviewsDisabledMessage: (state) => {
      const reviewsFlag = state.flags?.reviews
      const message = (reviewsFlag?.message || '').trim()
      if (message) {
        return message
      }
      return REVIEWS_DISABLED_FALLBACK_MESSAGE
    },
  },
  actions: {
    async fetchPublicFlags(force = false) {
      if (this.loading || (this.loaded && !force)) {
        return
      }
      this.loading = true
      this.error = ''
      try {
        const response = await fetch(`${API_BASE_URL}/flags`, {
          headers: {
            Accept: 'application/json',
          },
          credentials: 'include',
        })
        if (!response.ok) {
          throw new Error(`Failed to fetch flags: ${response.status}`)
        }
        const payload = await response.json()
        const incomingFlags = payload?.flags || {}
        this.flags = {
          ...defaultFlagsState(),
          ...incomingFlags,
        }
        this.loaded = true
      } catch (error) {
        console.error('Error fetching feature flags', error)
        this.error = 'No se pudieron cargar los feature flags.'
      } finally {
        this.loading = false
      }
    },
    ensurePublicFlags() {
      if (this.loaded || this.loading) {
        return
      }
      return this.fetchPublicFlags()
    },
  },
})
