<script setup>
import { reactive, ref, onMounted } from 'vue'
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
  tags: '',
})

const submitting = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const validationErrors = ref({})

const mapElement = ref(null)
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
}

const resetMessages = () => {
  successMessage.value = ''
  errorMessage.value = ''
  validationErrors.value = {}
}

const normalizeTags = (raw) =>
  (raw || '')
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)

const handleSubmit = async () => {
  resetMessages()
  if (!form.lat || !form.long) {
    validationErrors.value = { general: ['Seleccioná la ubicación en el mapa.'] }
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
    tags: normalizeTags(form.tags),
  }

  submitting.value = true
  try {
    const response = await fetch(`${API_BASE_URL}/sites/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
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
      form.tags = ''
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
          <label class="form-grid__full">
            Etiquetas (separadas por coma)
            <input
              v-model="form.tags"
              type="text"
              placeholder="Ej. patrimonio,colonial,arquitectura"
            />
            <small>Usamos estas etiquetas para agrupar sitios similares.</small>
          </label>
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
