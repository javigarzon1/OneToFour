<script setup>
import {ref} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import {login,register} from '../services/api'
const route=useRoute(),router=useRouter()
const mode=ref(route.query.mode==='register'?'register':'login')
const usuario=ref(''),password=ref(''),confirm=ref(''),loading=ref(false),error=ref('')
async function submit(){
  error.value=''
  if(mode.value==='register' && password.value!==confirm.value){error.value='Las contraseñas no coinciden.';return}
  loading.value=true
  try{
    const fn=mode.value==='register'?register:login
    await fn({usuario:usuario.value.trim(),password:password.value})
    router.push(String(route.query.redirect||'/'))
  }catch(e){error.value=e.message}finally{loading.value=false}
}
</script>
<template><section class="auth page"><div class="auth-card card"><small>ONETOFOUR AUTH 1.0</small><h1>{{mode==='login'?'Bienvenido de nuevo':'Crea tu cuenta'}}</h1><p>{{mode==='login'?'Inicia sesión para guardar tus partidas y progreso.':'Regístrate para que tu progreso quede vinculado a tu cuenta.'}}</p><div class="auth-tabs"><button :class="{active:mode==='login'}" @click="mode='login'">Entrar</button><button :class="{active:mode==='register'}" @click="mode='register'">Registrarme</button></div><form @submit.prevent="submit"><label>Usuario<input v-model="usuario" minlength="3" maxlength="30" autocomplete="username" required placeholder="ej. javi"></label><label>Contraseña<input v-model="password" type="password" minlength="8" maxlength="128" :autocomplete="mode==='login'?'current-password':'new-password'" required placeholder="Mínimo 8 caracteres"></label><label v-if="mode==='register'">Repite la contraseña<input v-model="confirm" type="password" minlength="8" maxlength="128" autocomplete="new-password" required></label><div v-if="error" class="agent-error">{{error}}</div><button class="primary" :disabled="loading">{{loading?'Procesando...':mode==='login'?'Iniciar sesión':'Crear cuenta'}} <span>→</span></button></form></div></section></template>
