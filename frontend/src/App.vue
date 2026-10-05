<script setup>
import {RouterLink,RouterView} from 'vue-router'
</script>
<template>
<div class="app">
<header>
  <RouterLink class="brand" to="/"><b>1</b> OneToFour</RouterLink>
  <nav><RouterLink to="/">Inicio</RouterLink><RouterLink to="/jugar">Jugar</RouterLink><RouterLink to="/ranking">Ranking</RouterLink><RouterLink to="/estadisticas">Estadísticas</RouterLink><RouterLink to="/perfil">Mi progreso</RouterLink><RouterLink to="/agente">Agente IA</RouterLink></nav>
</header>
<main><RouterView/></main>
<footer><span>OneToFour</span><span> © 2026 Creada por 
          <a
            href="https://www.linkedin.com/in/javier-garzon-garcia/"
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold hover:text-secondary transition-colors"
          >
            Javier Garzón
          </a>. Todos los derechos reservados.</span></footer>
</div>
</template>
