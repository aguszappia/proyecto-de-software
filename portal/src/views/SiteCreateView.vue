<script setup>
import { reactive, ref, onMounted, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import API_BASE_URL from '@/constants/api'

const defaultCoords = { lat: -34.6037, long: -58.3816 }

const provinces = [
  'Buenos Aires',
  'Catamarca',
  'Chaco',
  'Chubut',
  'Córdoba',
  'Corrientes',
  'Entre Ríos',
  'Formosa',
  'Jujuy',
  'La Pampa',
  'La Rioja',
  'Mendoza',
  'Misiones',
  'Neuquén',
  'Río Negro',
  'Salta',
  'San Juan',
  'San Luis',
  'Santa Cruz',
  'Santa Fe',
  'Santiago del Estero',
  'Tierra del Fuego',
  'Tucumán',
]

const conservationStatuses = [
  { label: 'Excelente / Bueno', value: 'Bueno' },
  { label: 'Regular', value: 'Regular' },
  { label: 'Malo', value: 'Malo' },
]

const categories = [
  { label: 'Arquitectura', value: 'Arquitectura' },
  { label: 'Infraestructura', value: 'Infraestructura' },
  { label: 'Sitio arqueológico', value: 'Sitio arqueológico' },
  { label: 'Otro', value: 'Otro' },
]

const MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

const form = reactive({
  name: '',
  short_description: '',
  description: '',
  city: '',
  province: '',
  country: 'AR',
  state_of_conservation: '',
  category: '',
  inaguration_year: '',
  lat: '',
  long: '',
  tags: [],
})

const coverImageInputId = 'site-cover-image'
const submitting = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const validationErrors = ref({})
const coverImageFile = ref(null)
const coverImagePreview = ref('')
const coverImageError = ref('')

const mapElement = ref(null)
const availableTags = ref([])
const tagsDropdownOpen = ref(false)
const tagsDropdownRef = ref(null)
const coverImageInput = ref(null)
let mapInstance = null
let markerInstance = null

const ensureMarker = (lat, lng) => {
  if (!mapInstance) {
    return
  }
  const point = [lat, lng]
  if (!markerInstance) {
    markerInstance = L.marker(point).addTo(mapInstance)
  } else {
    markerInstance.setLatLng(point)
  }
}

const fetchAvailableTags = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/tags`)
    if (!response.ok) {
      throw new Error('Failed to fetch tags')
    }
    const payload = await response.json()
    const mapped = Array.isArray(payload?.data) ? payload.data : []
    availableTags.value = mapped
      .map((tag) => (typeof tag?.name === 'string' ? tag.name.trim() : ''))
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b))
  } catch (error) {
    availableTags.value = []
  }
}

const toggleTag = (tag) => {
  if (!tag) return
  const current = new Set(form.tags)
  if (current.has(tag)) {
    current.delete(tag)
  } else {
    current.add(tag)
  }
  form.tags = Array.from(current)
}

const toggleTagDropdown = () => {
  if (!availableTags.value.length) {
    return
  }
  tagsDropdownOpen.value = !tagsDropdownOpen.value
}

const closeTagDropdown = () => {
  tagsDropdownOpen.value = false
}

const handleClickOutside = (event) => {
  if (!tagsDropdownRef.value) return
  if (!tagsDropdownRef.value.contains(event.target)) {
    closeTagDropdown()
  }
}

const revokeImagePreview = () => {
  if (coverImagePreview.value) {
    URL.revokeObjectURL(coverImagePreview.value)
    coverImagePreview.value = ''
  }
}

const clearImageSelection = ({ preserveError = false } = {}) => {
  coverImageFile.value = null
  if (!preserveError) {
    coverImageError.value = ''
  }
  revokeImagePreview()
  if (coverImageInput.value) {
    coverImageInput.value.value = ''
  }
}

const handleImageChange = (event) => {
  coverImageError.value = ''
  const [file] = event.target?.files || []
  if (!file) {
    clearImageSelection()
    return
  }
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    coverImageError.value = 'El archivo debe ser JPG, PNG o WEBP.'
    clearImageSelection({ preserveError: true })
    return
  }
  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    coverImageError.value = 'La imagen no puede superar los 5 MB.'
    clearImageSelection({ preserveError: true })
    return
  }
  coverImageFile.value = file
  revokeImagePreview()
  coverImagePreview.value = URL.createObjectURL(file)
}

onMounted(() => {
  if (!mapElement.value) {
    return
  }
  mapInstance = L.map(mapElement.value).setView([defaultCoords.lat, defaultCoords.long], 5)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(mapInstance)

  mapInstance.on('click', (event) => {
    const { lat, lng } = event.latlng
    form.lat = lat.toFixed(6)
    form.long = lng.toFixed(6)
    ensureMarker(lat, lng)
  })

  document.addEventListener('click', handleClickOutside)
  fetchAvailableTags()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  clearImageSelection()
})

const fieldLabels = {
  name: 'Nombre',
  short_description: 'Descripción breve',
  description: 'Descripción completa',
  city: 'Ciudad',
  province: 'Provincia',
  state_of_conservation: 'Estado de conservación',
  category: 'Categoría',
  inaguration_year: 'Año de inauguración',
  lat: 'Latitud',
  long: 'Longitud',
  tags: 'Etiquetas',
  cover_image: 'Imagen representativa',
}

const resetMessages = () => {
  successMessage.value = ''
  errorMessage.value = ''
  validationErrors.value = {}
}

const handleSubmit = async () => {
  resetMessages()
  if (!form.lat || !form.long) {
    validationErrors.value = { general: ['Seleccioná la ubicación en el mapa.'] }
    return
  }
  if (!coverImageFile.value) {
    validationErrors.value = { cover_image: ['Subí al menos una imagen del sitio.'] }
    return
  }

  const payload = {
    name: form.name,
    short_description: form.short_description,
    description: form.description,
    city: form.city,
    province: form.province,
    country: form.country || 'AR',
    lat: parseFloat(form.lat),
    long: parseFloat(form.long),
    state_of_conservation: form.state_of_conservation,
    category: form.category,
    inaguration_year: form.inaguration_year ? Number(form.inaguration_year) : null,
    tags: form.tags,
  }

  submitting.value = true
  try {
    const formData = new FormData()
    Object.entries(payload).forEach(([key, value]) => {
      if (key === 'tags') {
        return
      }
      if (value === null || value === undefined || value === '') {
        return
      }
      formData.append(key, value)
    })
    payload.tags.forEach((tag) => formData.append('tags[]', tag))
    formData.append('cover_image', coverImageFile.value)

    const response = await fetch(`${API_BASE_URL}/sites/`, {
      method: 'POST',
      body: formData,
    })

    if (response.status === 201) {
      successMessage.value = '¡Gracias! Revisaremos tu propuesta antes de publicarla.'
      validationErrors.value = {}
      const created = await response.json()
      form.name = ''
      form.short_description = ''
      form.description = ''
      form.city = ''
      form.province = ''
      form.state_of_conservation = ''
      form.category = ''
      form.inaguration_year = ''
      form.lat = ''
      form.long = ''
      form.tags = []
      clearImageSelection()
      if (markerInstance && mapInstance) {
        mapInstance.removeLayer(markerInstance)
        markerInstance = null
      }
      return created
    }

    let payloadError = {}
    try {
      payloadError = await response.json()
    } catch (err) {
      // ignore parse errors
    }
    if (payloadError?.error?.details) {
      validationErrors.value = payloadError.error.details
    }
    errorMessage.value =
      payloadError?.error?.message || `No se pudo enviar la propuesta (error ${response.status}).`
  } catch (err) {
    errorMessage.value = 'No se pudo conectar con el servidor. Intentá más tarde.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="view-panel">
    <div class="view-panel__card">
      <p class="view-panel__subtitle">Participá</p>
      <h1>Proponer un nuevo sitio histórico</h1>
      <p>
        Este formulario es el mismo que utilizamos internamente para cargar sitios. Cada dato nos
        ayuda a validar la postulación y a mostrarla correctamente en el portal.
      </p>
    </div>

    <div class="view-panel__card create-form">
      <div v-if="successMessage" class="alert alert--success">
        {{ successMessage }}
      </div>
      <div v-if="errorMessage" class="alert alert--error">
        {{ errorMessage }}
      </div>
      <div v-if="Object.keys(validationErrors).length" class="alert alert--warning">
        <p>Revisá los siguientes campos:</p>
        <ul>
          <li v-for="(messages, field) in validationErrors" :key="field">
            <strong>{{ fieldLabels[field] || field }}:</strong>
            {{ Array.isArray(messages) ? messages.join(', ') : messages }}
          </li>
        </ul>
      </div>

      <form class="site-form" @submit.prevent="handleSubmit">
        <div class="form-grid">
          <label>
            Nombre del sitio
            <input v-model="form.name" type="text" required placeholder="Ej. Cabildo de Buenos Aires" />
          </label>
          <label>
            Descripción breve
            <input
              v-model="form.short_description"
              type="text"
              required
              placeholder="Resumen corto para las tarjetas"
            />
          </label>
          <label class="form-grid__full">
            Descripción completa
            <textarea
              v-model="form.description"
              rows="4"
              required
              placeholder="Contanos la historia y relevancia del sitio"
            ></textarea>
          </label>
          <label>
            Ciudad
            <input v-model="form.city" type="text" required placeholder="Ej. La Plata" />
          </label>
          <label>
            Provincia
            <select v-model="form.province" required>
              <option value="">Seleccioná una provincia</option>
              <option v-for="province in provinces" :key="province" :value="province">
                {{ province }}
              </option>
            </select>
          </label>
          <label>
            Estado de conservación
            <select v-model="form.state_of_conservation" required>
              <option value="">Seleccioná una opción</option>
              <option v-for="option in conservationStatuses" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
          <label>
            Categoría
            <select v-model="form.category" required>
              <option value="">Seleccioná una categoría</option>
              <option v-for="option in categories" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
          <label>
            Año de inauguración
            <input
              v-model="form.inaguration_year"
              type="number"
              min="0"
              required
              placeholder="Ej. 1890"
            />
          </label>
          <div class="form-grid__full filter-group filter-group--tags create-form__tags">
            <span>Etiquetas</span>
            <div class="tag-dropdown" ref="tagsDropdownRef">
              <button
                type="button"
                class="tag-dropdown__toggle"
                :disabled="!availableTags.length"
                @click.stop="toggleTagDropdown"
              >
                <span v-if="form.tags.length">
                  {{ form.tags.length }} seleccionada{{ form.tags.length === 1 ? '' : 's' }}
                </span>
                <span v-else>
                  {{ availableTags.length ? 'Seleccionar etiquetas' : 'No hay etiquetas disponibles' }}
                </span>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M6 9l6 6 6-6"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </button>
              <div v-if="tagsDropdownOpen" class="tag-dropdown__panel">
                <label
                  v-for="tag in availableTags"
                  :key="tag"
                  class="tag-dropdown__option"
                >
                  <input
                    type="checkbox"
                    :value="tag"
                    :checked="form.tags.includes(tag)"
                    @change="toggleTag(tag)"
                  />
                  <span>{{ tag }}</span>
                </label>
                <p v-if="!availableTags.length" class="tag-placeholder">
                  Cargaremos etiquetas cuando haya sitios disponibles.
                </p>
                <button
                  type="button"
                  class="secondary-button tag-dropdown__close"
                  @click="closeTagDropdown"
                >
                  Listo
                </button>
              </div>
            </div>
            <div v-if="form.tags.length" class="tag-selected-summary">
              <span v-for="tag in form.tags" :key="tag" class="tag-pill">
                {{ tag }}
                <button type="button" @click="toggleTag(tag)" aria-label="Quitar tag">
                  ×
                </button>
              </span>
            </div>
            <small>Usamos estas etiquetas para agrupar sitios similares.</small>
          </div>
        </div>

        <div class="media-panel">
          <div>
            <p class="media-panel__kicker">Imagen representativa</p>
            <h2>Subí una foto del sitio</h2>
            <p>La usamos como portada mientras revisamos tu propuesta.</p>
          </div>
          <div class="media-panel__body">
            <input
              :id="coverImageInputId"
              ref="coverImageInput"
              class="media-panel__input"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              @change="handleImageChange"
            />
            <label class="media-upload" :for="coverImageInputId">
              <span>Seleccionar imagen</span>
            </label>
            <div v-if="coverImagePreview" class="media-preview">
              <img :src="coverImagePreview" alt="Previsualización de la imagen seleccionada" />
              <button type="button" class="secondary-button" @click="clearImageSelection">
                Quitar imagen
              </button>
            </div>
            <p class="media-hint">Formatos admitidos: JPG, PNG o WEBP. Tamaño máximo 5 MB.</p>
            <p v-if="coverImageError" class="media-error">{{ coverImageError }}</p>
          </div>
        </div>

        <div class="map-panel">
          <div class="map-panel__header">
            <div>
              <p class="map-panel__kicker">Ubicación geográfica</p>
              <h2>Marcá el punto en el mapa</h2>
              <p>Hacé clic en el mapa para completar automáticamente las coordenadas.</p>
            </div>
            <div class="map-panel__coords">
              <label>
                Latitud
                <input v-model="form.lat" type="text" readonly placeholder="-34.603700" />
              </label>
              <label>
                Longitud
                <input v-model="form.long" type="text" readonly placeholder="-58.381600" />
              </label>
            </div>
          </div>
          <div ref="mapElement" class="map-panel__map" aria-live="polite"></div>
        </div>

        <div class="form-actions">
          <button class="primary-button" type="submit" :disabled="submitting">
            {{ submitting ? 'Enviando...' : 'Enviar propuesta' }}
          </button>
          <p class="form-actions__note">
            Las propuestas se revisan manualmente antes de publicarse en el portal público.
          </p>
        </div>
      </form>
    </div>
  </section>
</template>
