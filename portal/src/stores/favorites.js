import { defineStore } from 'pinia'
import API_BASE_URL from '@/constants/api'
import { resolveCsrfToken } from '@/utils/csrf'

const normalizeId = (value) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

export const useFavoritesStore = defineStore('favorites', {
  state: () => ({
    favoriteIds: new Set(),
    pendingIds: [],
  }),
  actions: {
    hydrateFromSites(sites = []) {
      if (!Array.isArray(sites) || !sites.length) {
        return
      }
      const current = new Set(this.favoriteIds)
      let changed = false
      sites.forEach((site) => {
        const id = normalizeId(site?.id)
        if (!id) return
        const flag = site?.is_favorite ?? site?.isFavorite
        if (flag === true && !current.has(id)) {
          current.add(id)
          changed = true
        }
        if (flag === false && current.has(id)) {
          current.delete(id)
          changed = true
        }
      })
      if (changed) {
        this.favoriteIds = current
      }
    },
    isFavorite(siteId) {
      const id = normalizeId(siteId)
      if (!id) return false
      return this.favoriteIds.has(id)
    },
    isPending(siteId) {
      const id = normalizeId(siteId)
      if (!id) return false
      return this.pendingIds.includes(id)
    },
    setPending(siteId, value) {
      const id = normalizeId(siteId)
      if (!id) return
      if (value) {
        if (!this.pendingIds.includes(id)) {
          this.pendingIds = [...this.pendingIds, id]
        }
      } else {
        this.pendingIds = this.pendingIds.filter((existing) => existing !== id)
      }
    },
    applyFavorite(siteId, shouldFavorite) {
      const id = normalizeId(siteId)
      if (!id) return
      if (shouldFavorite) {
        if (!this.favoriteIds.has(id)) {
          this.favoriteIds.add(id)
        }
      } else {
        if (this.favoriteIds.has(id)) {
          this.favoriteIds.delete(id)
        }
      }
    },
    async setFavorite(siteId, shouldFavorite) {
      const id = normalizeId(siteId)
      if (!id) {
        throw new Error('ID inválido')
      }
      if (this.isPending(id)) {
        return this.isFavorite(id)
      }
      this.setPending(id, true)
      try {
        const headers = {
          Accept: 'application/json',
        }
        const csrfToken = resolveCsrfToken()
        if (csrfToken) {
          headers['X-CSRF-TOKEN'] = csrfToken
          headers['X-CSRFToken'] = csrfToken
        }
        if (shouldFavorite) {
          headers['Content-Type'] = 'application/json'
        }
        const response = await fetch(`${API_BASE_URL}/sites/${id}/favorite`, {
          method: shouldFavorite ? 'PUT' : 'DELETE',
          credentials: 'include',
          headers,
          body: shouldFavorite ? JSON.stringify({}) : undefined,
        })
        if (response.status === 401) {
          throw new Error('unauthorized')
        }
        if (!response.ok && response.status !== 204) {
          throw new Error('favorite_failed')
        }
        this.applyFavorite(id, shouldFavorite)
        return shouldFavorite
      } finally {
        this.setPending(id, false)
      }
    },
    async toggleFavorite(siteId) {
      const shouldFavorite = !this.isFavorite(siteId)
      return this.setFavorite(siteId, shouldFavorite)
    },
    reset() {
      this.favoriteIds = new Set()
      this.pendingIds = []
    },
  },
})
