import { defineStore } from 'pinia'
import axios from 'axios'
import API_BASE_URL, { AUTH_BASE_URL } from '@/constants/api'
import { useFavoritesStore } from '@/stores/favorites'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    loadingUser: false,
    loginPromptVisible: false,
    loginPromptNextUrl: '/',
  }),
  getters: {
    isAuthenticated: (state) => state.user !== null,
  },
  actions: {
    async fetchCurrentUser() {
      this.loadingUser = true
      try {
        const response = await axios.get(`${API_BASE_URL}/auth/jwt/me`, {
          withCredentials: true,
        })
        this.user = response.data?.data || null
      } catch (error) {
        if (error.response && error.response.status === 401) {
          this.user = null
        } else {
          console.error('Error fetching current user', error)
        }
      } finally {
        this.loadingUser = false
      }
    },
    loginWithGoogle(nextPath) {
      const next = nextPath || window.location.pathname + window.location.search + window.location.hash
      const target = `${AUTH_BASE_URL}/api/auth/google/login?next=${encodeURIComponent(next)}`
      window.location.href = target
    },
    requestLoginPrompt(nextUrl) {
      this.loginPromptVisible = true
      this.loginPromptNextUrl = nextUrl || window.location.href || '/'
    },
    cancelLoginPrompt() {
      this.loginPromptVisible = false
      this.loginPromptNextUrl = '/'
    },
    confirmLoginPrompt() {
      const next = this.loginPromptNextUrl || '/'
      this.cancelLoginPrompt()
      this.loginWithGoogle(next)
    },
    async logout() {
      try {
        await axios.post(
          `${API_BASE_URL}/auth/jwt/logout`,
          {},
          {
            withCredentials: true,
          },
        )
      } catch (error) {
        console.error('Error logging out', error)
      } finally {
        this.user = null
        const favoritesStore = useFavoritesStore()
        favoritesStore.reset()
      }
    },
  },
})
