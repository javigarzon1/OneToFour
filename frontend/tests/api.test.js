import assert from 'node:assert/strict'
import { afterEach, beforeEach, describe, test } from 'node:test'

import * as api from '../src/services/api.js'

let calls
const realFetch = globalThis.fetch

function mockFetch(handler) {
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options })
    return handler(url, options)
  }
}

const json = (body, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
})

beforeEach(() => {
  calls = []
})

afterEach(() => {
  globalThis.fetch = realFetch
  delete globalThis.localStorage
})

describe('partidas', () => {
  test('startGame envía los filtros como JSON', async () => {
    mockFetch(() => json({ partida_id: 'abc' }))
    const result = await api.startGame({ jugador: 'Javi', categoria: 'Historia' })

    assert.equal(result.partida_id, 'abc')
    assert.equal(calls[0].url, '/api/games/start')
    assert.equal(calls[0].options.method, 'POST')
    assert.equal(calls[0].options.headers['Content-Type'], 'application/json')
    assert.deepEqual(JSON.parse(calls[0].options.body), { jugador: 'Javi', categoria: 'Historia' })
  })

  test('answerGame envía el índice y la letra elegida', async () => {
    mockFetch(() => json({ acierto: true }))
    await api.answerGame('id-1', 3, 'B')

    assert.equal(calls[0].url, '/api/games/id-1/answer')
    assert.deepEqual(JSON.parse(calls[0].options.body), { indice: 3, respuesta: 'B' })
  })

  test('answerGame permite respuesta vacía (tiempo agotado)', async () => {
    mockFetch(() => json({ acierto: false }))
    await api.answerGame('id-1', 0, '')

    assert.deepEqual(JSON.parse(calls[0].options.body), { indice: 0, respuesta: '' })
  })

  test('finishGame no envía puntuación: la calcula el servidor', async () => {
    mockFetch(() => json({ puntuacion: 7 }))
    await api.finishGame('id-1')

    assert.equal(calls[0].url, '/api/games/id-1/finish')
    assert.equal(calls[0].options.method, 'POST')
    assert.equal(calls[0].options.body, undefined)
  })

  test('getGame codifica el identificador', async () => {
    mockFetch(() => json({}))
    await api.getGame('a/b')

    assert.equal(calls[0].url, '/api/games/a%2Fb')
  })

  test('el cliente ya no puede enviar su propia puntuación', () => {
    assert.equal(api.saveGame, undefined)
    assert.equal(api.getQuestions, undefined)
  })
})

describe('agente, ranking y perfil', () => {
  test('generateQuiz hace POST con el cuerpo indicado', async () => {
    mockFetch(() => json({ partida_id: 'x', preguntas: [] }))
    await api.generateQuiz({ tema: 'Cine', dificultad: 'Fácil', jugador: 'Javi' })

    assert.equal(calls[0].url, '/api/agent/generate')
    assert.equal(JSON.parse(calls[0].options.body).tema, 'Cine')
  })

  test('getRanking y getStats hacen GET', async () => {
    mockFetch(() => json([]))
    await api.getRanking()
    await api.getStats()

    assert.deepEqual(calls.map((c) => c.url), ['/api/ranking', '/api/stats'])
    assert.equal(calls[0].options.method, undefined)
  })

  test('getPlayerProfile codifica el nombre', async () => {
    mockFetch(() => json({}))
    await api.getPlayerProfile('Ana María / 2')

    assert.equal(calls[0].url, '/api/player/Ana%20Mar%C3%ADa%20%2F%202/profile')
  })
})

describe('errores', () => {
  test('usa el mensaje "detail" de la API', async () => {
    mockFetch(() => json({ detail: 'No se pudo consultar el ranking.' }, 503))

    await assert.rejects(api.getRanking(), (error) => {
      assert.ok(error instanceof api.ApiError)
      assert.equal(error.message, 'No se pudo consultar el ranking.')
      assert.equal(error.status, 503)
      return true
    })
  })

  test('los errores de validación (detail como lista) dan un mensaje legible', async () => {
    mockFetch(() => json({ detail: [{ loc: ['body', 'respuesta'], msg: 'x' }] }, 422))

    await assert.rejects(api.startGame({}), { message: 'Los datos enviados no son válidos.' })
  })

  test('un detail que no es texto no se muestra como [object Object]', async () => {
    mockFetch(() => json({ detail: { status: 'error' } }, 503))

    await assert.rejects(api.getStats(), { message: 'Error en la API.' })
  })

  test('respuesta de error que no es JSON', async () => {
    mockFetch(() => ({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError('no es JSON')
      },
    }))

    await assert.rejects(api.getRanking(), { message: 'Error en la API.', status: 502 })
  })

  test('sin conexión con el backend', async () => {
    mockFetch(() => {
      throw new TypeError('fetch failed')
    })

    await assert.rejects(api.getRanking(), (error) => {
      assert.match(error.message, /No se puede conectar con el backend/)
      assert.equal(error.status, 0)
      return true
    })
  })

  test('un 429 conserva el mensaje del límite de uso', async () => {
    mockFetch(() => json({ detail: 'Has generado muchas partidas seguidas.' }, 429))

    await assert.rejects(api.generateQuiz({}), (error) => {
      assert.equal(error.status, 429)
      assert.match(error.message, /muchas partidas/)
      return true
    })
  })
})

describe('nombre del jugador', () => {
  function fakeStorage(initial = {}) {
    const data = { ...initial }
    globalThis.localStorage = {
      getItem: (key) => (key in data ? data[key] : null),
      setItem: (key, value) => {
        data[key] = value
      },
    }
    return data
  }

  test('devuelve "Jugador" si no hay nombre guardado', () => {
    fakeStorage()
    assert.equal(api.getPlayer(), 'Jugador')
  })

  test('guarda el nombre sin espacios sobrantes', () => {
    const data = fakeStorage()
    api.setPlayer('  Javi  ')

    assert.equal(data.onetoFour_player, 'Javi')
    assert.equal(api.getPlayer(), 'Javi')
  })

  test('un nombre vacío se guarda como "Jugador"', () => {
    const data = fakeStorage()
    api.setPlayer('   ')

    assert.equal(data.onetoFour_player, 'Jugador')
  })

  test('no falla si el almacenamiento no está disponible', () => {
    globalThis.localStorage = {
      getItem() {
        throw new Error('bloqueado')
      },
      setItem() {
        throw new Error('bloqueado')
      },
    }

    assert.equal(api.getPlayer(), 'Jugador')
    assert.doesNotThrow(() => api.setPlayer('Javi'))
  })
})
