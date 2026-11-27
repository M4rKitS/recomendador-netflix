/* ¿Qué veo ahora? — lógica de la web.
   Los datos los genera exportar_web.py con el motor en Python: catalogo.json (todos los
   títulos) y fichas/NNN.json (detalle y recomendaciones precalculadas, en bloques de 100).

   Hay dos webs con este mismo código: la española (/, catálogo de Netflix España) y la
   inglesa (/en/, catálogo de Netflix USA). El idioma sale del atributo lang de la página. */

"use strict";

document.documentElement.classList.add("js");

const INGLES = document.documentElement.lang === "en";
const DATOS = INGLES ? "/datos/us/" : "/datos/es/";
const IMG = "https://image.tmdb.org/t/p/";
const POR_BLOQUE = 100;
const MAX_SUGERENCIAS = 8;

/** Todos los textos que escribe el JavaScript, en los dos idiomas. */
const TEXTOS = {
  es: {
    locale: "es-ES", decimal: ",", pais: "Netflix España",
    tipo: { p: "Película", s: "Serie" },
    publico: "Recomendada por el público",
    porciento: (n) => `${n} %`,
    noEncontrado: (q) => `No encontramos «${q}» en el catálogo actual de Netflix España. Prueba con otro título.`,
    errorFichas: "No se han podido cargar las recomendaciones. Recarga la página.",
    errorCatalogo: "No se ha podido cargar el catálogo. Recarga la página.",
    estos: { t: "Estos títulos", p: "Estas películas", s: "Estas series" },
    contexto: (estos, nombre, meta) => `${estos} del catálogo de Netflix España son los que más se parecen a ${nombre} (${meta.toLowerCase()}), ordenados por afinidad.`,
    sinParecidas: (f) => `No hay ${{ t: "títulos parecidos", p: "películas parecidas", s: "series parecidas" }[f]} en el catálogo. Prueba con «Todo».`,
    afinidad: "afinidad",
    deAfinidad: (n) => `${n} % de afinidad`,
    primera: "La que más se parece",
    partirDeEsta: "Recomiéndame a partir de esta",
    verFicha: "Ver ficha",
    y: " y ",
    elige: "Elige un título y verás aquí qué tiene en común con su mejor recomendación.",
    coinciden: (lista) => ` coinciden en ${lista}. `,
    sinCoincidencias: " se parecen por su sinopsis y su formato. ",
    comunidad: "Además, según la comunidad de TMDb, a quien le gustó una también le gustó la otra. ",
    cierreExplica: (n, nivel) => `Con un ${n} % de afinidad (${nivel}), es la primera recomendación. Los grupos marcados son los que más han pesado.`,
    niveles: ["del mismo estilo", "muy parecida", "de la misma familia"],
    tuBusqueda: (n) => `Tu búsqueda · ${n} %`,
    cartelDe: (nombre) => `Cartel de ${nombre}`,
    nota: (n) => `nota ${n}`,
    sinSinopsis: "Sin sinopsis.",
    generos: "Géneros", direccion: "Dirección", creacion: "Creación", reparto: "Reparto",
    partirSerie: "Recomiéndame a partir de esta serie",
    partirPelicula: "Recomiéndame a partir de esta película",
    teDaTiempo: (t) => `Con ${t} te da tiempo a ver`,
    duranMenos: (t) => `del catálogo de Netflix España: las que duran ${t} o menos.`,
    masPopular: " La más popular es ",
    queDura: (t) => `, que dura ${t}.`,
    abanico: (n, t) => `Las ${n} películas más populares que puedes ver en ${t}.`,
    pulsaUna: "Pulsa una y te recomendamos otras parecidas.",
    verRecomendaciones: (nombre, min) => `${nombre}, ${min} minutos. Ver recomendaciones`,
    actualizado: (fecha, total) => `Catálogo actualizado el ${fecha}: ${total} títulos.`,
  },
  en: {
    locale: "en-US", decimal: ".", pais: "Netflix US",
    tipo: { p: "Movie", s: "Series" },
    publico: "Recommended by audiences",
    porciento: (n) => `${n}%`,
    noEncontrado: (q) => `We couldn't find “${q}” in the current Netflix US catalog. Try another title.`,
    errorFichas: "The recommendations couldn't be loaded. Please reload the page.",
    errorCatalogo: "The catalog couldn't be loaded. Please reload the page.",
    estos: { t: "These titles", p: "These movies", s: "These series" },
    contexto: (estos, nombre, meta) => `${estos} from the Netflix US catalog are the closest to ${nombre} (${meta.toLowerCase()}), ranked by affinity.`,
    sinParecidas: (f) => `There are no similar ${{ t: "titles", p: "movies", s: "series" }[f]} in the catalog. Try “All”.`,
    afinidad: "affinity",
    deAfinidad: (n) => `${n}% affinity`,
    primera: "The closest match",
    partirDeEsta: "Recommend from this one",
    verFicha: "Details",
    y: " and ",
    elige: "Pick a title and you'll see here what it shares with its top recommendation.",
    coinciden: (lista) => ` share ${lista}. `,
    sinCoincidencias: " are alike in their synopsis and format. ",
    comunidad: "And according to the TMDb community, people who liked one also liked the other. ",
    cierreExplica: (n, nivel) => `With ${n}% affinity (${nivel}), it is the top recommendation. The highlighted groups are the ones that weighed most.`,
    niveles: ["same style", "very similar", "same family"],
    tuBusqueda: (n) => `Your search · ${n}%`,
    cartelDe: (nombre) => `Poster for ${nombre}`,
    nota: (n) => `rated ${n}`,
    sinSinopsis: "No synopsis.",
    generos: "Genres", direccion: "Director", creacion: "Creator", reparto: "Cast",
    partirSerie: "Recommend from this series",
    partirPelicula: "Recommend from this movie",
    teDaTiempo: (t) => `With ${t} you have time to watch`,
    duranMenos: (t) => `from the Netflix US catalog: the ones that run ${t} or less.`,
    masPopular: " The most popular is ",
    queDura: (t) => `, which runs ${t}.`,
    abanico: (n, t) => `The ${n} most popular movies you can watch in ${t}.`,
    pulsaUna: "Tap one and we'll recommend similar ones.",
    verRecomendaciones: (nombre, min) => `${nombre}, ${min} minutes. See recommendations`,
    actualizado: (fecha, total) => `Catalog updated on ${fecha}: ${total} titles.`,
  },
};
const T = TEXTOS[INGLES ? "en" : "es"];
const TIPO = T.tipo;
// Grupo de «Cómo decide» que ilumina cada motivo (los motivos llegan en el idioma de la web).
const GRUPO = {
  "Dirección": "Dirección", "Creación": "Dirección", Reparto: "Reparto", Temas: "Temas", "Géneros": "Géneros", "País": "País",
  Director: "Dirección", Creator: "Dirección", Cast: "Reparto", Themes: "Temas", Genres: "Géneros", Country: "País",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const menosMovimiento = matchMedia("(prefers-reduced-motion: reduce)");
const punteroFino = matchMedia("(hover: hover) and (pointer: fine)");
const estado = { catalogo: [], indice: [], bloques: new Map(), actual: null, filtro: "t", activa: -1, colores: new Map() };

/* ---------- Utilidades ---------- */

/** Minúsculas, sin acentos ni signos: "Miércoles!" -> "miercoles". */
function normalizar(texto) {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, " ").trim();
}

function crear(etiqueta, atributos = {}, ...hijos) {
  const el = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos)) {
    if (valor === undefined || valor === null || valor === false) continue;
    if (clave === "texto") el.textContent = valor;
    else if (clave.startsWith("on")) el.addEventListener(clave.slice(2), valor);
    else el.setAttribute(clave, valor);
  }
  for (const hijo of hijos) if (hijo !== null && hijo !== undefined && hijo !== false) el.append(hijo);
  return el;
}

function imagen(ruta, tamano, alt = "", { prisa = false } = {}) {
  return crear("img", { src: `${IMG}${tamano}${ruta}`, alt, loading: prisa ? "eager" : "lazy", decoding: "async" });
}

function titulo(i) { return estado.catalogo[i][0]; }
function meta(i) { const [, , anio, tipo] = estado.catalogo[i]; return [TIPO[tipo], anio].filter(Boolean).join(" · "); }
/** Nota del público ("★ 8,2"), o null si tiene muy pocos votos para fiarse. */
function decimal(n) { return String(n).replace(".", T.decimal); }
function nota(i) { const n = estado.catalogo[i][7]; return n ? `★\u00a0${decimal(n)}` : null; }
const PUBLICO = T.publico;

/** Icono de dos personas: la comunidad de TMDb también lo recomienda. */
function iconoPublico() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = '<circle cx="9" cy="8" r="3.25"/><path d="M2.75 19.5c.6-3.4 3.1-5.5 6.25-5.5s5.65 2.1 6.25 5.5"/><circle cx="16.5" cy="9" r="2.5"/><path d="M16.5 13.75c2.6 0 4.4 1.7 4.85 4.5"/>';
  return svg;
}
// El castellano no separa los miles en números de cuatro cifras ("6580"), pero aquí se lee mejor "6.580".
function numero(n) { return n.toLocaleString(T.locale, { useGrouping: "always" }); }

/** 190 -> "3 h 10 min", 120 -> "2 h", 45 -> "45 min". */
function horas(minutos) {
  const h = Math.floor(minutos / 60), m = minutos % 60;
  return [h ? `${h} h` : "", m ? `${m} min` : ""].filter(Boolean).join(" ");
}

function recortar(texto, max) {
  if (texto.length <= max) return texto;
  return `${texto.slice(0, texto.lastIndexOf(" ", max))}…`;
}

async function bloqueDe(i) {
  const n = Math.floor(i / POR_BLOQUE);
  if (!estado.bloques.has(n)) {
    const ruta = `${DATOS}fichas/${String(n).padStart(3, "0")}.json`;
    estado.bloques.set(n, fetch(ruta).then((r) => {
      if (!r.ok) throw new Error(`No se pudo cargar ${ruta}`);
      return r.json();
    }));
  }
  return (await estado.bloques.get(n))[i];
}

/** Cambia el contenido con una transición de vista si el navegador la tiene. */
function transicion(cambio) {
  if (!document.startViewTransition || menosMovimiento.matches || document.hidden) { cambio(); return; }
  const t = document.startViewTransition(cambio);
  t.ready.catch(() => {});
  t.finished.catch(() => {});
}

/** Anima un número de su valor actual hasta `hasta`. */
function contar(el, hasta, duracion = 900) {
  const desde = Number(el.dataset.valor || 0);
  el.dataset.valor = hasta;
  if (menosMovimiento.matches || desde === hasta) { el.textContent = numero(hasta); return; }
  const inicio = performance.now();
  const paso = (ahora) => {
    const t = Math.min((ahora - inicio) / duracion, 1);
    const e = 1 - (1 - t) ** 4;
    el.textContent = numero(Math.round(desde + (hasta - desde) * e));
    if (t < 1 && el.dataset.valor == hasta) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

/* ---------- Luz ambiente: el color del cartel elegido ---------- */

function colorDelCartel(ruta) {
  if (!ruta) return Promise.resolve(null);
  if (estado.colores.has(ruta)) return estado.colores.get(ruta);
  const promesa = new Promise((resolver) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const lienzo = document.createElement("canvas");
        lienzo.width = 24; lienzo.height = 36;
        const ctx = lienzo.getContext("2d", { willReadFrequently: true });
        ctx.drawImage(img, 0, 0, 24, 36);
        const { data } = ctx.getImageData(0, 0, 24, 36);
        // Media de los píxeles con más color: pesan más cuanto más saturados.
        let r = 0, g = 0, b = 0, total = 0;
        for (let k = 0; k < data.length; k += 4) {
          const max = Math.max(data[k], data[k + 1], data[k + 2]);
          const min = Math.min(data[k], data[k + 1], data[k + 2]);
          const sat = max ? (max - min) / max : 0;
          const peso = sat * sat * (max > 40 && max < 250 ? 1 : 0.1) + 0.002;
          r += data[k] * peso; g += data[k + 1] * peso; b += data[k + 2] * peso; total += peso;
        }
        resolver(ajustarColor(r / total, g / total, b / total));
      } catch { resolver(null); }
    };
    img.onerror = () => resolver(null);
    // w154 solo se usa aquí: así el navegador no reutiliza una copia en caché pedida sin CORS.
    img.src = `${IMG}w154${ruta}`;
  });
  estado.colores.set(ruta, promesa);
  return promesa;
}

/** Lo convierte en una luz agradable sobre fondo oscuro: saturación y brillo acotados. */
function ajustarColor(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;
  let h = 0, s = 0;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
    h *= 60;
  }
  const sat = s < 0.12 ? 25 : Math.min(Math.max(s * 100, 50), 82);
  return `hsl(${Math.round(h)} ${Math.round(sat)}% 56%)`;
}

async function ponerAmbiente(ruta) {
  const color = await colorDelCartel(ruta);
  document.documentElement.style.setProperty("--ambiente", color || "#4a5bd4");
}

/* ---------- Barra superior ---------- */

const barra = $(".barra");
const alDesplazar = () => barra.classList.toggle("opaca", scrollY > 40);
addEventListener("scroll", alDesplazar, { passive: true });
alDesplazar();

/* ---------- Menú: llevar cada sección al centro de la pantalla ---------- */

/** Desplaza hasta el contenido de la sección y lo centra en el hueco bajo la barra.
    Si no cabe entero, lo deja arriba, justo debajo de la barra. */
function irASeccion(seccion) {
  const contenido = seccion.querySelector(".contenedor") ?? seccion;
  const caja = contenido.getBoundingClientRect();
  const alto = barra.offsetHeight;
  const hueco = innerHeight - alto;
  const margen = 24;
  const destino = caja.height + margen * 2 <= hueco
    ? scrollY + caja.top - alto - (hueco - caja.height) / 2
    : scrollY + caja.top - alto - margen;
  scrollTo({ top: Math.max(0, destino), behavior: menosMovimiento.matches ? "auto" : "smooth" });
}

$$('a[href^="#"]').forEach((enlace) => {
  const seccion = document.getElementById(enlace.getAttribute("href").slice(1));
  if (!seccion || !seccion.matches("section")) return;
  enlace.addEventListener("click", (e) => {
    e.preventDefault();
    irASeccion(seccion);
    const titulo = seccion.querySelector("h2");
    titulo?.setAttribute("tabindex", "-1");
    titulo?.focus({ preventScroll: true });
  });
});

/* ---------- Portada: la pared de carteles ---------- */

function construirPared() {
  const pared = $("#pared");
  const columnas = matchMedia("(max-width: 720px)").matches ? 4 : 7;
  const porColumna = 7;
  const mejores = estado.catalogo
    .map((fila, i) => [i, fila[5], fila[4]])
    .filter(([, , cartel]) => cartel)
    .sort((a, b) => b[1] - a[1])
    .slice(0, columnas * porColumna)
    .map(([i]) => i);
  // Barajado estable para que no salgan siempre en orden de votos.
  mejores.sort((a, b) => ((a * 9301 + 49297) % 233280) - ((b * 9301 + 49297) % 233280));

  pared.style.setProperty("--columnas", columnas);
  const hijos = [];
  for (let c = 0; c < columnas; c += 1) {
    const ids = mejores.slice(c * porColumna, (c + 1) * porColumna);
    const columna = crear("div", {
      class: "pared-columna",
      style: `--duracion:${60 + ((c * 17) % 5) * 9}s; --sentido:${c % 2 ? "reverse" : "normal"}`,
    });
    // Dos veces la misma lista: al llegar a la mitad, el bucle no se nota.
    for (const vuelta of [0, 1]) ids.forEach((i) => columna.append(imagen(estado.catalogo[i][4], "w185", "", { prisa: vuelta === 0 && c < 4 })));
    hijos.push(columna);
  }
  pared.replaceChildren(...hijos);
  requestAnimationFrame(() => pared.classList.add("lista"));
}

/* ---------- Búsqueda ---------- */

function buscar(texto, limite = MAX_SUGERENCIAS) {
  const consulta = normalizar(texto);
  if (!consulta) return [];
  const empiezan = [];
  const contienen = [];
  const palabra = new RegExp(`\\b${consulta.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`);
  estado.indice.forEach(([nombre, alias], i) => {
    if (nombre.startsWith(consulta) || alias.some((a) => a.startsWith(consulta))) empiezan.push(i);
    else if (palabra.test(nombre) || alias.some((a) => palabra.test(a))) contienen.push(i);
  });
  // Primero los que empiezan por lo escrito; dentro de cada grupo, los más vistos.
  const porVotos = (a, b) => estado.catalogo[b][5] - estado.catalogo[a][5];
  return [...empiezan.sort(porVotos), ...contienen.sort(porVotos)].slice(0, limite);
}

function exacto(texto) {
  const consulta = normalizar(texto);
  const i = estado.indice.findIndex(([nombre, alias]) => nombre === consulta || alias.includes(consulta));
  return i >= 0 ? i : (buscar(texto, 1)[0] ?? -1);
}

/* ---------- Buscador accesible (combobox) ---------- */

const entrada = $("#entrada");
const lista = $("#sugerencias");

function mostrarSugerencias() {
  const resultados = buscar(entrada.value);
  lista.replaceChildren();
  estado.activa = -1;
  if (!resultados.length || (resultados.length === 1 && titulo(resultados[0]) === entrada.value)) {
    cerrarSugerencias();
    return;
  }
  resultados.forEach((i, n) => {
    const [nombre, alias, , , cartel] = estado.catalogo[i];
    lista.append(crear("li", {
      id: `sug-${n}`, role: "option", "aria-selected": "false", "data-indice": i,
      onmousedown: (e) => { e.preventDefault(); elegir(i); },
    },
      cartel ? imagen(cartel, "w92", "", { prisa: true }) : crear("span", { class: "sin-cartel" }),
      crear("span", {},
        crear("span", { class: "sug-titulo", texto: nombre }),
        alias ? crear("span", { class: "sug-alias", texto: alias }) : null),
      crear("span", { class: "sug-meta", texto: meta(i) })));
  });
  lista.hidden = false;
  entrada.setAttribute("aria-expanded", "true");
}

function cerrarSugerencias() {
  lista.hidden = true;
  entrada.setAttribute("aria-expanded", "false");
  entrada.removeAttribute("aria-activedescendant");
  estado.activa = -1;
}

function marcar(n) {
  const opciones = [...lista.children];
  if (!opciones.length) return;
  estado.activa = (n + opciones.length) % opciones.length;
  opciones.forEach((op, k) => op.setAttribute("aria-selected", String(k === estado.activa)));
  entrada.setAttribute("aria-activedescendant", opciones[estado.activa].id);
  opciones[estado.activa].scrollIntoView({ block: "nearest" });
}

entrada.addEventListener("input", mostrarSugerencias);
entrada.addEventListener("focus", () => entrada.select());
entrada.addEventListener("blur", () => setTimeout(cerrarSugerencias, 120));
entrada.addEventListener("keydown", (e) => {
  if (e.key === "ArrowDown") { e.preventDefault(); lista.hidden ? mostrarSugerencias() : marcar(estado.activa + 1); }
  else if (e.key === "ArrowUp") { e.preventDefault(); marcar(estado.activa - 1); }
  else if (e.key === "Escape") cerrarSugerencias();
  else if (e.key === "Enter" && estado.activa >= 0) {
    e.preventDefault();
    elegir(Number(lista.children[estado.activa].dataset.indice));
  }
});

$("#buscador").addEventListener("submit", (e) => {
  e.preventDefault();
  const i = exacto(entrada.value);
  if (i < 0) {
    cerrarSugerencias();
    $("#contexto").textContent = T.noEncontrado(entrada.value);
    $("#mira").scrollIntoView();
    return;
  }
  elegir(i);
});

function prepararEjemplos() {
  $$("[data-ejemplo]").forEach((boton) => {
    const i = exacto(boton.dataset.ejemplo);
    if (i >= 0 && estado.catalogo[i][4]) boton.prepend(imagen(estado.catalogo[i][4], "w92", "", { prisa: true }));
    boton.addEventListener("click", () => elegir(i));
  });
}

/* ---------- Elegir un título y mostrar sus recomendaciones ---------- */

async function elegir(i, { desplazar = true, historial = true } = {}) {
  if (i < 0) return;
  cerrarSugerencias();
  estado.actual = i;
  entrada.value = titulo(i);
  if (historial) history.replaceState(null, "", `?t=${encodeURIComponent(titulo(i))}`);
  ponerAmbiente(estado.catalogo[i][4]);
  await pintar();
  if (desplazar) $("#mira").scrollIntoView({ behavior: menosMovimiento.matches ? "auto" : "smooth" });
}

async function pintar() {
  const i = estado.actual;
  const caja = $("#resultados");
  caja.setAttribute("aria-busy", "true");
  let ficha;
  try {
    ficha = await bloqueDe(i);
  } catch {
    $("#contexto").textContent = T.errorFichas;
    caja.removeAttribute("aria-busy");
    return;
  }

  const ids = ficha.l[estado.filtro];
  const [nombre, , , , cartel] = estado.catalogo[i];
  const estos = T.estos[estado.filtro];

  const [primera, ...resto] = ids.slice(0, 11);
  const fichaPrimera = primera !== undefined ? await bloqueDe(primera).catch(() => null) : null;

  transicion(() => {
    $("#origen").replaceChildren(cartel ? imagen(cartel, "w342", "", { prisa: true }) : "");
    $("#mira-nombre").textContent = nombre;
    $("#contexto").replaceChildren(
      ids.length
        ? T.contexto(estos, nombre, meta(i))
        : T.sinParecidas(estado.filtro));
    caja.replaceChildren(...(ids.length ? [destacada(primera, ficha.r[primera], fichaPrimera), carteles(resto, ficha.r)] : []));
    caja.removeAttribute("aria-busy");
  });

  explicar(i, primera, ids.length ? ficha.r[primera] : null);
  requestAnimationFrame(() => requestAnimationFrame(() => {
    $$(".anillo").forEach((a) => a.style.setProperty("--a", a.dataset.afinidad));
  }));
}

function itemsMotivos(motivos, publico) {
  return [
    publico ? crear("li", { class: "motivo-publico" }, iconoPublico(), PUBLICO) : null,
    ...motivos.map(([n, v]) => crear("li", {}, crear("b", { texto: n }), v.join(", "))),
  ];
}

function chipsMotivos(motivos, publico) {
  return crear("ul", { class: "motivos" }, ...itemsMotivos(motivos, publico));
}

function destacada(j, [afinidad, motivos, publico], ficha) {
  const [nombre, , , , cartel] = estado.catalogo[j];
  const abrir = () => abrirFicha(j, motivos, publico);
  const fondo = ficha?.bd ? imagen(ficha.bd, "w1280", "", { prisa: true }) : (cartel ? imagen(cartel, "w780", "", { prisa: true }) : null);
  return crear("article", { class: "destacada aparecer", onclick: abrir },
    crear("div", { class: "destacada-fondo" }, fondo),
    crear("div", { class: "anillo", "data-afinidad": afinidad, role: "img", "aria-label": T.deAfinidad(afinidad) },
      crear("b", { texto: `${afinidad}%` }), crear("span", { texto: T.afinidad })),
    crear("div", { class: "destacada-info" },
      crear("div", { class: "destacada-cabeza" },
        cartel ? crear("div", { class: "destacada-cartel" }, imagen(cartel, "w342", "", { prisa: true })) : null,
        crear("div", {},
          crear("p", { class: "destacada-puesto", texto: T.primera }),
          crear("h3", { class: "destacada-titulo" }, crear("button", { type: "button", texto: nombre, onclick: (e) => { e.stopPropagation(); abrir(); } })),
          crear("p", { class: "meta", texto: [meta(j), ficha?.dur, nota(j)].filter(Boolean).join(" · ") }))),
      motivos.length || publico ? chipsMotivos(motivos, publico) : null,
      ficha?.d ? crear("p", { class: "destacada-sinopsis", texto: recortar(ficha.d, 240) }) : null,
      crear("div", { class: "destacada-acciones" },
        crear("button", { type: "button", class: "boton", texto: T.partirDeEsta, onclick: (e) => { e.stopPropagation(); elegir(j); } }),
        crear("button", { type: "button", class: "boton boton-fantasma", texto: T.verFicha, onclick: (e) => { e.stopPropagation(); abrir(); } }))));
}

function carteles(ids, recomendados) {
  return crear("ul", { class: "carteles" }, ...ids.map((j, n) => {
    const [nombre, , , , cartel] = estado.catalogo[j];
    const [afinidad, motivos, publico] = recomendados[j];
    const abrir = () => abrirFicha(j, motivos, publico);
    const marco = crear("div", { class: "cartel-marco" },
      crear("span", { class: "cartel-puesto", texto: `${afinidad}%`, "aria-label": T.deAfinidad(afinidad) }),
      publico ? crear("span", { class: "cartel-publico", title: PUBLICO, role: "img", "aria-label": PUBLICO }, iconoPublico()) : null,
      cartel ? imagen(cartel, "w342", "") : crear("div", { class: "sin-cartel-grande", texto: nombre }),
      motivos.length || publico ? crear("div", { class: "cartel-capa", "aria-hidden": "true" },
        publico ? crear("span", {}, crear("b", { texto: PUBLICO })) : null,
        ...motivos.map(([k, v]) => crear("span", {}, crear("b", { texto: `${k} ` }), v.join(", ")))) : null);
    relieve(marco);
    return crear("li", { class: "cartel aparecer", style: `--retraso:${120 + n * 55}ms` },
      marco,
      crear("h3", { class: "cartel-titulo" }, crear("button", { type: "button", texto: nombre, onclick: abrir })),
      crear("p", { class: "meta", texto: [meta(j), nota(j)].filter(Boolean).join(" · ") }));
  }));
}

/** Relieve 3D con reflejo de luz que sigue al ratón. */
function relieve(marco) {
  if (!punteroFino.matches || menosMovimiento.matches) return;
  marco.addEventListener("pointermove", (e) => {
    const caja = marco.getBoundingClientRect();
    const x = (e.clientX - caja.left) / caja.width;
    const y = (e.clientY - caja.top) / caja.height;
    marco.classList.add("siguiendo");
    marco.style.setProperty("--ry", `${(x - 0.5) * 14}deg`);
    marco.style.setProperty("--rx", `${(0.5 - y) * 14}deg`);
    marco.style.setProperty("--gx", `${x * 100}%`);
    marco.style.setProperty("--gy", `${y * 100}%`);
  });
  marco.addEventListener("pointerleave", () => {
    marco.classList.remove("siguiendo");
    marco.style.setProperty("--rx", "0deg");
    marco.style.setProperty("--ry", "0deg");
  });
}

/* ---------- Cómo decide, en vivo ---------- */

function explicar(origen, primera, datos) {
  const caja = $("#en-vivo-texto");
  const coinciden = new Set((datos?.[1] ?? []).map(([n]) => GRUPO[n]));
  $$("#pesos li").forEach((li) => li.classList.toggle("coincide", coinciden.has(li.dataset.grupo)));
  marcarEscala(datos?.[0]);
  if (!datos) { caja.textContent = T.elige; return; }
  const [afinidad, motivos, publico] = datos;
  const partes = motivos.map(([n, v]) => `${n.toLowerCase()} (${v.join(", ")})`);
  const lista = partes.length > 1 ? `${partes.slice(0, -1).join(", ")}${T.y}${partes.at(-1)}` : partes[0];
  caja.replaceChildren(
    crear("strong", { texto: titulo(origen) }), T.y, crear("strong", { texto: titulo(primera) }),
    lista ? T.coinciden(lista) : T.sinCoincidencias,
    publico ? T.comunidad : "",
    T.cierreExplica(afinidad, nivel(afinidad)));
}

/** Lectura en palabras de un porcentaje de afinidad (la misma escala que explica la web). */
function zona(afinidad) { return afinidad >= 40 ? 3 : afinidad >= 25 ? 2 : 1; }
function nivel(afinidad) { return T.niveles[zona(afinidad) - 1]; }

/** Lleva la marca del medidor a la afinidad de la mejor recomendación e ilumina su zona. */
function marcarEscala(afinidad) {
  const escala = $("#escala");
  const hay = Number.isFinite(afinidad);
  escala.classList.toggle("con-valor", hay);
  escala.style.setProperty("--valor", hay ? afinidad : 0);
  if (hay) $("#medidor-texto").textContent = T.tuBusqueda(afinidad);
  $$("#escala .zonas li").forEach((li) => li.classList.toggle("activa", hay && Number(li.dataset.zona) === zona(afinidad)));
}

/* ---------- Filtro Todo / Películas / Series ---------- */

const radios = $$(".filtro [role=radio]");
function filtrar(boton) {
  radios.forEach((r, n) => {
    const activo = r === boton;
    r.setAttribute("aria-checked", String(activo));
    r.tabIndex = activo ? 0 : -1;
    if (activo) $(".filtro").style.setProperty("--i", n);
  });
  estado.filtro = boton.dataset.tipo;
  if (estado.actual !== null) pintar();
}
radios.forEach((r, n) => {
  r.tabIndex = n === 0 ? 0 : -1;
  r.addEventListener("click", () => filtrar(r));
  r.addEventListener("keydown", (e) => {
    const paso = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    if (!paso) return;
    e.preventDefault();
    const siguiente = radios[(n + paso + radios.length) % radios.length];
    siguiente.focus();
    filtrar(siguiente);
  });
});

/* ---------- Ficha de detalle ---------- */

const dialogo = $("#ficha");

async function abrirFicha(j, motivos = [], publico = 0) {
  const ficha = await bloqueDe(j).catch(() => null);
  if (!ficha) return;
  const [nombre, alias, anio, tipo, cartel] = estado.catalogo[j];
  $("#ficha-fondo").replaceChildren(ficha.bd ? imagen(ficha.bd, "w1280", "", { prisa: true }) : "");
  $("#ficha-cartel").replaceChildren(cartel ? imagen(cartel, "w342", T.cartelDe(nombre), { prisa: true }) : "");
  $("#ficha-titulo").textContent = nombre;
  $("#ficha-meta").textContent = [TIPO[tipo], anio, ficha.dur, ficha.nota ? T.nota(decimal(ficha.nota)) : null, alias]
    .filter(Boolean).join(" · ");
  $("#ficha-motivos").replaceChildren(...itemsMotivos(motivos, publico).filter(Boolean));
  $("#ficha-motivos").hidden = !motivos.length && !publico;
  $("#ficha-sinopsis").textContent = ficha.d || T.sinSinopsis;
  const datos = [
    [T.generos, ficha.g],
    [tipo === "s" ? T.creacion : T.direccion, ficha.dir],
    [T.reparto, ficha.rep.join(", ")],
  ].filter(([, v]) => v);
  $("#ficha-datos").replaceChildren(...datos.flatMap(([k, v]) => [crear("dt", { texto: k }), crear("dd", { texto: v })]));
  const tmdb = $("#ficha-tmdb");
  tmdb.href = `https://www.themoviedb.org/${tipo === "s" ? "tv" : "movie"}/${ficha.tmdb}`;
  tmdb.hidden = !ficha.tmdb;
  $("#ficha-partir").textContent = tipo === "s" ? T.partirSerie : T.partirPelicula;
  $("#ficha-partir").onclick = () => { dialogo.close(); elegir(j); };
  dialogo.showModal();
  dialogo.scrollTop = 0;
}

$("#ficha-cerrar").addEventListener("click", () => dialogo.close());
dialogo.addEventListener("click", (e) => { if (e.target === dialogo) dialogo.close(); });

/* ---------- ¿Cuánto tiempo tienes? ---------- */

const minutos = $("#minutos");
let abanicoActual = "";

function contarPeliculas() {
  const limite = Number(minutos.value);
  const p = ((limite - minutos.min) / (minutos.max - minutos.min)) * 100;
  minutos.style.setProperty("--p", `${p}%`);
  const tiempo = horas(limite);
  $("#minutos-valor").textContent = tiempo;
  $("#resultado-antes").textContent = T.teDaTiempo(tiempo);

  const caben = [];
  estado.catalogo.forEach(([, , , tipo, , , duracion], i) => {
    if (tipo === "p" && duracion > 0 && duracion <= limite) caben.push(i);
  });
  contar($("#cifra"), caben.length);
  caben.sort((a, b) => estado.catalogo[b][5] - estado.catalogo[a][5]);
  const cinco = caben.filter((i) => estado.catalogo[i][4]).slice(0, 5);

  const explica = $("#noche-explica");
  explica.replaceChildren(T.duranMenos(tiempo));
  if (cinco.length) {
    const mejor = cinco[0];
    explica.append(T.masPopular, crear("a", {
      href: `?t=${encodeURIComponent(titulo(mejor))}`, texto: titulo(mejor),
      onclick: (e) => { e.preventDefault(); elegir(mejor); },
    }), T.queDura(horas(estado.catalogo[mejor][6])));
  }

  $("#abanico-pie").replaceChildren(
    crear("strong", { texto: T.abanico(cinco.length, tiempo) }),
    crear("br"), T.pulsaUna);

  const clave = cinco.join();
  if (clave === abanicoActual) return;
  abanicoActual = clave;
  const abanico = $("#abanico");
  // El más visto en el centro, los demás a los lados.
  const orden = [cinco[3], cinco[1], cinco[0], cinco[2], cinco[4]].filter((i) => i !== undefined);
  abanico.classList.remove("cambia");
  abanico.replaceChildren(...orden.map((i) => crear("li", {},
    crear("button", { type: "button", "aria-label": T.verRecomendaciones(titulo(i), estado.catalogo[i][6]), onclick: () => elegir(i) },
      imagen(estado.catalogo[i][4], "w342", "")))));
  void abanico.offsetWidth;
  abanico.classList.add("cambia");
}
minutos.addEventListener("input", contarPeliculas);

/* ---------- Entradas al hacer scroll ---------- */

function revelar() {
  const piezas = $$(".como-texto, .pesos, .escala, .pasos, .cifras, .noche-texto, .abanico-marco, .cierre-arriba");
  if (!("IntersectionObserver" in window)) { piezas.forEach((p) => p.classList.add("visible")); return; }
  const observador = new IntersectionObserver((entradas) => {
    entradas.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.classList.add("visible");
      if (e.target.id === "cifras") $$("#cifras dd").forEach((dd) => contar(dd, Number(dd.dataset.cuenta), 1400));
      observador.unobserve(e.target);
    });
  }, { threshold: 0.2 });
  // Pesos y pasos entran pieza a pieza (en el CSS), no como un bloque.
  piezas.forEach((p) => { if (!p.matches(".pesos, .pasos")) p.classList.add("revela"); observador.observe(p); });
}

/* ---------- Arranque ---------- */

async function iniciar() {
  const listo = () => document.documentElement.classList.add("listo");
  (document.fonts?.ready ?? Promise.resolve()).then(listo);
  setTimeout(listo, 1200); // por si la fuente tarda: nunca dejar el titular oculto
  revelar();

  let datos;
  try {
    datos = await fetch(`${DATOS}catalogo.json`).then((r) => r.json());
  } catch {
    $("#contexto").textContent = T.errorCatalogo;
    return;
  }
  estado.catalogo = datos.titulos;
  estado.indice = datos.titulos.map(([nombre, alias]) => [
    normalizar(nombre), alias ? alias.split(" | ").map(normalizar) : [],
  ]);

  const total = estado.catalogo.length;
  const peliculas = estado.catalogo.filter((t) => t[3] === "p").length;
  const fecha = new Date(`${datos.actualizado}T12:00:00`);
  $("#actualizado").textContent = T.actualizado(fecha.toLocaleDateString(T.locale, { day: "numeric", month: "long", year: "numeric" }), numero(total));
  const cifras = $$("#cifras dd");
  [total, peliculas, total - peliculas].forEach((n, k) => { cifras[k].dataset.cuenta = n; cifras[k].textContent = numero(n); });

  construirPared();
  prepararEjemplos();
  contarPeliculas();

  const pedido = new URLSearchParams(location.search).get("t");
  const inicial = exacto(pedido || entrada.value);
  if (inicial >= 0) elegir(inicial, { desplazar: Boolean(pedido), historial: Boolean(pedido) });
}

iniciar();
