"""DeepCore CRM Pro — Panel de Actividades e Historial."""
import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from datetime import datetime
import database as db

TIPOS = db.TIPOS_ACTIVIDAD
ICONO_TIPO = {
    'Nota':     'N',
    'Llamada':  'L',
    'Email':    'E',
    'Reunión':  'R',
    'Tarea':    'T',
}
COLOR_TIPO = {
    'Nota':     '#818CF8',
    'Llamada':  '#60A5FA',
    'Email':    '#10B981',
    'Reunión':  '#F59E0B',
    'Tarea':    '#FB923C',
}


class ActividadesPanel(ctk.CTkFrame):
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

        ctk.CTkLabel(hdr, text="Actividades",
                     font=ctk.CTkFont(size=22, weight='bold'),
                     text_color=self.C['heading']).pack(side='left')
        ctk.CTkLabel(hdr, text="Historial de interacciones con clientes",
                     font=ctk.CTkFont(size=12), text_color=self.C['overlay2']).pack(
                         side='left', padx=(12, 0), pady=(6, 0))

        acc = ctk.CTkFrame(hdr, fg_color='transparent')
        acc.pack(side='right')
        ctk.CTkButton(acc, text="Nueva actividad", width=150, height=34,
                      corner_radius=8, fg_color=self.C['green'],
                      hover_color=self.C['teal'], text_color='#000000',
                      font=ctk.CTkFont(size=13, weight='bold'),
                      command=self._nueva).pack(side='right', padx=(8, 0))
        ctk.CTkButton(acc, text="Completar", width=90, height=34,
                      corner_radius=8, fg_color=self.C['surface1'],
                      hover_color=self.C['surface2'], text_color=self.C['text'],
                      font=ctk.CTkFont(size=12),
                      command=self._completar).pack(side='right', padx=(8, 0))
        ctk.CTkButton(acc, text="Eliminar", width=80, height=34,
                      corner_radius=8, fg_color='transparent',
                      hover_color=self.C['red'], border_width=1,
                      border_color=self.C['red'], text_color=self.C['red'],
                      font=ctk.CTkFont(size=12), command=self._eliminar).pack(side='right')

        ctk.CTkFrame(self, fg_color=self.C['border'], height=1).pack(fill='x', padx=24, pady=12)

        # Filtros
        bar = ctk.CTkFrame(self, fg_color='transparent')
        bar.pack(fill='x', padx=24, pady=(0, 10))

        self._var_tipo = tk.StringVar(value='Todos')
        ctk.CTkLabel(bar, text="TIPO", font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=self.C['overlay2']).pack(side='left', padx=(0, 6))
        ctk.CTkOptionMenu(bar, values=['Todos'] + TIPOS,
                          variable=self._var_tipo, width=130, height=36,
                          corner_radius=8, fg_color=self.C['surface0'],
                          button_color=self.C['surface1'], button_hover_color=self.C['surface2'],
                          dropdown_fg_color=self.C['surface0'], text_color=self.C['text'],
                          font=ctk.CTkFont(size=12),
                          command=lambda _: self.cargar()).pack(side='left')

        self._var_estado = tk.StringVar(value='Pendientes')
        ctk.CTkLabel(bar, text="ESTADO", font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=self.C['overlay2']).pack(side='left', padx=(16, 6))
        ctk.CTkOptionMenu(bar, values=['Todas', 'Pendientes', 'Completadas'],
                          variable=self._var_estado, width=130, height=36,
                          corner_radius=8, fg_color=self.C['surface0'],
                          button_color=self.C['surface1'], button_hover_color=self.C['surface2'],
                          dropdown_fg_color=self.C['surface0'], text_color=self.C['text'],
                          font=ctk.CTkFont(size=12),
                          command=lambda _: self.cargar()).pack(side='left')

        # Tabla
        frame_tabla = ctk.CTkFrame(self, fg_color=self.C['surface0'],
                                   corner_radius=12, border_width=1,
                                   border_color=self.C['border'])
        frame_tabla.pack(fill='both', expand=True, padx=24, pady=(0, 16))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('ACT.Treeview',
            background=self.C['surface0'], foreground=self.C['text'],
            fieldbackground=self.C['surface0'], rowheight=30, borderwidth=0,
            font=('Segoe UI', 11))
        style.configure('ACT.Treeview.Heading',
            background=self.C['mantle'], foreground=self.C['accent'],
            font=('Segoe UI', 11, 'bold'), relief='flat')
        style.map('ACT.Treeview',
            background=[('selected', self.C['surface1'])],
            foreground=[('selected', self.C['text'])])

        cols = ('tipo', 'titulo', 'contacto', 'oportunidad', 'fecha', 'estado')
        self._tree = ttk.Treeview(frame_tabla, columns=cols, show='headings',
                                   style='ACT.Treeview', selectmode='browse')

        hdrs = {
            'tipo':        ('Tipo', 90),
            'titulo':      ('Título', 220),
            'contacto':    ('Contacto', 160),
            'oportunidad': ('Oportunidad', 160),
            'fecha':       ('Fecha', 140),
            'estado':      ('Estado', 90),
        }
        for col, (txt, w) in hdrs.items():
            self._tree.heading(col, text=txt)
            self._tree.column(col, width=w, minwidth=50)

        vsb = ttk.Scrollbar(frame_tabla, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y', pady=8, padx=(0, 8))
        self._tree.pack(fill='both', expand=True, padx=8, pady=8)
        self._tree.bind('<<TreeviewSelect>>', self._on_select)

        self._ids: list[int] = []

    def cargar(self):
        tipo   = self._var_tipo.get() if self._var_tipo.get() != 'Todos' else ''
        estado = self._var_estado.get()
        comp   = -1
        if estado == 'Pendientes':
            comp = 0
        elif estado == 'Completadas':
            comp = 1

        rows = db.listar_actividades(tipo=tipo, completada=comp)

        for item in self._tree.get_children():
            self._tree.delete(item)
        self._ids = []

        for r in rows:
            contacto   = f"{r.get('contacto_nombre','') or ''} {r.get('contacto_apellido','') or ''}".strip() or '—'
            oportunidad= r.get('oportunidad_nombre') or '—'
            fecha      = r.get('fecha', '')[:16] if r.get('fecha') else '—'
            estado_v   = 'Completada' if r.get('completada') else 'Pendiente'
            self._tree.insert('', 'end',
                              values=(r.get('tipo',''), r.get('titulo',''), contacto,
                                      oportunidad, fecha, estado_v))
            self._ids.append(r['id'])

        self._sel_id = None

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if sel:
            idx = self._tree.index(sel[0])
            self._sel_id = self._ids[idx] if idx < len(self._ids) else None

    def _nueva(self):
        FormActividad(self, self.C, on_guardar=self.cargar)

    def _completar(self):
        if not self._sel_id:
            messagebox.showwarning("Sin selección", "Selecciona una actividad primero.", parent=self)
            return
        db.completar_actividad(self._sel_id)
        self.cargar()

    def _eliminar(self):
        if not self._sel_id:
            messagebox.showwarning("Sin selección", "Selecciona una actividad primero.", parent=self)
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar esta actividad?", parent=self):
            db.eliminar_actividad(self._sel_id)
            self._sel_id = None
            self.cargar()


# ══════════════════════════════════════════════════════════════════════════════
#  FORMULARIO ACTIVIDAD
# ══════════════════════════════════════════════════════════════════════════════

class FormActividad(ctk.CTkToplevel):
    def __init__(self, master, C: dict, contacto_id: int = None,
                 oportunidad_id: int = None, on_guardar=None):
        super().__init__(master)
        self.C = C
        self.on_guardar = on_guardar
        self._contacto_id_fijo = contacto_id
        self._oportunidad_id_fijo = oportunidad_id

        self.title("Nueva actividad")
        self.geometry("500x520")
        self.configure(fg_color=C['base'])
        self.resizable(False, False)
        self.grab_set()

        self.update_idletasks()
        px, py = master.winfo_rootx(), master.winfo_rooty()
        pw, ph = master.winfo_width(), master.winfo_height()
        self.geometry(f"+{px + pw//2 - 250}+{py + ph//2 - 260}")

        self._build()

    def _build(self):
        C = self.C
        ctk.CTkFrame(self, fg_color=C['accent'], height=3).pack(fill='x')

        ctk.CTkLabel(self, text="Nueva actividad",
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=C['heading']).pack(pady=(20, 4), padx=24, anchor='w')
        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=24, pady=(0, 12))

        scroll = ctk.CTkScrollableFrame(self, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=24)

        def opcion(label, values, default=''):
            ctk.CTkLabel(scroll, text=label, font=ctk.CTkFont(size=12, weight='bold'),
                         text_color=C['text2']).pack(anchor='w', pady=(8, 2))
            var = tk.StringVar(value=default or values[0])
            ctk.CTkOptionMenu(scroll, values=values, variable=var, width=440, height=36,
                              corner_radius=8, fg_color=C['surface0'],
                              button_color=C['surface1'], button_hover_color=C['surface2'],
                              dropdown_fg_color=C['surface0'], text_color=C['text'],
                              font=ctk.CTkFont(size=12)).pack(anchor='w')
            return var

        def campo(label, default=''):
            ctk.CTkLabel(scroll, text=label, font=ctk.CTkFont(size=12, weight='bold'),
                         text_color=C['text2']).pack(anchor='w', pady=(8, 2))
            e = ctk.CTkEntry(scroll, width=440, height=36, corner_radius=8,
                             fg_color=C['surface0'], border_color=C['border'],
                             border_width=1, text_color=C['text'], font=ctk.CTkFont(size=13))
            e.insert(0, default)
            e.bind('<FocusIn>',  lambda ev: e.configure(border_color=C['accent']))
            e.bind('<FocusOut>', lambda ev: e.configure(border_color=C['border']))
            e.pack(anchor='w')
            return e

        self._var_tipo = opcion("Tipo de actividad", TIPOS)
        self._e_titulo = campo("Título *")
        self._e_fecha  = campo("Fecha y hora (YYYY-MM-DD HH:MM)",
                               datetime.now().strftime('%Y-%m-%d %H:%M'))

        # Contacto
        contactos_db = db.listar_contactos()
        cont_map  = {f"{r['nombre']} {r['apellido']}".strip(): r['id'] for r in contactos_db}
        cont_names = ['— Sin contacto —'] + list(cont_map.keys())
        cont_def   = '— Sin contacto —'
        if self._contacto_id_fijo:
            c = next((r for r in contactos_db if r['id'] == self._contacto_id_fijo), None)
            if c:
                cont_def = f"{c['nombre']} {c['apellido']}".strip()
        self._var_contacto = opcion("Contacto", cont_names, cont_def)
        self._cont_map = cont_map

        # Oportunidad
        ops_db  = db.listar_oportunidades()
        ops_map  = {r['nombre']: r['id'] for r in ops_db}
        ops_names = ['— Sin oportunidad —'] + list(ops_map.keys())
        self._var_op = opcion("Oportunidad", ops_names)
        self._ops_map = ops_map

        ctk.CTkLabel(scroll, text="Descripción", font=ctk.CTkFont(size=12, weight='bold'),
                     text_color=C['text2']).pack(anchor='w', pady=(8, 2))
        self._txt_desc = ctk.CTkTextbox(scroll, width=440, height=90, corner_radius=8,
                                        fg_color=C['surface0'], border_color=C['border'],
                                        border_width=1, text_color=C['text'],
                                        font=ctk.CTkFont(size=12))
        self._txt_desc.pack(anchor='w')

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
        titulo = self._e_titulo.get().strip()
        if not titulo:
            messagebox.showwarning("Campo requerido", "El título es obligatorio.", parent=self)
            return
        contacto_id   = self._cont_map.get(self._var_contacto.get()) or self._contacto_id_fijo
        oportunidad_id = self._ops_map.get(self._var_op.get()) or self._oportunidad_id_fijo
        db.crear_actividad(
            tipo=self._var_tipo.get(),
            titulo=titulo,
            descripcion=self._txt_desc.get('1.0', 'end-1c').strip(),
            contacto_id=contacto_id,
            oportunidad_id=oportunidad_id,
            fecha=self._e_fecha.get().strip() or None
        )
        if self.on_guardar:
            self.on_guardar()
        self.destroy()
