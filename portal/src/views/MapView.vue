<script setup>
import { ref } from 'vue'
import { LMap, LTileLayer } from '@vue-leaflet/vue-leaflet'
import 'leaflet/dist/leaflet.css'

const zoom = ref(4)
const center = ref([-34.6037, -58.3816])
</script>

<template>
  <section class="view-panel">
    <div class="view-panel__card">
      <p class="view-panel__subtitle">Mapa interactivo</p>
      <h1>Explorá los sitios de forma geográfica</h1>
      <p>
        Esta vista se alimentará de los mismos datos que se gestionan en el panel privado. Mientras
        integramos los endpoints definitivos, dejamos lista la estructura con Leaflet y la estética
        del portal público.
      </p>
    </div>

    <div class="view-panel__card map-card">
      <l-map v-model:zoom="zoom" :center="center">
        <l-tile-layer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          layer-type="base"
          name="OpenStreetMap"
        />
      </l-map>
    </div>
  </section>
</template>
