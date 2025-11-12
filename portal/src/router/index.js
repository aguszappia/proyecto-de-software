import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import MapView from '../views/MapView.vue'
import SiteDetailView from '../views/SiteDetailView.vue'
import SiteListView from '../views/SiteListView.vue'
import SiteCreateView from '../views/SiteCreateView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    return {
      top: 0,
      left: 0,
      behavior: 'smooth',
    }
  },
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/map/',
      name: 'map',
      component: MapView,
    },
    {
      path: '/sitios',
      name: 'sites',
      component: SiteListView,
    },
    {
      path: '/sitios/nuevo',
      name: 'site-create',
      component: SiteCreateView,
    },
    {
      path: '/sitios/:id',
      name: 'site-detail',
      component: SiteDetailView,
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/AboutView.vue'),
    },
  ],
})

export default router
