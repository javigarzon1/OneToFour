const API_URL=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')
const demoQuestions=[
{id:1,pregunta:'¿Cuál es la capital de España?',opcion_a:'Madrid',opcion_b:'Sevilla',opcion_c:'Valencia',opcion_d:'Bilbao',correcta:'A',categoria:'Geografía',dificultad:'Fácil'},
{id:2,pregunta:'¿Cuánto es 5 × 6?',opcion_a:'25',opcion_b:'30',opcion_c:'35',opcion_d:'40',correcta:'B',categoria:'Matemáticas',dificultad:'Fácil'},
{id:3,pregunta:'¿Qué lenguaje se utiliza en este proyecto?',opcion_a:'Java',opcion_b:'C++',opcion_c:'Python',opcion_d:'PHP',correcta:'C',categoria:'Programación',dificultad:'Fácil'},
{id:4,pregunta:'¿Cuál es el planeta más cercano al Sol?',opcion_a:'Venus',opcion_b:'Tierra',opcion_c:'Marte',opcion_d:'Mercurio',correcta:'D',categoria:'Ciencia',dificultad:'Fácil'},
{id:5,pregunta:'¿Qué estructura de Python almacena pares clave-valor?',opcion_a:'Lista',opcion_b:'Tupla',opcion_c:'Diccionario',opcion_d:'Conjunto',correcta:'C',categoria:'Programación',dificultad:'Medio'},
{id:6,pregunta:'¿Qué tecnología utiliza Databricks para almacenar tablas transaccionales?',opcion_a:'Delta Lake',opcion_b:'HTML',opcion_c:'FTP',opcion_d:'SMTP',correcta:'A',categoria:'Databricks',dificultad:'Medio'}
]
const demoRanking=[{jugador:'Ana',puntuacion:5,porcentaje:100},{jugador:'Carlos',puntuacion:4,porcentaje:80},{jugador:'Lucía',puntuacion:4,porcentaje:80}]

async function request(path,options={}) {
  const response=await fetch(API_URL+path,options)
  if(!response.ok){
    let detail='Error en la API.'
    try{const body=await response.json();detail=body.detail||detail}catch{}
    throw new Error(detail)
  }
  return response.json()
}

export async function getQuestions(params={}){
  if(!API_URL){
    return demoQuestions
      .filter(q=>!params.categoria||params.categoria==='Todas'||q.categoria===params.categoria)
      .filter(q=>!params.dificultad||params.dificultad==='Todas'||q.dificultad===params.dificultad)
  }
  return request('/api/questions?'+new URLSearchParams({...params,limit:params.limit||100}))
}

export async function saveGame(data){
  if(!API_URL)return {...data,partida_id:crypto.randomUUID()}
  return request('/api/games',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(data)
  })
}

export async function getRanking(){
  if(!API_URL)return demoRanking
  return request('/api/ranking')
}
