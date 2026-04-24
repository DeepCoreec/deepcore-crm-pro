"""DeepCore CRM Pro — Panel Pipeline de Oportunidades."""
import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
import database as db

ETAPAS = db.ETAPAS
COLOR_ETAPA = {
    'Prospecto':    '#60A5FA',
    'Calificado':   '#818CF8',
    'Propuesta':    '#F59E0B',
    'Negociación':  '#FB923C',
    'Ganado':       '#10B981',
    'Perdido':      '#EF4444',
}


class PipelinePanel(ctk.CTkFrame):
    def __init__(self, parent, C: dict):
        super().__init__(parent, fg_color='transparent')
        self.C = C
        self._sel_id: int | None = None
        self._build()
        self.cargar()

    def _build(self):
        # Cabecera
        hdr = ctk.CTkFrame(self, fg_color='transparent')
        hdr.pack(fill='x', padx=24, pady=(20, 0))

        ctk.CTkLabel(hdr, text="Pipeline de Ventas",
                     font=ctk.CTkFont(size=22, weight='bold'),
                     text_color=self.C['heading']).pack(side='left')
        ctk.CTkLabel(hdr, text="Seguimiento de oportunidades comerciales",
                     font=ctk.CTkFont(size=12), text_color=self.C['overlay2']).pack(
                         side='left', padx=(12, 0), pady=(6, 0))

        acc = ctk.CTkFrame(hdr, fg_color='transparent')
        acc.pack(side='right')
        ctk.CTkButton(acc, text="Nueva oportunidad", width=160, height=34,
                      corner_radius=8, fg_color=self.C['green'],
                      hover_color=self.C['teal'], text_color='#000000',
                      font=ctk.CTkFont(size=13, weight='bold'),
                      command=self._nueva).pack(side='right', padx=(8, 0))
        ctk.CTkButton(acc, text="Eliminar", width=90, height=34,
                      corner_radius=8, fg_color='transparent',
                      hover_color=self.C['red'], border_width=1,
                      border_color=self.C['red'], text_color=self.C['red'],
                      font=ctk.CTkFont(size=12), command=self._eliminar).pack(side='right', padx=(8, 0))
        ctk.CTkButton(acc, text="Editar", width=80, height=34,
                      corner_radius=8, fg_color=self.C['surface1'],
                      hover_color=self.C['surface2'], text_color=self.C['text'],
                      font=ctk.CTkFont(size=12), command=self._editar).pack(side='right')

        ctk.CTkFrame(self, fg_color=self.C['border'], height=1).pack(fill='x', padx=24, pady=12)

        # KPIs por etapa
        self._frame_kpis = ctk.CTkFrame(self, fg_color='transparent')
        self._frame_kpis.pack(fill='x', padx=24, pady=(0, 12))

        # Filtro + búsqueda
        bar = ctk.CTkFrame(self, fg_color='transparent')
        bar.pack(fill='x', padx=24, pady=(0, 10))

        self._var_buscar = tk.StringVar()
        self._var_buscar.trace_add('write', lambda *_: self.cargar())
        entry = ctk.CTkEntry(bar, textvariable=self._var_buscar,
                             placeholder_text="Buscar oportunidad, cliente o empresa...",
                             width=280, height=36, corner_radius=8,
                             fg_color=self.C['surface0'], border_color=self.C['border'],
                             border_width=1, text_color=self.C['text'],
                             placeholder_text_color=self.C['overlay2'],
                             font=ctk.CTkFont(size=13))
        entry.pack(side='left')
        entry.bind('<FocusIn>',  lambda e: entry.configure(border_color=self.C['accent']))
        entry.bind('<FocusOut>', lambda e: entry.configure(border_color=self.C['border']))

        self._var_etapa = tk.StringVar(value='Todas')
        ctk.CTkOptionMenu(bar, values=['Todas'] + ETAPAS,
                          variable=self._var_etapa, width=130, height=36,
                          corner_radius=8, fg_color=self.C['surface0'],
                          button_color=self.C['surface1'], button_hover_color=self.C['surface2'],
                          dropdown_fg_color=self.C['surface0'], text_color=self.C['text'],
                          font=ctk.CTkFont(size=12),
                          command=lambda _: self.cargar()).pack(side='left', padx=(10, 0))

        # Tabla
        frame_tabla = ctk.CTkFrame(self, fg_color=self.C['surface0'],
                                   corner_radius=12, border_width=1,
                                   border_color=self.C['border'])
        frame_tabla.pack(fill='both', expand=True, padx=24, pady=(0, 16))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('PP.Treeview',
            background=self.C['surface0'], foreground=self.C['text'],
            fieldbackground=self.C['surface0'], rowheight=30, borderwidth=0,
            font=('Segoe UI', 11))
        style.configure('PP.Treeview.Heading',
            background=self.C['mantle'], foreground=self.C['accent'],
            font=('Segoe UI', 11, 'bold'), relief='flat')
        style.map('PP.Treeview',
            background=[('selected', self.C['surface1'])],
            foreground=[('selected', self.C['text'])])

        cols = ('nombre', 'contacto', 'empresa', 'valor', 'etapa', 'prob', 'cierre', 'creado')
        self._tree = ttk.Treeview(frame_tabla, columns=cols, show='headings',
                                   style='PP.Treeview', selectmode='browse')

        hdrs = {
            'nombre':   ('Oportunidad', 200), 'contacto': ('Contacto', 150),
            'empresa':  ('Empresa', 140),      'valor':    ('Valor ($)', 100),
            'etapa':    ('Etapa', 110),         'prob':     ('Prob.', 60),
            'cierre':   ('Cierre esperado', 110),'creado':  ('Creado', 90),
        }
        for col, (txt, w) in hdrs.items():
            self._tree.heading(col, text=txt)
            self._tree.column(col, width=w, minwidth=50)

        vsb = ttk.Scrollbar(frame_tabla, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y', pady=8, padx=(0, 8))
        self._tree.pack(fill='both', expand=True, padx=8, pady=8)
        self._tree.bind('<<TreeviewSelect>>', self._on_select)
        self._tree.bind('<Double-1>', lambda e: self._editar())

        self._ids: list[int] = []

    def _build_kpis(self, stats: dict):
        for w in self._frame_kpis.winfo_children():
            w.destroy()

        # Configurar columnas uniformes
        for i in range(len(ETAPAS)):
            self._frame_kpis.columnconfigure(i, weight=1, uniform='kpi')

        for i, etapa in enumerate(ETAPAS):
            datos = stats.get('por_etapa', {}).get(etapa, {'n': 0, 'total': 0})
            color = COLOR_ETAPA.get(etapa, self.C['accent'])

            card = ctk.CTkFrame(self._frame_kpis, fg_color=self.C['surface0'],
                                corner_radius=10, border_width=1, border_color=self.C['border'])
            card.grid(row=0, column=i, padx=4, pady=0, sticky='nsew')

            ctk.CTkFrame(card, fg_color=color, height=3, corner_radius=2).pack(fill='x', padx=12, pady=(12, 6))
            ctk.CTkLabel(card, text=str(datos['n']),
                         font=ctk.CTkFont(size=22, weight='bold'),
                         text_color=color).pack()
            ctk.CTkLabel(card, text=etapa,
                         font=ctk.CTkFont(size=10),
                         text_color=self.C['text2']).pack(pady=(2, 8))

    # ── Datos ─────────────────────────────────────────────────────────────────

    def cargar(self):
        busq  = self._var_buscar.get().strip()
        etapa = self._var_etapa.get() if self._var_etapa.get() != 'Todas' else ''
        rows  = db.listar_oportunidades(etapa=etapa, busqueda=busq)
        stats = db.stats_pipeline()

        self._build_kpis(stats)

        for item in self._tree.get_children():
            self._tree.delete(item)
        self._ids = []

        moneda = db.get_config('moneda', '$')
        for r in rows:
            contacto = f"{r.get('contacto_nombre','') or ''} {r.get('contacto_apellido','') or ''}".strip() or '—'
            empresa  = r.get('empresa_nombre') or '—'
            valor    = f"{moneda}{r.get('valor',0):,.2f}"
            etapa_v  = r.get('etapa', '')
            prob     = f"{r.get('probabilidad',0)}%"
            cierre   = r.get('fecha_cierre', '') or '—'
            creado   = (r.get('created_at',''))[:10]
            self._tree.insert('', 'end', values=(r['nombre'], contacto, empresa, valor, etapa_v, prob, cierre, creado))
            self._ids.append(r['id'])

        self._sel_id = None

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if sel:
            idx = self._tree.index(sel[0])
            self._sel_id = self._ids[idx] if idx < len(self._ids) else None

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _nueva(self):
        FormOportunidad(self, self.C, on_guardar=self.cargar)

    def _editar(self):
        if not self._sel_id:
            messagebox.showwarning("Sin selección", "Selecciona una oportunidad primero.", parent=self)
            return
        rows = db.listar_oportunidades()
        datos = next((r for r in rows if r['id'] == self._sel_id), None)
        if datos:
            FormOportunidad(self, self.C, datos=datos, on_guardar=self.cargar)

    def _eliminar(self):
        if not self._sel_id:
            messagebox.showwarning("Sin selección", "Selecciona una oportunidad primero.", parent=self)
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar esta oportunidad?", parent=self):
            db.eliminar_oportunidad(self._sel_id)
            self._sel_id = None
            self.cargar()


# ══════════════════════════════════════════════════════════════════════════════
#  FORMULARIO OPORTUNIDAD
# ══════════════════════════════════════════════════════════════════════════════

class FormOportunidad(ctk.CTkToplevel):
    def __init__(self, master, C: dict, datos: dict = None, on_guardar=None):
        super().__init__(master)
        self.C = C
        self.datos = datos
        self.on_guardar = on_guardar
        self._es_edicion = datos is not None

        self.title("Editar oportunidad" if self._es_edicion else "Nueva oportunidad")
        self.geometry("520x580")
        self.configure(fg_color=C['base'])
        self.resizable(False, False)
        self.grab_set()

        self.update_idletasks()
        px, py = master.winfo_rootx(), master.winfo_rooty()
        pw, ph = master.winfo_width(), master.winfo_height()
        self.geometry(f"+{px + pw//2 - 260}+{py + ph//2 - 290}")

        self._build()

    def _build(self):
        C = self.C
        ctk.CTkFrame(self, fg_color=C['accent'], height=3).pack(fill='x')

        ctk.CTkLabel(self, text="Nueva oportunidad" if not self._es_edicion else "Editar oportunidad",
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=C['heading']).pack(pady=(20, 4), padx=24, anchor='w')
        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=24, pady=(0, 12))

        scroll = ctk.CTkScrollableFrame(self, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=24)

        d = self.datos or {}

        def campo(label, default='', ancho=460):
            ctk.CTkLabel(scroll, text=label, font=ctk.CTkFont(size=12, weight='bold'),
                         text_color=C['text2']).pack(anchor='w', pady=(8, 2))
            e = ctk.CTkEntry(scroll, width=ancho, height=36, corner_radius=8,
                             fg_color=C['surface0'], border_color=C['border'],
                             border_width=1, text_color=C['text'], font=ctk.CTkFont(size=13))
            e.insert(0, default)
            e.bind('<FocusIn>',  lambda ev: e.configure(border_color=C['accent']))
            e.bind('<FocusOut>', lambda ev: e.configure(border_color=C['border']))
            e.pack(anchor='w')
            return e

        def opcion(label, values, default=''):
            ctk.CTkLabel(scroll, text=label, font=ctk.CTkFont(size=12, weight='bold'),
                         text_color=C['text2']).pack(anchor='w', pady=(8, 2))
            var = tk.StringVar(value=default or values[0])
            ctk.CTkOptionMenu(scroll, values=values, variable=var, width=460, height=36,
                              corner_radius=8, fg_color=C['surface0'],
                              button_color=C['surface1'], button_hover_color=C['surface2'],
                              dropdown_fg_color=C['surface0'], text_color=C['text'],
                              font=ctk.CTkFont(size=12)).pack(anchor='w')
            return var

        self._e_nombre  = campo("Nombre de la oportunidad *", d.get('nombre', ''))
        self._e_valor   = campo("Valor estimado ($)", str(d.get('valor', '0')), ancho=220)

        # Etapa
        self._var_etapa = opcion("Etapa", ETAPAS, d.get('etapa', 'Prospecto'))

        # Contacto
        contactos_db = db.listar_contactos()
        cont_map = {f"{r['nombre']} {r['apellido']}".strip(): r['id'] for r in contactos_db}
        cont_names = ['— Sin contacto —'] + list(cont_map.keys())
        cont_def = '— Sin contacto —'
        if d.get('contacto_nombre'):
            nombre_c = f"{d.get('contacto_nombre','')} {d.get('contacto_apellido','')}".strip()
            if nombre_c in cont_map:
                cont_def = nombre_c
        self._var_contacto = opcion("Contacto", cont_names, cont_def)
        self._cont_map = cont_map

        # Empresa
        empresas_db = db.listar_empresas()
        emp_map = {e['nombre']: e['id'] for e in empresas_db}
        emp_names = ['— Sin empresa —'] + list(emp_map.keys())
        emp_def = d.get('empresa_nombre') if d.get('empresa_nombre') in emp_map else '— Sin empresa —'
        self._var_empresa = opcion("Empresa", emp_names, emp_def)
        self._emp_map = emp_map

        self._e_cierre = campo("Fecha de cierre esperada (YYYY-MM-DD)", d.get('fecha_cierre', ''))

        ctk.CTkLabel(scroll, text="Notas", font=ctk.CTkFont(size=12, weight='bold'),
                     text_color=C['text2']).pack(anchor='w', pady=(8, 2))
        self._txt_notas = ctk.CTkTextbox(scroll, width=460, height=70, corner_radius=8,
                                         fg_color=C['surface0'], border_color=C['border'],
                                         border_width=1, text_color=C['text'],
                                         font=ctk.CTkFont(size=12))
        self._txt_notas.pack(anchor='w')
        if d.get('notas'):
            self._txt_notas.insert('1.0', d['notas'])

        btns = ctk.CTkFrame(self, fg_color='transparent')
        btns.pack(fill='x', padx=24, pady=16)
        ctk.CTkButton(btns, text="Cancelar", width=110, height=38, corner_radius=8,
                      fg_color=C['surface1'], hover_color=C['surface2'],
                      text_color=C['text'], font=ctk.CTkFont(size=13),
                      command=self.destroy).pack(side='right', padx=(8, 0))
        ctk.CTkButton(btns, text="Guardar", width=130, height=38, corner_radius=8,
                      fg_color=C['green'], hover_color=C['teal'],
                      text_color='#000000', font=ctk.CTkFont(size=13, weight='bold'),
                      command=self._guardar).pack(side='right')

    def _guardar(self):
        nombre = self._e_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Campo requerido", "El nombre es obligatorio.", parent=self)
            return
        try:
            valor = float(self._e_valor.get().replace(',', '.') or '0')
        except ValueError:
            messagebox.showwarning("Valor inválido", "Ingresa un número válido.", parent=self)
            return

        contacto_id = self._cont_map.get(self._var_contacto.get())
        empresa_id  = self._emp_map.get(self._var_empresa.get())

        kwargs = dict(
            nombre=nombre, contacto_id=contacto_id, empresa_id=empresa_id,
            valor=valor, etapa=self._var_etapa.get(),
            fecha_cierre=self._e_cierre.get().strip(),
            notas=self._txt_notas.get('1.0', 'end-1c').strip()
        )

        if self._es_edicion:
            db.actualizar_oportunidad(self.datos['id'], **kwargs)
        else:
            db.crear_oportunidad(**kwargs)

        if self.on_guardar:
            self.on_guardar()
        self.destroy()
