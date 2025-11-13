import { defineStore } from 'pinia'
import axios from 'axios'
import API_BASE_URL from '@/constants/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    loadingUser: false,
  }),
  getters: {
    isAuthenticated: (state) => state.user !== null,
  },
  actions: {
    async fetchCurrentUser() {
      this.loadingUser = true
      try {
        const response = await axios.get(`${API_BASE_URL}/me`, {
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
      const baseAuthUrl = API_BASE_URL.replace('/api', '')
      const target = `${baseAuthUrl}/api/auth/google/login?next=${encodeURIComponent(next)}`
      window.location.href = target
    },
    async logout() {
      try {
        await axios.post(
          `${API_BASE_URL}/auth/logout`,
          {},
          {
            withCredentials: true,
          },
        )
      } catch (error) {
        console.error('Error logging out', error)
      } finally {
        this.user = null
      }
    },
  },
})
