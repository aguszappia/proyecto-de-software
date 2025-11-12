<template>
  <section class="about-view view-panel">
    <header class="about-hero view-panel__card">
      <p class="view-panel__subtitle">Proyecto Integrador 2025</p>
      <h1>Sitios Históricos · Grupo 28</h1>
      <p class="about-hero__lead">
        Portal público para explorar, proponer y seguir el patrimonio cultural del país. Abrimos la
        experiencia al público general con una interfaz moderna que conecta a los usuarios con los
        sitios históricos de manera simple.
      </p>
      <ul class="about-hero__meta">
        <li>Portal público</li>
        <li>Etapa 2</li>
        <li> Vue 3 + API</li>
      </ul>
    </header>

    <article class="about-card about-card--intro view-panel__card">
      <h2>¿De qué se trata?</h2>
      <p>
        Este portal forma parte del <strong>Trabajo Integrador 2025</strong> de la cátedra
        <em>Proyecto de Software</em>. Implementamos un portal público con
        <strong>Vue 3</strong> para que el público pueda
        visualizar sitios históricos destacados, acceder a reseñas y mapas interactivos desde cualquier
        dispositivo. Trabajamos con <strong>PostgreSQL</strong> (soporte geoespacial) y una API
        que integra ambos frentes dentro del directorio <code>web</code> del proyecto.
      </p>
    </article>

    <div class="about-grid">
      <article class="about-card view-panel__card">
        <h2>Home con secciones destacadas</h2>
        <p>
          Hero con buscador rápido y carruseles de sitios mejor puntuados, favoritos, recientes y
          más visitados, cada uno con tarjetas que conducen al detalle o al listado filtrado.
        </p>
      </article>

      <article class="about-card view-panel__card">
        <h2>Listado y búsqueda</h2>
        <p>
          Listado mobile first con búsqueda por texto, filtros combinables, órdenes configurables y
          mapa interactivo para explorar sitios por ubicación.
        </p>
      </article>

      <article class="about-card view-panel__card">
        <h2>Detalle, reseñas y mapa</h2>
        <p>
          Página de detalle con galería accesible, chips de estado y tags, mapa con marcador, bloque
          de reseñas con calificación promedio y llamado a escribir reseña.
        </p>
      </article>

      <article class="about-card view-panel__card">
        <h2>Autenticación y perfil</h2>
        <p>
          Login con Google para habilitar favoritos y reseñas, indicador de sesión en el header y
          perfil con pestañas de “Mis reseñas” y “Sitios favoritos”.
        </p>
      </article>
    </div>

    <footer class="about-footer view-panel__card">
      <div>
        <p class="section-kicker">Grupo Nº 28 — Etapa 2</p>
        <p class="about-footer__note">
          Aplicación pública desarrollada con Vue 3 conectada a la API Python + Flask.
        </p>
      </div>
      <div class="about-footer__logos" aria-label="Tecnologías utilizadas">
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/3/3c/Flask_logo.svg"
          alt="Logo de Flask"
          loading="lazy"
          width="120"
          height="48"
        />
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg"
          alt="Logo de Python"
          loading="lazy"
          width="110"
          height="48"
        />
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/9/95/Vue.js_Logo_2.svg"
          alt="Logo de Vue"
          loading="lazy"
          width="110"
          height="48"
        />
      </div>
    </footer>
  </section>
</template>
