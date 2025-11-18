import { reactive } from 'vue'
import API_BASE_URL from '@/constants/api'

const MAINTENANCE_FALLBACK_MESSAGE =
  'Estamos realizando tareas de mantenimiento. Volvé a intentarlo en unos minutos.'

const maintenanceState = reactive({
  pending: true,
  enabled: false,
  message: '',
})

let inflightPromise = null

const applyMaintenanceState = (enabled, message) => {
  maintenanceState.enabled = enabled
  maintenanceState.message = enabled ? message || MAINTENANCE_FALLBACK_MESSAGE : ''
}

const fetchMaintenanceStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/status`, {
      headers: {
        Accept: 'application/json',
      },
    })
    if (!response.ok) {
      throw new Error('Failed to fetch maintenance status')
    }
    const payload = await response.json()
    const portalState = payload?.maintenance?.portal || {}
    applyMaintenanceState(Boolean(portalState.enabled), portalState.message)
  } catch (error) {
    console.error('Error fetching maintenance status', error)
    if (maintenanceState.pending) {
      applyMaintenanceState(false, '')
    }
  } finally {
    maintenanceState.pending = false
  }
  return maintenanceState
}

export const useMaintenanceState = () => maintenanceState

export const refreshMaintenanceStatus = async () => {
  if (inflightPromise) {
    return inflightPromise
  }
  inflightPromise = fetchMaintenanceStatus()
  try {
    await inflightPromise
  } finally {
    inflightPromise = null
  }
  return maintenanceState
}
