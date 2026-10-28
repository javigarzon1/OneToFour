// Cliente de la API. En producción usa rutas relativas (mismo dominio);
// en local VITE_API_URL apunta al backend (ver .env.example).
const API_URL = (import.meta.env?.VITE_API_URL ?? '').replace(/\/$/, '')

const GENERIC_ERROR = 'Error en la API.'

function messageFrom(body) {
  const detail = body?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) return 'Los datos enviados no son válidos.'
  return GENERIC_ERROR
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(API_URL + path, options)
  } catch {
    throw new ApiError(
      `No se puede conectar con el backend (${API_URL || 'mismo dominio'}). Comprueba que la API está disponible.`,
      0,
    )
  }

  if (!response.ok) {
    let message = GENERIC_ERROR
    try {
      message = messageFrom(await response.json())
    } catch {
      // La respuesta de error no era JSON: se usa el mensaje genérico.
    }
    throw new ApiError(message, response.status)
  }
  return response.json()
}

function post(path, data) {
  const options = { method: 'POST' }
  if (data !== undefined) {
    options.headers = { 'Content-Type': 'application/json' }
    options.body = JSON.stringify(data)
  }
  return request(path, options)
}

// --- Partidas (el servidor guarda las preguntas y calcula la puntuación) ---
export const startGame = (data) => post('/api/games/start', data)
export const getGame = (id) => request(`/api/games/${encodeURIComponent(id)}`)
export const answerGame = (id, indice, respuesta) =>
  post(`/api/games/${encodeURIComponent(id)}/answer`, { indice, respuesta })
export const finishGame = (id) => post(`/api/games/${encodeURIComponent(id)}/finish`)

// --- Agente IA ---
export const getAgentOptions = () => request('/api/agent/options')
export const generateQuiz = (data) => post('/api/agent/generate', data)

// --- Ranking, estadísticas y perfil ---
export const getRanking = () => request('/api/ranking')
export const getStats = () => request('/api/stats')
export const getPlayerProfile = (jugador) => {
  const nombre = String(jugador || getPlayer()).trim()
  return request('/api/player/' + encodeURIComponent(nombre) + '/profile')
}

// --- Nombre del jugador (guardado sólo en este navegador) ---
const PLAYER_KEY = 'onetoFour_player'

export function getPlayer() {
  try {
    return localStorage.getItem(PLAYER_KEY) || 'Jugador'
  } catch {
    return 'Jugador'
  }
}

export function setPlayer(nombre) {
  try {
    localStorage.setItem(PLAYER_KEY, String(nombre || 'Jugador').trim() || 'Jugador')
  } catch {
    // Sin almacenamiento (modo privado): se sigue usando el nombre en memoria.
  }
}
