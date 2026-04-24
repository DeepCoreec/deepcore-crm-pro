"""DeepCore CRM Pro — Panel del Agente IA con ejecución real de herramientas."""
import threading
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
import database as db
from modules.agent_engine import AgentEngine, ollama_disponible, ollama_modelos

_ACCIONES_RAPIDAS = [
    ("Resumen hoy",  "Dame un resumen ejecutivo del CRM: contactos, pipeline y actividades pendientes."),
    ("Pendientes",   "¿Qué actividades tengo pendientes? Ordénalas por prioridad y dime cuál hacer primero."),
    ("Pipeline",     "Analiza mi pipeline de ventas. ¿Qué oportunidades están en riesgo? ¿Cuál tiene más valor?"),
    ("Alertas",      "Identifica alertas críticas: oportunidades sin actividad reciente, contactos fríos y tareas vencidas."),
]

_COLOR_CORRIENDO = '#F59E0B'
_COLOR_OK        = '#10B981'
_COLOR_ERROR     = '#EF4444'


def _ts() -> str:
    return datetime.now().strftime('%H:%M')


class AgentPanel(ctk.CTkFrame):
    """Panel del Agente IA — conversación con ejecución real de herramientas."""

    def __init__(self, parent, C: dict, on_datos_cambiados=None):
        super().__init__(parent, fg_color='transparent')
        self.C = C
        self._on_datos_cambiados = on_datos_cambiados
        self._engine: AgentEngine | None = None
        self._historial: list[dict] = []
        self._pensando = False
        self._anim_id  = None
        self._modelo_var  = tk.StringVar(value='haiku')
        self._backend_var = tk.StringVar(value='claude')
        self._ollama_modelo_var = tk.StringVar(value='llama3.2')
        self._pasos_activos: dict = {}
        self._grupo_herramientas: ctk.CTkFrame | None = None

        self._build()
        self._inicializar_engine()
        self._mostrar_bienvenida()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        C = self.C

        # Franja superior de acento
        ctk.CTkFrame(self, fg_color=C['mauve'], height=3, corner_radius=0).pack(fill='x')

        # ── Cabecera ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color='transparent')
        hdr.pack(fill='x', padx=24, pady=(16, 0))

        title_row = ctk.CTkFrame(hdr, fg_color='transparent')
        title_row.pack(side='left', fill='y')

        # Badge IA
        badge = ctk.CTkFrame(title_row, fg_color=C['mauve'], corner_radius=6,
                              width=32, height=24)
        badge.pack(side='left', pady=4)
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="IA", font=ctk.CTkFont(size=11, weight='bold'),
                     text_color='#000000').place(relx=0.5, rely=0.5, anchor='center')

        ctk.CTkLabel(title_row, text="Agente CRM",
                     font=ctk.CTkFont(size=22, weight='bold'),
                     text_color=C['heading']).pack(side='left', padx=(10, 0))

        self._lbl_estado = ctk.CTkLabel(title_row, text="● Activo",
                                         font=ctk.CTkFont(size=11),
                                         text_color=C['green'])
        self._lbl_estado.pack(side='left', padx=(12, 0), pady=(4, 0))

        # Controles lado derecho
        ctrl = ctk.CTkFrame(hdr, fg_color='transparent')
        ctrl.pack(side='right')

        # Selector backend: Claude | Ollama
        ctk.CTkLabel(ctrl, text="Motor:",
                     font=ctk.CTkFont(size=11), text_color=C['overlay2']).pack(side='left')

        self._seg_backend = ctk.CTkSegmentedButton(
            ctrl,
            values=['Claude', 'Ollama'],
            font=ctk.CTkFont(size=11), height=28,
            fg_color=C['surface1'],
            selected_color=C['mauve'],
            selected_hover_color=C['mauve'],
            unselected_color=C['surface1'],
            unselected_hover_color=C['surface2'],
            text_color=C['text'],
            command=self._cambiar_backend,
        )
        self._seg_backend.set('Claude')
        self._seg_backend.pack(side='left', padx=(4, 0))

        # Selector de modelo (cambia según backend)
        self._opt_modelo = ctk.CTkOptionMenu(
            ctrl,
            values=['Rápido (Haiku)', 'Avanzado (Sonnet)'],
            variable=self._modelo_var,
            width=160, height=28, corner_radius=6,
            fg_color=C['surface1'], button_color=C['surface2'],
            button_hover_color=C['surface1'],
            dropdown_fg_color=C['surface0'],
            text_color=C['text'], font=ctk.CTkFont(size=11),
            command=self._aplicar_modelo,
        )
        self._opt_modelo.set('Rápido (Haiku)')
        self._opt_modelo.pack(side='left', padx=(6, 0))

        ctk.CTkButton(ctrl, text="Limpiar", width=70, height=28, corner_radius=6,
                      fg_color='transparent', border_width=1,
                      border_color=C['border'], text_color=C['overlay2'],
                      font=ctk.CTkFont(size=11), hover_color=C['surface1'],
                      command=self._limpiar_chat).pack(side='left', padx=(8, 0))

        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=24, pady=12)

        # ── Acciones rápidas ──────────────────────────────────────────────────
        acc = ctk.CTkFrame(self, fg_color='transparent')
        acc.pack(fill='x', padx=24, pady=(0, 10))
        ctk.CTkLabel(acc, text="ACCIONES RÁPIDAS",
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=C['overlay2']).pack(anchor='w', pady=(0, 6))
        btns_row = ctk.CTkFrame(acc, fg_color='transparent')
        btns_row.pack(anchor='w')

        _ACC_COLORS = [C['mauve'], C['blue'], C['green'], C['amber']]
        for i, (label, prompt) in enumerate(_ACCIONES_RAPIDAS):
            col = _ACC_COLORS[i % len(_ACC_COLORS)]
            ctk.CTkButton(
                btns_row, text=label, width=108, height=30,
                corner_radius=6, fg_color=C['surface0'],
                hover_color=C['surface1'], border_width=1,
                border_color=col, text_color=col,
                font=ctk.CTkFont(size=11, weight='bold'),
                command=lambda p=prompt: self._enviar(p)
            ).pack(side='left', padx=(0, 6))

        # ── Conversación ──────────────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=C['surface0'],
            corner_radius=12, border_width=1, border_color=C['border'])
        self._scroll.pack(fill='both', expand=True, padx=24, pady=(0, 10))
        self._scroll.grid_columnconfigure(0, weight=1)
        self._scroll_row = 0

        # ── Input ─────────────────────────────────────────────────────────────
        input_frame = ctk.CTkFrame(self, fg_color=C['surface0'],
                                   corner_radius=12, border_width=1,
                                   border_color=C['border'])
        input_frame.pack(fill='x', padx=24, pady=(0, 16))
        input_frame.bind('<FocusIn>',  lambda e: input_frame.configure(border_color=C['mauve']))
        input_frame.bind('<FocusOut>', lambda e: input_frame.configure(border_color=C['border']))

        self._entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Escribe una instrucción o pregunta al agente...",
            height=44, corner_radius=10, border_width=0,
            fg_color='transparent',
            text_color=C['text'],
            placeholder_text_color=C['overlay2'],
            font=ctk.CTkFont(size=13)
        )
        self._entry.pack(side='left', fill='x', expand=True, padx=(12, 6), pady=6)
        self._entry.bind('<Return>', lambda e: self._enviar())
        self._entry.bind('<FocusIn>',  lambda e: input_frame.configure(border_color=C['mauve']))
        self._entry.bind('<FocusOut>', lambda e: input_frame.configure(border_color=C['border']))

        self._btn_enviar = ctk.CTkButton(
            input_frame, text="Enviar", width=90, height=36,
            corner_radius=8, fg_color=C['mauve'],
            hover_color='#A855F7', text_color='#FFFFFF',
            font=ctk.CTkFont(size=13, weight='bold'),
            command=self._enviar
        )
        self._btn_enviar.pack(side='right', padx=(0, 8), pady=6)

    # ── Inicialización ────────────────────────────────────────────────────────

    def _inicializar_engine(self):
        api_key = db.obtener_config('api_key') or ''
        self._engine = AgentEngine(
            api_key=api_key,
            modelo='haiku',
            backend='claude',
            on_tool_start=self._cb_tool_start,
            on_tool_done=self._cb_tool_done,
            on_datos_cambiados=self._cb_datos_cambiados,
        )
        if not api_key:
            self._lbl_estado.configure(text="● Sin API key", text_color=self.C['yellow'])
        # Detectar Ollama en background sin bloquear el arranque
        threading.Thread(target=self._detectar_ollama, daemon=True).start()

    def _detectar_ollama(self):
        if not ollama_disponible():
            return
        modelos = ollama_modelos()
        if not modelos:
            return
        def _actualizar():
            opciones_claude = ['Rápido (Haiku)', 'Avanzado (Sonnet)']
            opciones_ollama = [f"Ollama: {m}" for m in modelos[:6]]
            self._opt_modelo.configure(values=opciones_claude + opciones_ollama)
        self.after(0, _actualizar)

    def _cambiar_backend(self, valor: str):
        C = self.C
        if valor == 'Ollama':
            self._engine.backend = 'ollama'
            modelos = ollama_modelos()
            if modelos:
                opciones = [f"Ollama: {m}" for m in modelos[:6]]
                self._opt_modelo.configure(values=opciones)
                self._opt_modelo.set(opciones[0])
                self._engine.ollama_modelo = modelos[0]
            else:
                self._opt_modelo.configure(values=["Ollama no detectado"])
                self._opt_modelo.set("Ollama no detectado")
            self._lbl_estado.configure(text="● Ollama local", text_color=C['green'])
        else:
            self._engine.backend = 'claude'
            self._opt_modelo.configure(values=['Rápido (Haiku)', 'Avanzado (Sonnet)'])
            self._opt_modelo.set('Rápido (Haiku)')
            from modules.agent_engine import _MODELOS_CLAUDE
            self._engine.modelo = _MODELOS_CLAUDE['haiku']
            api_key = self._engine.api_key
            color   = C['green'] if (api_key and len(api_key) > 10) else C['yellow']
            texto   = "● Activo" if (api_key and len(api_key) > 10) else "● Sin API key"
            self._lbl_estado.configure(text=texto, text_color=color)

    def _aplicar_modelo(self, valor: str):
        from modules.agent_engine import _MODELOS_CLAUDE
        if valor.startswith('Ollama: '):
            self._engine.backend       = 'ollama'
            self._engine.ollama_modelo = valor[len('Ollama: '):]
            self._seg_backend.set('Ollama')
            self._lbl_estado.configure(
                text="● Ollama local", text_color=self.C['green'])
        elif 'Haiku' in valor:
            self._engine.backend = 'claude'
            self._engine.modelo  = _MODELOS_CLAUDE['haiku']
            self._seg_backend.set('Claude')
        elif 'Sonnet' in valor:
            self._engine.backend = 'claude'
            self._engine.modelo  = _MODELOS_CLAUDE['sonnet']
            self._seg_backend.set('Claude')

    # ── Enviar mensaje ────────────────────────────────────────────────────────

    def _enviar(self, texto: str = ''):
        if self._pensando:
            return
        msg = texto or self._entry.get().strip()
        if not msg:
            return
        self._entry.delete(0, 'end')

        self._agregar_burbuja_usuario(msg)
        self._iniciar_pensando()
        self._pensando = True
        self._btn_enviar.configure(state='disabled', text='...')
        self._grupo_herramientas = None

        def worker():
            try:
                respuesta = self._engine.ejecutar(msg, list(self._historial))
                self._historial.append({"role": "user",      "content": msg})
                self._historial.append({"role": "assistant", "content": respuesta})
                if len(self._historial) > 20:
                    self._historial = self._historial[-20:]
                self.after(0, lambda: self._mostrar_respuesta(respuesta))
            except RuntimeError as e:
                self.after(0, lambda: self._mostrar_error(str(e)))
            except Exception as e:
                self.after(0, lambda: self._mostrar_error(f"Error inesperado: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    # ── Callbacks herramientas (hilo secundario → hilo UI) ────────────────────

    def _cb_tool_start(self, nombre_legible: str):
        self.after(0, lambda: self._agregar_paso(nombre_legible, 'corriendo'))

    def _cb_tool_done(self, nombre_legible: str, ok: bool):
        self.after(0, lambda: self._actualizar_paso(nombre_legible, ok))

    def _cb_datos_cambiados(self):
        if self._on_datos_cambiados:
            self.after(0, self._on_datos_cambiados)

    # ── Renderizado ───────────────────────────────────────────────────────────

    def _mostrar_bienvenida(self):
        texto = (
            "Hola. Soy tu Agente CRM con acceso directo a tus datos.\n\n"
            "Puedo crear contactos, empresas y oportunidades, mover deals en el pipeline, "
            "registrar actividades y analizar tu CRM — todo desde aquí.\n\n"
            "Prueba: \"Crea un contacto para Juan López de TechEC\" o usa los botones de arriba."
        )
        self._agregar_burbuja_agente(texto)

    def _agregar_burbuja_usuario(self, texto: str):
        C = self.C
        outer = ctk.CTkFrame(self._scroll, fg_color='transparent')
        outer.grid(row=self._scroll_row, column=0, sticky='e', padx=(80, 12), pady=(6, 2))
        self._scroll_row += 1

        # Timestamp
        ctk.CTkLabel(outer, text=_ts(), font=ctk.CTkFont(size=9),
                     text_color=C['overlay2']).pack(anchor='e', padx=4, pady=(0, 2))

        burbuja = ctk.CTkFrame(outer, fg_color=C['surface1'],
                                corner_radius=14, border_width=1,
                                border_color=C['surface2'])
        burbuja.pack(anchor='e')
        ctk.CTkLabel(burbuja, text=texto, font=ctk.CTkFont(size=12),
                     text_color=C['text'], wraplength=380,
                     justify='left').pack(padx=14, pady=10)
        self._scroll_to_bottom()

    def _agregar_burbuja_agente(self, texto: str):
        C = self.C
        outer = ctk.CTkFrame(self._scroll, fg_color='transparent')
        outer.grid(row=self._scroll_row, column=0, sticky='w', padx=(12, 80), pady=(2, 6))
        self._scroll_row += 1

        row = ctk.CTkFrame(outer, fg_color='transparent')
        row.pack(anchor='w')

        # Avatar Aria
        av = ctk.CTkFrame(row, fg_color=C['mauve'], corner_radius=6,
                           width=28, height=28)
        av.pack(side='left', anchor='n', pady=(18, 0))
        av.pack_propagate(False)
        ctk.CTkLabel(av, text="A", font=ctk.CTkFont(size=11, weight='bold'),
                     text_color='#000000').place(relx=0.5, rely=0.5, anchor='center')

        right = ctk.CTkFrame(row, fg_color='transparent')
        right.pack(side='left', padx=(8, 0))

        # Nombre + timestamp
        meta = ctk.CTkFrame(right, fg_color='transparent')
        meta.pack(anchor='w', pady=(0, 2))
        ctk.CTkLabel(meta, text="Aria",
                     font=ctk.CTkFont(size=10, weight='bold'),
                     text_color=C['mauve']).pack(side='left')
        ctk.CTkLabel(meta, text=f"  {_ts()}",
                     font=ctk.CTkFont(size=9),
                     text_color=C['overlay2']).pack(side='left')

        # Burbuja con borde izquierdo mauve
        wrapper = ctk.CTkFrame(right, fg_color='transparent')
        wrapper.pack(anchor='w')

        accent_bar = ctk.CTkFrame(wrapper, fg_color=C['mauve'], width=3, corner_radius=2)
        accent_bar.pack(side='left', fill='y')

        burbuja = ctk.CTkFrame(wrapper, fg_color=C['crust'],
                                corner_radius=12, border_width=1,
                                border_color=C['surface1'])
        burbuja.pack(side='left')
        ctk.CTkLabel(burbuja, text=texto, font=ctk.CTkFont(size=12),
                     text_color=C['text'], wraplength=400,
                     justify='left').pack(padx=14, pady=10)
        self._scroll_to_bottom()

    # ── Pasos de herramientas ─────────────────────────────────────────────────

    def _asegurar_grupo_herramientas(self):
        """Crea o retorna el contenedor agrupado de pasos de herramientas."""
        if self._grupo_herramientas is None or not self._grupo_herramientas.winfo_exists():
            C = self.C
            outer = ctk.CTkFrame(self._scroll, fg_color='transparent')
            outer.grid(row=self._scroll_row, column=0, sticky='ew', padx=(48, 80), pady=(4, 4))
            self._scroll_row += 1

            grupo = ctk.CTkFrame(outer, fg_color=C['surface0'],
                                  corner_radius=8, border_width=1,
                                  border_color=C['border'])
            grupo.pack(fill='x')

            ctk.CTkLabel(grupo, text="Acciones del agente",
                         font=ctk.CTkFont(size=9, weight='bold'),
                         text_color=C['overlay2']).pack(anchor='w', padx=12, pady=(8, 4))

            self._grupo_herramientas = grupo
            self._grupo_contenido = ctk.CTkFrame(grupo, fg_color='transparent')
            self._grupo_contenido.pack(fill='x', padx=12, pady=(0, 8))

        return self._grupo_contenido

    def _agregar_paso(self, nombre: str, estado: str):
        C = self.C
        contenido = self._asegurar_grupo_herramientas()

        fila = ctk.CTkFrame(contenido, fg_color='transparent')
        fila.pack(fill='x', pady=1)

        lbl = ctk.CTkLabel(fila,
                            text=f"  ⟳  {nombre}",
                            font=ctk.CTkFont(size=11),
                            text_color=_COLOR_CORRIENDO,
                            anchor='w')
        lbl.pack(side='left')
        self._pasos_activos[nombre] = lbl
        self._scroll_to_bottom()

    def _actualizar_paso(self, nombre: str, ok: bool):
        lbl = self._pasos_activos.get(nombre)
        if lbl and lbl.winfo_exists():
            icono = '  ✓  ' if ok else '  ✗  '
            color = _COLOR_OK if ok else _COLOR_ERROR
            lbl.configure(text=f"{icono}{nombre}", text_color=color,
                          font=ctk.CTkFont(size=11))
        self._scroll_to_bottom()

    # ── Pensando animation ────────────────────────────────────────────────────

    def _iniciar_pensando(self):
        C = self.C
        self._pensando_frame = ctk.CTkFrame(self._scroll, fg_color='transparent')
        self._pensando_frame.grid(row=self._scroll_row, column=0, sticky='w',
                                   padx=(54, 80), pady=(4, 4))
        self._scroll_row += 1

        inner = ctk.CTkFrame(self._pensando_frame,
                              fg_color=C['surface0'],
                              corner_radius=10, border_width=1,
                              border_color=C['border'])
        inner.pack(anchor='w')

        self._pensando_lbl = ctk.CTkLabel(
            inner, text="Pensando   ",
            font=ctk.CTkFont(size=12),
            text_color=C['mauve'])
        self._pensando_lbl.pack(padx=14, pady=8)
        self._anim_paso = 0
        self._animar_pensando()
        self._scroll_to_bottom()

    def _animar_pensando(self):
        if not self._pensando:
            return
        frames = ['Pensando   ', 'Pensando .  ', 'Pensando .. ', 'Pensando ...']
        try:
            self._pensando_lbl.configure(text=frames[self._anim_paso % len(frames)])
        except Exception:
            return
        self._anim_paso += 1
        self._anim_id = self.after(380, self._animar_pensando)

    def _detener_pensando(self):
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        try:
            self._pensando_frame.destroy()
        except Exception:
            pass
        self._pensando = False
        self._btn_enviar.configure(state='normal', text='Enviar')

    def _mostrar_respuesta(self, texto: str):
        self._detener_pensando()
        self._grupo_herramientas = None
        self._agregar_burbuja_agente(texto)

    def _mostrar_error(self, texto: str):
        self._detener_pensando()
        C = self.C
        frame = ctk.CTkFrame(self._scroll, fg_color='transparent')
        frame.grid(row=self._scroll_row, column=0, sticky='ew', padx=24, pady=4)
        self._scroll_row += 1
        burbuja = ctk.CTkFrame(frame, fg_color='#1a0808', corner_radius=10,
                                border_width=1, border_color=C['red'])
        burbuja.pack(anchor='w')
        ctk.CTkLabel(burbuja, text=f"  ✗  {texto}",
                     font=ctk.CTkFont(size=11), text_color=C['red'],
                     wraplength=460, justify='left').pack(padx=12, pady=8)
        self._scroll_to_bottom()

    # ── Utilidades ────────────────────────────────────────────────────────────

    def _limpiar_chat(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        self._scroll_row = 0
        self._historial  = []
        self._pasos_activos.clear()
        self._grupo_herramientas = None
        self._mostrar_bienvenida()

    def _scroll_to_bottom(self):
        self.after(60, lambda: self._scroll._parent_canvas.yview_moveto(1.0))

    def actualizar_api_key(self, nueva_key: str):
        """Llamar desde ConfigPanel cuando el usuario guarda una nueva API key."""
        if self._engine:
            self._engine.api_key = nueva_key
        if nueva_key and len(nueva_key) > 10:
            self._lbl_estado.configure(text="● Activo", text_color=self.C['green'])
        else:
            self._lbl_estado.configure(text="● Sin API key", text_color=self.C['yellow'])
