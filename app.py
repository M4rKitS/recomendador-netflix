"""Interfaz gráfica (tkinter) del recomendador de Netflix.

Ejecuta:  python app.py
"""

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from recomendador import Recomendador, buscar_csv

CARPETA_DATOS = Path(__file__).parent / "data"

# Paleta inspirada en Netflix
NEGRO = "#141414"
GRIS = "#222222"
GRIS_CLARO = "#2f2f2f"
TEXTO = "#e5e5e5"
TEXTO_SUAVE = "#9a9a9a"
ROJO = "#e50914"
ROJO_OSCURO = "#b20710"
FUENTE = "Helvetica"

FILTROS = {"Todo": None, "Películas": "Movie", "Series": "TV Show"}
NOMBRES_GRUPO = {
    "director": "Dirección", "reparto": "Reparto", "generos": "Géneros", "temas": "Temas", "pais": "País",
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Recomendador de Netflix")
        self.geometry("1000x700")
        self.minsize(820, 560)
        self.configure(bg=NEGRO)

        self.motor = None
        self.resultados = []
        self._cola = queue.Queue()

        self._estilos()
        self._construir_interfaz()
        self.after(100, self._cargar_datos)

    # ------------------------------------------------------------------ #
    # Aspecto
    # ------------------------------------------------------------------ #

    def _estilos(self):
        estilo = ttk.Style(self)
        estilo.theme_use("clam")  # 'clam' permite cambiar colores en todos los sistemas
        estilo.configure(".", background=NEGRO, foreground=TEXTO, font=(FUENTE, 13))
        estilo.configure("TFrame", background=NEGRO)
        estilo.configure("TLabel", background=NEGRO, foreground=TEXTO)
        estilo.configure("Suave.TLabel", foreground=TEXTO_SUAVE, font=(FUENTE, 12))
        estilo.configure("Logo.TLabel", foreground=ROJO, font=(FUENTE, 30, "bold"))
        estilo.configure("Subtitulo.TLabel", foreground=TEXTO_SUAVE, font=(FUENTE, 14))
        estilo.configure("Seccion.TLabel", font=(FUENTE, 15, "bold"))

        estilo.configure(
            "TEntry", fieldbackground=GRIS_CLARO, foreground=TEXTO,
            insertcolor=TEXTO, bordercolor=GRIS_CLARO, lightcolor=GRIS_CLARO, padding=8,
        )
        estilo.map("TEntry", bordercolor=[("focus", ROJO)], lightcolor=[("focus", ROJO)])

        estilo.configure(
            "Rojo.TButton", background=ROJO, foreground="white", borderwidth=0,
            focuscolor=ROJO, font=(FUENTE, 13, "bold"), padding=(18, 8),
        )
        estilo.map("Rojo.TButton", background=[("disabled", GRIS_CLARO), ("active", ROJO_OSCURO)])

        estilo.configure("TRadiobutton", background=NEGRO, foreground=TEXTO, indicatorcolor=GRIS_CLARO)
        estilo.map("TRadiobutton", indicatorcolor=[("selected", ROJO)], background=[("active", NEGRO)])

        estilo.configure(
            "TSpinbox", fieldbackground=GRIS_CLARO, foreground=TEXTO, arrowcolor=TEXTO,
            background=GRIS, bordercolor=GRIS_CLARO, padding=4,
        )

        estilo.configure(
            "Treeview", background=GRIS, fieldbackground=GRIS, foreground=TEXTO,
            rowheight=30, borderwidth=0, font=(FUENTE, 12),
        )
        estilo.map("Treeview", background=[("selected", ROJO_OSCURO)], foreground=[("selected", "white")])
        estilo.configure(
            "Treeview.Heading", background=GRIS_CLARO, foreground=TEXTO,
            font=(FUENTE, 12, "bold"), borderwidth=0, padding=6,
        )
        estilo.map("Treeview.Heading", background=[("active", GRIS_CLARO)])
        estilo.configure("Vertical.TScrollbar", background=GRIS_CLARO, troughcolor=GRIS, arrowcolor=TEXTO)

    # ------------------------------------------------------------------ #
    # Widgets
    # ------------------------------------------------------------------ #

    def _construir_interfaz(self):
        raiz = ttk.Frame(self, padding=(28, 20))
        raiz.pack(fill="both", expand=True)

        # Cabecera
        cabecera = ttk.Frame(raiz)
        cabecera.pack(fill="x")
        ttk.Label(cabecera, text="NETFLIX", style="Logo.TLabel").pack(side="left")
        ttk.Label(cabecera, text="  ·  ¿Qué ver ahora?", style="Subtitulo.TLabel").pack(side="left", pady=(8, 0))

        ttk.Label(
            raiz, text="Escribe una película o serie que te haya gustado:", style="Suave.TLabel"
        ).pack(anchor="w", pady=(18, 6))

        # Buscador + botón
        fila = ttk.Frame(raiz)
        fila.pack(fill="x")
        self.busqueda = tk.StringVar()
        self.entrada = ttk.Entry(fila, textvariable=self.busqueda, font=(FUENTE, 15))
        self.entrada.pack(side="left", fill="x", expand=True)
        self.entrada.bind("<KeyRelease>", self._al_escribir)
        self.entrada.bind("<Return>", lambda e: self._recomendar())
        self.entrada.bind("<Down>", self._bajar_a_sugerencias)
        self.boton = ttk.Button(
            fila, text="Recomendar", style="Rojo.TButton", command=self._recomendar, state="disabled"
        )
        self.boton.pack(side="left", padx=(10, 0))

        # Sugerencias (aparecen bajo el buscador mientras se escribe)
        self.sugerencias = tk.Listbox(
            raiz, height=6, bg=GRIS_CLARO, fg=TEXTO, selectbackground=ROJO,
            selectforeground="white", highlightthickness=0, borderwidth=0,
            font=(FUENTE, 13), activestyle="none",
        )
        self.sugerencias.bind("<<ListboxSelect>>", self._elegir_sugerencia)
        self.sugerencias.bind("<Return>", self._elegir_sugerencia)

        # Opciones
        self.opciones = ttk.Frame(raiz)
        self.opciones.pack(fill="x", pady=(12, 14))
        ttk.Label(self.opciones, text="Mostrar:", style="Suave.TLabel").pack(side="left")
        self.filtro = tk.StringVar(value="Todo")
        for nombre in FILTROS:
            ttk.Radiobutton(
                self.opciones, text=nombre, value=nombre, variable=self.filtro,
                command=self._refrescar_si_hay_resultados,
            ).pack(side="left", padx=(10, 0))
        self.cantidad = tk.IntVar(value=10)
        ttk.Spinbox(
            self.opciones, from_=5, to=30, increment=5, width=4, textvariable=self.cantidad,
            command=self._refrescar_si_hay_resultados, state="readonly",
        ).pack(side="right")
        ttk.Label(self.opciones, text="Nº de recomendaciones:", style="Suave.TLabel").pack(side="right", padx=8)

        # Zona de resultados: tabla + detalle
        self.resultados_frame = ttk.Frame(raiz)
        self.resultados_frame.pack(fill="both", expand=True)

        tabla_frame = ttk.Frame(self.resultados_frame)
        tabla_frame.pack(side="left", fill="both", expand=True)
        columnas = ("titulo", "anio", "tipo", "afinidad", "nota")
        self.tabla = ttk.Treeview(tabla_frame, columns=columnas, show="headings", selectmode="browse")
        for col, texto, ancho, ancla in (
            ("titulo", "Título", 280, "w"), ("anio", "Año", 60, "center"), ("tipo", "Tipo", 80, "center"),
            ("afinidad", "Afinidad", 85, "center"), ("nota", "Nota", 60, "center"),
        ):
            self.tabla.heading(col, text=texto, anchor=ancla)
            self.tabla.column(col, width=ancho, anchor=ancla, stretch=(col == "titulo"))
        self.tabla.tag_configure("par", background=GRIS)
        self.tabla.tag_configure("impar", background="#1b1b1b")
        barra = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")
        self.tabla.bind("<<TreeviewSelect>>", self._mostrar_detalle)

        detalle = tk.Frame(self.resultados_frame, bg=GRIS, width=330)
        detalle.pack(side="left", fill="both", padx=(14, 0))
        detalle.pack_propagate(False)
        self.detalle = tk.Text(
            detalle, bg=GRIS, fg=TEXTO, wrap="word", borderwidth=0, highlightthickness=0,
            padx=16, pady=14, font=(FUENTE, 12), cursor="arrow",
        )
        self.detalle.pack(fill="both", expand=True)
        self.detalle.tag_configure("titulo", font=(FUENTE, 17, "bold"), spacing3=4)
        self.detalle.tag_configure("meta", foreground=TEXTO_SUAVE, spacing3=10)
        self.detalle.tag_configure("seccion", foreground=ROJO, font=(FUENTE, 12, "bold"), spacing1=12, spacing3=4)
        self.detalle.tag_configure("cuerpo", spacing3=2)
        self._escribir_detalle([("Elige un resultado para ver su sinopsis y por qué te lo recomendamos.", "meta")])

        # Barra de estado
        self.estado = tk.StringVar(value="Cargando catálogo…")
        pie = ttk.Frame(raiz)
        pie.pack(fill="x", pady=(10, 0))
        ttk.Label(pie, textvariable=self.estado, style="Suave.TLabel").pack(anchor="w")
        # Atribución obligatoria según las condiciones de uso de la API de TMDb.
        ttk.Label(
            pie, text="Datos: TMDb y JustWatch. Este producto usa la API de TMDb pero no está avalado por TMDb.",
            style="Suave.TLabel", font=(FUENTE, 10),
        ).pack(anchor="w", pady=(2, 0))

    # ------------------------------------------------------------------ #
    # Carga del dataset (en segundo plano para no congelar la ventana)
    # ------------------------------------------------------------------ #

    def _cargar_datos(self, ruta=None):
        ruta = ruta or buscar_csv(CARPETA_DATOS)
        if ruta is None:
            messagebox.showinfo(
                "Falta el dataset",
                "No encuentro el CSV de Netflix en la carpeta data/.\n\n"
                "Descarga el catálogo actual con  python descargar_catalogo.py\n"
                "(ver README) o selecciona un CSV ahora.",
            )
            ruta = filedialog.askopenfilename(
                title="Selecciona el CSV de Netflix", filetypes=[("CSV", "*.csv")]
            )
            if not ruta:
                self.estado.set("Sin dataset: no puedo recomendar nada todavía.")
                return

        self.ruta_datos = Path(ruta)
        self.estado.set(f"Analizando {self.ruta_datos.name}…")

        def tarea():
            try:
                self._cola.put(Recomendador.desde_csv(ruta))
            except Exception as error:  # se muestra al usuario en la ventana
                self._cola.put(error)

        threading.Thread(target=tarea, daemon=True).start()
        self.after(100, self._esperar_carga)

    def _esperar_carga(self):
        try:
            resultado = self._cola.get_nowait()
        except queue.Empty:
            self.after(100, self._esperar_carga)
            return
        if isinstance(resultado, Exception):
            messagebox.showerror("Error al cargar el dataset", str(resultado))
            self.estado.set("No se pudo cargar el dataset.")
            return
        self.motor = resultado
        self.boton.state(["!disabled"])
        total = len(self.motor.datos)
        peliculas = int((self.motor.datos["tipo"] == "Movie").sum())
        self.estado.set(
            f"Catálogo listo: {total} títulos ({peliculas} películas, {total - peliculas} series)"
            f" · {self.ruta_datos.name}"
        )
        self.entrada.focus_set()

    # ------------------------------------------------------------------ #
    # Buscador con sugerencias
    # ------------------------------------------------------------------ #

    def _al_escribir(self, evento):
        if evento.keysym in ("Return", "Down", "Up", "Escape"):
            if evento.keysym == "Escape":
                self._ocultar_sugerencias()
            return
        if not self.motor:
            return
        coincidencias = self.motor.buscar_titulos(self.busqueda.get(), limite=8)
        if not coincidencias or coincidencias == [self.busqueda.get()]:
            self._ocultar_sugerencias()
            return
        self.sugerencias.delete(0, "end")
        for titulo in coincidencias:
            self.sugerencias.insert("end", titulo)
        self.sugerencias.configure(height=len(coincidencias))
        if not self.sugerencias.winfo_ismapped():
            self.sugerencias.pack(fill="x", before=self.opciones, pady=(2, 0))

    def _bajar_a_sugerencias(self, _evento):
        if self.sugerencias.winfo_ismapped():
            self.sugerencias.focus_set()
            self.sugerencias.selection_clear(0, "end")
            self.sugerencias.selection_set(0)
            self.sugerencias.activate(0)

    def _elegir_sugerencia(self, _evento):
        seleccion = self.sugerencias.curselection()
        if not seleccion:
            return
        self.busqueda.set(self.sugerencias.get(seleccion[0]))
        self._ocultar_sugerencias()
        self.entrada.icursor("end")
        self.entrada.focus_set()
        self._recomendar()

    def _ocultar_sugerencias(self):
        self.sugerencias.pack_forget()

    # ------------------------------------------------------------------ #
    # Recomendaciones
    # ------------------------------------------------------------------ #

    def _refrescar_si_hay_resultados(self):
        if self.resultados:
            self._recomendar()

    def _recomendar(self):
        if not self.motor:
            return
        self._ocultar_sugerencias()
        titulo = self.busqueda.get().strip()
        if not titulo:
            self.estado.set("Escribe un título para empezar.")
            return

        # Si no es exacto, usamos la mejor sugerencia ("narcos" -> "Narcos").
        if self.motor.indice_de(titulo) is None:
            parecidos = self.motor.buscar_titulos(titulo, limite=1)
            if not parecidos:
                self.estado.set(f"No encuentro «{titulo}» en el catálogo de Netflix.")
                self._limpiar_resultados()
                return
            titulo = parecidos[0]
            self.busqueda.set(titulo)

        self.resultados = self.motor.recomendar(
            titulo, cantidad=int(self.cantidad.get()), tipo=FILTROS[self.filtro.get()]
        )
        self._limpiar_resultados(borrar_lista=False)
        for n, rec in enumerate(self.resultados):
            nota = "—" if rec.nota != rec.nota else f"{rec.nota:.1f}"  # NaN != NaN
            tipo = "Película" if rec.tipo == "Movie" else "Serie" if rec.tipo == "TV Show" else rec.tipo
            self.tabla.insert(
                "", "end", iid=str(n), values=(rec.titulo, rec.anio, tipo, f"{rec.similitud:.0f} %", nota),
                tags=("par" if n % 2 == 0 else "impar",),
            )
        if self.resultados:
            self.estado.set(f"{len(self.resultados)} recomendaciones porque te gustó «{titulo}».")
            self.tabla.selection_set("0")
        else:
            self.estado.set(f"No hay títulos parecidos a «{titulo}» con ese filtro.")

    def _limpiar_resultados(self, borrar_lista=True):
        if borrar_lista:
            self.resultados = []
        self.tabla.delete(*self.tabla.get_children())
        self._escribir_detalle([])

    def _mostrar_detalle(self, _evento):
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        rec = self.resultados[int(seleccion[0])]
        partes = [
            (rec.titulo + "\n", "titulo"),
            (" · ".join(x for x in (rec.anio, rec.generos) if x) + "\n", "meta"),
            ("Sinopsis\n", "seccion"),
            ((rec.descripcion or "Sin descripción.") + "\n", "cuerpo"),
            ("Por qué te lo recomendamos\n", "seccion"),
        ]
        if rec.coincidencias:
            for grupo, valores in rec.coincidencias.items():
                nombres = ", ".join(valores[:4])
                etiqueta = "Creación" if grupo == "director" and rec.tipo == "TV Show" else NOMBRES_GRUPO[grupo]
                partes.append((f"• {etiqueta}: {nombres}\n", "cuerpo"))
        else:
            partes.append(("• Argumento y tono parecidos.\n", "cuerpo"))
        self._escribir_detalle(partes)

    def _escribir_detalle(self, partes):
        self.detalle.configure(state="normal")
        self.detalle.delete("1.0", "end")
        for texto, etiqueta in partes:
            self.detalle.insert("end", texto, etiqueta)
        self.detalle.configure(state="disabled")


if __name__ == "__main__":
    App().mainloop()
