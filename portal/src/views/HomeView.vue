<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import FeaturedSection from '@/components/FeaturedSection.vue'
import HeroBanner from '@/components/HeroBanner.vue'

const router = useRouter()

const isAuthenticated = ref(false) // TODO: conectar con la sesión real cuando esté disponible.

const sectionsConfig = [
  {
    key: 'mostVisited',
    title: 'Más visitados',
    subtitle: 'Tendencias entre los usuarios.',
    ctaParams: { sort: 'visits' },
    emptyMessage: 'Todavía no registramos sitios populares aquí.',
    skeletonItems: 4,
  },
  {
    key: 'topRated',
    title: 'Mejor puntuados',
    subtitle: 'Los sitios con mejores valoraciones.',
    ctaParams: { sort: 'rating' },
    emptyMessage: 'Aún no hay calificaciones cargadas.',
    skeletonItems: 3,
  },
  {
    key: 'favorites',
    title: 'Favoritos',
    subtitle: 'Mi lista personal de favoritos.',
    ctaParams: { filter: 'favorites' },
    emptyMessage: 'Inicia sesión para comenzar a guardar tus favoritos.',
    requiresAuth: true,
  },
  {
    key: 'recent',
    title: 'Recientemente agregados',
    subtitle: 'Nuevos sitios que acaban de sumarse al portal.',
    ctaParams: { sort: 'recent' },
    emptyMessage: 'Pronto verás novedades aquí.',
    skeletonItems: 3,
  },
]

const sectionsState = reactive(
  sectionsConfig.reduce((acc, config) => {
    acc[config.key] = {
      items: [],
      loading: !config.requiresAuth,
    }
    return acc
  }, {}),
)

const visibleSections = computed(() =>
  sectionsConfig.filter((section) => !section.requiresAuth || isAuthenticated.value),
)

const heroCopy = {
  eyebrow: 'Portal de sitios históricos',
  title: 'Descubrí sitios históricos',
  description:
    'Explora nuestro catálogo de sitios históricos.',
  hint: 'Tip: se puede buscar por ciudad, provincia o palabra clave.',
}

const buildCtaTo = (params = {}) => ({
  name: 'sites',
  query: params,
})

const mockDataBySection = {
  mostVisited: [
    {
      id: 'museo-arte-moderno',
      name: 'Museo de Arte Moderno',
      city: 'CABA',
      province: 'Buenos Aires',
      rating: 4.9,
      badge: 'Destacado',
      category: 'Museo',
      updatedAt: 'hace 2 días',
      image:
        'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=800&q=60',
      href: { name: 'site-detail', params: { id: 'museo-arte-moderno' } },
    },
    {
      id: 'delta-tigre',
      name: 'Delta del Tigre',
      city: 'Tigre',
      province: 'Buenos Aires',
      rating: 4.7,
      category: 'Reservas Naturales',
      updatedAt: 'hace 5 días',
      image:
        'https://images.unsplash.com/photo-1470246973918-29a93221c455?auto=format&fit=crop&w=800&q=60',
      href: { name: 'site-detail', params: { id: 'delta-tigre' } },
    },
    {
      id: 'cataratas-iguazu',
      name: 'Parque Nacional Iguazú',
      city: 'Puerto Iguazú',
      province: 'Misiones',
      rating: 4.8,
      category: 'Parques',
      updatedAt: 'hace 1 semana',
      image:
        'https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=800&q=60',
      href: { name: 'site-detail', params: { id: 'cataratas-iguazu' } },
    },
  ],
  topRated: [
    {
      id: 'observatorio-cordoba',
      name: 'Observatorio Astronómico',
      city: 'Córdoba',
      province: 'Córdoba',
      rating: 5,
      badge: 'Mejor Valoración',
      category: 'Centro Científico',
      updatedAt: 'hace 12 h',
      image:
        'https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=800&q=60',
      href: { name: 'site-detail', params: { id: 'observatorio-cordoba' } },
    },
    {
      id: 'teatro-san-martin',
      name: 'Teatro San Martín',
      city: 'CABA',
      province: 'Buenos Aires',
      rating: 4.9,
      category: 'Teatro',
      updatedAt: 'hace 3 días',
      image:
        'https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=800&q=60',
      href: { name: 'site-detail', params: { id: 'teatro-san-martin' } },
    },
    {
      id: 'casa-historica-tucuman',
      name: 'Casa Histórica de Tucumán',
      city: 'San Miguel de Tucumán',
      province: 'Tucumán',
      rating: 4.8,
      category: 'Historia',
      updatedAt: 'hace 4 días',
      image:
        'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=800&q=60',
      href: { name: 'site-detail', params: { id: 'casa-historica-tucuman' } },
    },
  ],
  favorites: [
    {
      id: 'anfiteatro-rosario',
      name: 'Anfiteatro Municipal',
      city: 'Rosario',
      province: 'Santa Fe',
      rating: 4.6,
      category: 'Eventos',
      updatedAt: 'hace 8 h',
      image:
        'https://images.unsplash.com/photo-1489515217757-5fd1be406fef?auto=format&fit=crop&w=800&q=60',
      href: { name: 'site-detail', params: { id: 'anfiteatro-rosario' } },
    },
    {
      id: 'atelier-salta',
      name: 'Atelier Salta',
      city: 'Salta',
      province: 'Salta',
      rating: 4.7,
      category: 'Galería de arte',
      updatedAt: 'ayer',
      image:
        'https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=800&q=60',
      href: { name: 'site-detail', params: { id: 'atelier-salta' } },
    },
  ],
  recent: [
    {
      id: 'sendero-norte',
      name: 'Sendero Norte',
      city: 'San Martín de los Andes',
      province: 'Neuquén',
      rating: 4.5,
      badge: 'Nuevo',
      category: 'Naturaleza',
      updatedAt: 'esta semana',
      image:
        'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=800&q=60',
      href: { name: 'site-detail', params: { id: 'sendero-norte' } },
    },
    {
      id: 'mercado-del-puerto',
      name: 'Mercado del Puerto',
      city: 'Bahía Blanca',
      province: 'Buenos Aires',
      rating: 4.4,
      category: 'Gastronomía',
      updatedAt: 'hace 2 días',
      image:
        'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=800&q=60',
      href: { name: 'site-detail', params: { id: 'mercado-del-puerto' } },
    },
    {
      id: 'centro-interpretacion-chaco',
      name: 'Centro de Interpretación del Chaco',
      city: 'Resistencia',
      province: 'Chaco',
      rating: 4.3,
      category: 'Centros culturales',
      updatedAt: 'hoy',
      image:
        'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=800&q=60',
      href: { name: 'site-detail', params: { id: 'centro-interpretacion-chaco' } },
    },
  ],
}

const loadSection = async (sectionKey) => {
  const state = sectionsState[sectionKey]
  if (!state) return

  state.loading = true

  await new Promise((resolve) => {
    const latency = 300 + Math.random() * 600
    setTimeout(resolve, latency)
  })

  state.items = mockDataBySection[sectionKey] || []
  state.loading = false
}

const bootstrapSections = () => {
  visibleSections.value.forEach((section) => {
    loadSection(section.key)
  })
}

const handleHeroSearch = (term) => {
  router.push({
    name: 'sites',
    query: term ? { search: term } : {},
  })
}

onMounted(() => {
  bootstrapSections()
})

watch(
  () => isAuthenticated.value,
  (loggedIn) => {
    if (loggedIn) {
      loadSection('favorites')
    }
  },
)
</script>

<template>
  <section class="home">
    <HeroBanner
      :eyebrow="heroCopy.eyebrow"
      :title="heroCopy.title"
      :description="heroCopy.description"
      :hint="heroCopy.hint"
      cta-label="Buscar"
      @search="handleHeroSearch"
    />

    <div class="home__sections">
      <FeaturedSection
        v-for="section in visibleSections"
        :key="section.key"
        :title="section.title"
        :subtitle="section.subtitle"
        :items="sectionsState[section.key]?.items"
        :loading="sectionsState[section.key]?.loading"
        :cta-label="section.ctaLabel || 'Ver todos'"
        :cta-to="buildCtaTo(section.ctaParams)"
        :empty-message="section.emptyMessage"
        :skeleton-items="section.skeletonItems || 3"
      />
    </div>
  </section>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
  padding: 1.5rem 0 3rem;
}

.home__sections {
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
}
</style>
