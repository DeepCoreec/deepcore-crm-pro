"""DeepCore CRM Pro — Panel de Contactos."""
import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
import database as db


# ── Constantes de estado ──────────────────────────────────────────────────────
ESTADOS  = ['Activo', 'Inactivo', 'Lead', 'Cliente', 'Ex-cliente']
FUENTES  = ['Directo', 'Referido', 'Web', 'Redes Sociales', 'Email', 'Evento', 'Otro']


class ContactosPanel(ctk.CTkFrame):
    def __init__(self, parent, C: dict, on_nueva_actividad=None):
        super().__init__(parent, fg_color='transparent')
        self.C = C
        self.on_nueva_actividad = on_nueva_actividad
        self._sel_id: int | None = None
        self._build()
        self.cargar()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        # Cabecera
        hdr = ctk.CTkFrame(self, fg_color='transparent')
        hdr.pack(fill='x', padx=24, pady=(20, 0))

        ctk.CTkLabel(hdr, text="Contactos",
                     font=ctk.CTkFont(size=22, weight='bold'),
                     text_color=self.C['heading']).pack(side='left')
        ctk.CTkLabel(hdr, text="Gestión de clientes y prospectos",
                     font=ctk.CTkFont(size=12),
                     text_color=self.C['overlay2']).pack(side='left', padx=(12, 0), pady=(6, 0))

        # Acciones
        acc = ctk.CTkFrame(hdr, fg_color='transparent')
        acc.pack(side='right')
        ctk.CTkButton(acc, text="Nuevo contacto", width=140, height=34,
                      corner_radius=8, fg_color=self.C['green'],
                      hover_color=self.C['teal'], text_color='#000000',
                      font=ctk.CTkFont(size=13, weight='bold'),
                      command=self._nuevo).pack(side='right', padx=(8, 0))
        ctk.CTkButton(acc, text="Eliminar", width=90, height=34,
                      corner_radius=8, fg_color='transparent',
                      hover_color=self.C['red'], border_width=1,
                      border_color=self.C['red'], text_color=self.C['red'],
                      font=ctk.CTkFont(size=12),
                      command=self._eliminar).pack(side='right', padx=(8, 0))
        ctk.CTkButton(acc, text="Editar", width=80, height=34,
                      corner_radius=8, fg_color=self.C['surface1'],
                      hover_color=self.C['surface2'], text_color=self.C['text'],
                      font=ctk.CTkFont(size=12),
                      command=self._editar).pack(side='right')

        # Separador
        ctk.CTkFrame(self, fg_color=self.C['border'], height=1).pack(fill='x', padx=24, pady=12)

        # Barra de búsqueda + filtros
        bar = ctk.CTkFrame(self, fg_color='transparent')
        bar.pack(fill='x', padx=24, pady=(0, 10))

        self._var_buscar = tk.StringVar()
        self._var_buscar.trace_add('write', lambda *_: self.cargar())
        entry = ctk.CTkEntry(bar, textvariable=self._var_buscar,
                             placeholder_text="Buscar por nombre, email o teléfono...",
                             width=300, height=36, corner_radius=8,
                             fg_color=self.C['surface0'], border_color=self.C['border'],
                             border_width=1, text_color=self.C['text'],
                             placeholder_text_color=self.C['overlay2'],
                             font=ctk.CTkFont(size=13))
        entry.pack(side='left')
        entry.bind('<FocusIn>',  lambda e: entry.configure(border_color=self.C['accent']))
        entry.bind('<FocusOut>', lambda e: entry.configure(border_color=self.C['border']))

        self._var_estado = tk.StringVar(value='Todos')
        ctk.CTkOptionMenu(bar, values=['Todos'] + ESTADOS,
                          variable=self._var_estado,
                          width=130, height=36, corner_radius=8,
                          fg_color=self.C['surface0'],
                          button_color=self.C['surface1'],
                          button_hover_color=self.C['surface2'],
                          dropdown_fg_color=self.C['surface0'],
                          text_color=self.C['text'],
                          font=ctk.CTkFont(size=12),
                          command=lambda _: self.cargar()
                          ).pack(side='left', padx=(10, 0))

        # Tabla Treeview
        frame_tabla = ctk.CTkFrame(self, fg_color=self.C['surface0'],
                                   corner_radius=12, border_width=1,
                                   border_color=self.C['border'])
        frame_tabla.pack(fill='both', expand=True, padx=24, pady=(0, 16))

        self._style = ttk.Style()
        self._style.theme_use('clam')
        self._style.configure('CRM.Treeview',
            background=self.C['surface0'], foreground=self.C['text'],
            fieldbackground=self.C['surface0'], rowheight=30, borderwidth=0,
            font=('Segoe UI', 11))
        self._style.configure('CRM.Treeview.Heading',
            background=self.C['mantle'], foreground=self.C['accent'],
            font=('Segoe UI', 11, 'bold'), relief='flat')
        self._style.map('CRM.Treeview',
            background=[('selected', self.C['surface1'])],
            foreground=[('selected', self.C['text'])])

        cols = ('nombre', 'empresa', 'cargo', 'email', 'telefono', 'estado', 'creado')
        self._tree = ttk.Treeview(frame_tabla, columns=cols, show='headings',
                                   style='CRM.Treeview', selectmode='browse')

        hdrs = {'nombre': ('Nombre', 200), 'empresa': ('Empresa', 160),
                'cargo': ('Cargo', 130), 'email': ('Email', 190),
                'telefono': ('Teléfono', 120), 'estado': ('Estado', 90),
                'creado': ('Creado', 90)}
        for col, (txt, w) in hdrs.items():
            self._tree.heading(col, text=txt)
            self._tree.column(col, width=w, minwidth=60)

        vsb = ttk.Scrollbar(frame_tabla, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y', pady=8, padx=(0, 8))
        self._tree.pack(fill='both', expand=True, padx=8, pady=8)
        self._tree.bind('<<TreeviewSelect>>', self._on_select)
        self._tree.bind('<Double-1>', lambda e: self._editar())

        # Mapa id→row
        self._ids: list[int] = []

    # ── Datos ─────────────────────────────────────────────────────────────────

    def cargar(self):
        busq   = self._var_buscar.get().strip()
        estado = self._var_estado.get() if self._var_estado.get() != 'Todos' else ''
        rows   = db.listar_contactos(busqueda=busq, estado=estado)

        for item in self._tree.get_children():
            self._tree.delete(item)
        self._ids = []

        for r in rows:
            nombre = f"{r['nombre']} {r['apellido']}".strip()
            empresa = r.get('empresa_nombre') or '—'
            cargo   = r.get('cargo') or '—'
            email   = r.get('email') or '—'
            tel     = r.get('telefono') or '—'
            estado  = r.get('estado', 'Activo')
            creado  = (r.get('created_at') or '')[:10]
            self._tree.insert('', 'end', values=(nombre, empresa, cargo, email, tel, estado, creado))
            self._ids.append(r['id'])

        self._sel_id = None

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if sel:
            idx = self._tree.index(sel[0])
            self._sel_id = self._ids[idx] if idx < len(self._ids) else None

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _nuevo(self):
        FormContacto(self, self.C, on_guardar=self._on_guardado)

    def _editar(self):
        if not self._sel_id:
            messagebox.showwarning("Sin selección", "Selecciona un contacto primero.", parent=self)
            return
        datos = db.obtener_contacto(self._sel_id)
        if datos:
            FormContacto(self, self.C, datos=datos, on_guardar=self._on_guardado)

    def _eliminar(self):
        if not self._sel_id:
            messagebox.showwarning("Sin selección", "Selecciona un contacto primero.", parent=self)
            return
        c = db.obtener_contacto(self._sel_id)
        nombre = f"{c['nombre']} {c['apellido']}".strip() if c else 'este contacto'
        if messagebox.askyesno("Confirmar", f"¿Eliminar a {nombre}?\nEsta acción no se puede deshacer.", parent=self):
            db.eliminar_contacto(self._sel_id)
            self._sel_id = None
            self.cargar()

    def _on_guardado(self):
        self.cargar()


# ══════════════════════════════════════════════════════════════════════════════
#  FORMULARIO CONTACTO
# ══════════════════════════════════════════════════════════════════════════════

class FormContacto(ctk.CTkToplevel):
    def __init__(self, master, C: dict, datos: dict = None, on_guardar=None):
        super().__init__(master)
        self.C = C
        self.datos = datos
        self.on_guardar = on_guardar
        self._es_edicion = datos is not None

        titulo = "Editar contacto" if self._es_edicion else "Nuevo contacto"
        self.title(titulo)
        self.geometry("560x620")
        self.configure(fg_color=C['base'])
        self.resizable(False, False)
        self.grab_set()

        # Centrar en pantalla padre
        self.update_idletasks()
        px, py = master.winfo_rootx(), master.winfo_rooty()
        pw, ph = master.winfo_width(), master.winfo_height()
        self.geometry(f"+{px + pw//2 - 280}+{py + ph//2 - 310}")

        self._build()

    def _build(self):
        C = self.C

        # Franja de acento superior
        ctk.CTkFrame(self, fg_color=C['accent'], height=3).pack(fill='x')

        # Título
        ctk.CTkLabel(self, text="Nuevo contacto" if not self._es_edicion else "Editar contacto",
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=C['heading']).pack(pady=(20, 4), padx=24, anchor='w')
        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=24, pady=(0, 16))

        scroll = ctk.CTkScrollableFrame(self, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=24, pady=0)

        d = self.datos or {}

        def campo(label, default='', ancho=480):
            ctk.CTkLabel(scroll, text=label, font=ctk.CTkFont(size=12, weight='bold'),
                         text_color=C['text2']).pack(anchor='w', pady=(8, 2))
            e = ctk.CTkEntry(scroll, width=ancho, height=36, corner_radius=8,
                             fg_color=C['surface0'], border_color=C['border'],
                             border_width=1, text_color=C['text'],
                             font=ctk.CTkFont(size=13))
            e.insert(0, default)
            e.bind('<FocusIn>',  lambda ev: e.configure(border_color=C['accent']))
            e.bind('<FocusOut>', lambda ev: e.configure(border_color=C['border']))
            e.pack(anchor='w')
            return e

        def opcion(label, values, default=''):
            ctk.CTkLabel(scroll, text=label, font=ctk.CTkFont(size=12, weight='bold'),
                         text_color=C['text2']).pack(anchor='w', pady=(8, 2))
            var = tk.StringVar(value=default or values[0])
            om = ctk.CTkOptionMenu(scroll, values=values, variable=var, width=480, height=36,
                                   corner_radius=8, fg_color=C['surface0'],
                                   button_color=C['surface1'], button_hover_color=C['surface2'],
                                   dropdown_fg_color=C['surface0'], text_color=C['text'],
                                   font=ctk.CTkFont(size=12))
            om.pack(anchor='w')
            return var

        # Fila nombre + apellido
        fila = ctk.CTkFrame(scroll, fg_color='transparent')
        fila.pack(fill='x', pady=(8, 0))
        ctk.CTkLabel(fila, text="Nombre *", font=ctk.CTkFont(size=12, weight='bold'),
                     text_color=C['text2']).grid(row=0, column=0, sticky='w')
        ctk.CTkLabel(fila, text="Apellido", font=ctk.CTkFont(size=12, weight='bold'),
                     text_color=C['text2']).grid(row=0, column=1, sticky='w', padx=(16, 0))

        self._e_nombre = ctk.CTkEntry(fila, width=228, height=36, corner_radius=8,
                                      fg_color=C['surface0'], border_color=C['border'],
                                      border_width=1, text_color=C['text'], font=ctk.CTkFont(size=13))
        self._e_nombre.insert(0, d.get('nombre', ''))
        self._e_nombre.grid(row=1, column=0, sticky='w')
        self._e_nombre.bind('<FocusIn>',  lambda e: self._e_nombre.configure(border_color=C['accent']))
        self._e_nombre.bind('<FocusOut>', lambda e: self._e_nombre.configure(border_color=C['border']))

        self._e_apellido = ctk.CTkEntry(fila, width=228, height=36, corner_radius=8,
                                        fg_color=C['surface0'], border_color=C['border'],
                                        border_width=1, text_color=C['text'], font=ctk.CTkFont(size=13))
        self._e_apellido.insert(0, d.get('apellido', ''))
        self._e_apellido.grid(row=1, column=1, sticky='w', padx=(16, 0))
        self._e_apellido.bind('<FocusIn>',  lambda e: self._e_apellido.configure(border_color=C['accent']))
        self._e_apellido.bind('<FocusOut>', lambda e: self._e_apellido.configure(border_color=C['border']))

        self._e_cargo   = campo("Cargo",    d.get('cargo', ''))
        self._e_email   = campo("Email",    d.get('email', ''))
        self._e_tel     = campo("Teléfono", d.get('telefono', ''))

        # Empresa
        empresas_db = db.listar_empresas()
        emp_map     = {e['nombre']: e['id'] for e in empresas_db}
        emp_names   = ['— Sin empresa —'] + list(emp_map.keys())
        emp_def     = '— Sin empresa —'
        if d.get('empresa_nombre') and d['empresa_nombre'] in emp_map:
            emp_def = d['empresa_nombre']
        ctk.CTkLabel(scroll, text="Empresa", font=ctk.CTkFont(size=12, weight='bold'),
                     text_color=C['text2']).pack(anchor='w', pady=(8, 2))
        self._var_empresa = tk.StringVar(value=emp_def)
        self._emp_map = emp_map
        ctk.CTkOptionMenu(scroll, values=emp_names, variable=self._var_empresa,
                          width=480, height=36, corner_radius=8, fg_color=C['surface0'],
                          button_color=C['surface1'], button_hover_color=C['surface2'],
                          dropdown_fg_color=C['surface0'], text_color=C['text'],
                          font=ctk.CTkFont(size=12)).pack(anchor='w')

        self._var_estado = opcion("Estado", ESTADOS, d.get('estado', 'Activo'))
        self._var_fuente = opcion("Fuente",  FUENTES, d.get('fuente', 'Directo'))

        ctk.CTkLabel(scroll, text="Notas", font=ctk.CTkFont(size=12, weight='bold'),
                     text_color=C['text2']).pack(anchor='w', pady=(8, 2))
        self._txt_notas = ctk.CTkTextbox(scroll, width=480, height=80, corner_radius=8,
                                         fg_color=C['surface0'], border_color=C['border'],
                                         border_width=1, text_color=C['text'],
                                         font=ctk.CTkFont(size=12))
        self._txt_notas.pack(anchor='w')
        if d.get('notas'):
            self._txt_notas.insert('1.0', d['notas'])

        # Botones
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

        emp_nombre = self._var_empresa.get()
        empresa_id = self._emp_map.get(emp_nombre)

        kwargs = dict(
            nombre=nombre, apellido=self._e_apellido.get().strip(),
            empresa_id=empresa_id, cargo=self._e_cargo.get().strip(),
            email=self._e_email.get().strip(), telefono=self._e_tel.get().strip(),
            estado=self._var_estado.get(), fuente=self._var_fuente.get(),
            notas=self._txt_notas.get('1.0', 'end-1c').strip()
        )

        if self._es_edicion:
            db.actualizar_contacto(self.datos['id'], **kwargs)
        else:
            db.crear_contacto(**kwargs)

        if self.on_guardar:
            self.on_guardar()
        self.destroy()
