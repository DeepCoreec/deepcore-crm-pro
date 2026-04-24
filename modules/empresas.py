"""DeepCore CRM Pro — Panel de Empresas."""
import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
import database as db
from modules.vista_empresa import VistaEmpresa

INDUSTRIAS = [
    'Tecnología', 'Comercio', 'Manufactura', 'Salud', 'Educación',
    'Construcción', 'Transporte', 'Finanzas', 'Servicios', 'Alimentación',
    'Agricultura', 'Turismo', 'Medios', 'Gobierno', 'Otro'
]


class EmpresasPanel(ctk.CTkFrame):
    def __init__(self, parent, C: dict):
        super().__init__(parent, fg_color='transparent')
        self.C = C
        self._sel_id: int | None = None
        self._build()
        self.cargar()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color='transparent')
        hdr.pack(fill='x', padx=24, pady=(20, 0))

        ctk.CTkLabel(hdr, text="Empresas",
                     font=ctk.CTkFont(size=22, weight='bold'),
                     text_color=self.C['heading']).pack(side='left')
        ctk.CTkLabel(hdr, text="Directorio de empresas y organizaciones",
                     font=ctk.CTkFont(size=12), text_color=self.C['overlay2']).pack(
                         side='left', padx=(12, 0), pady=(6, 0))

        acc = ctk.CTkFrame(hdr, fg_color='transparent')
        acc.pack(side='right')
        ctk.CTkButton(acc, text="Nueva empresa", width=140, height=34,
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
                      font=ctk.CTkFont(size=12), command=self._editar).pack(side='right', padx=(8, 0))
        ctk.CTkButton(acc, text="Ver 360°", width=80, height=34,
                      corner_radius=8, fg_color=self.C['surface0'],
                      hover_color=self.C['surface1'], text_color=self.C['accent'],
                      font=ctk.CTkFont(size=12), command=self._ver_empresa).pack(side='right')

        ctk.CTkFrame(self, fg_color=self.C['border'], height=1).pack(fill='x', padx=24, pady=12)

        # Búsqueda
        bar = ctk.CTkFrame(self, fg_color='transparent')
        bar.pack(fill='x', padx=24, pady=(0, 10))

        self._var_buscar = tk.StringVar()
        self._var_buscar.trace_add('write', lambda *_: self.cargar())
        entry = ctk.CTkEntry(bar, textvariable=self._var_buscar,
                             placeholder_text="Buscar por nombre, RUC o industria...",
                             width=300, height=36, corner_radius=8,
                             fg_color=self.C['surface0'], border_color=self.C['border'],
                             border_width=1, text_color=self.C['text'],
                             placeholder_text_color=self.C['overlay2'],
                             font=ctk.CTkFont(size=13))
        entry.pack(side='left')
        entry.bind('<FocusIn>',  lambda e: entry.configure(border_color=self.C['accent']))
        entry.bind('<FocusOut>', lambda e: entry.configure(border_color=self.C['border']))

        # Contador
        self._lbl_total = ctk.CTkLabel(bar, text="",
                                        font=ctk.CTkFont(size=12), text_color=self.C['text2'])
        self._lbl_total.pack(side='right')

        # Tabla
        frame_tabla = ctk.CTkFrame(self, fg_color=self.C['surface0'],
                                   corner_radius=12, border_width=1,
                                   border_color=self.C['border'])
        frame_tabla.pack(fill='both', expand=True, padx=24, pady=(0, 16))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('EMP.Treeview',
            background=self.C['surface0'], foreground=self.C['text'],
            fieldbackground=self.C['surface0'], rowheight=30, borderwidth=0,
            font=('Segoe UI', 11))
        style.configure('EMP.Treeview.Heading',
            background=self.C['mantle'], foreground=self.C['accent'],
            font=('Segoe UI', 11, 'bold'), relief='flat')
        style.map('EMP.Treeview',
            background=[('selected', self.C['surface1'])],
            foreground=[('selected', self.C['text'])])

        cols = ('nombre', 'ruc', 'industria', 'email', 'telefono', 'contactos', 'creado')
        self._tree = ttk.Treeview(frame_tabla, columns=cols, show='headings',
                                   style='EMP.Treeview', selectmode='browse')

        hdrs = {
            'nombre':    ('Empresa', 220), 'ruc':       ('RUC', 130),
            'industria': ('Industria', 130), 'email':   ('Email', 190),
            'telefono':  ('Teléfono', 120), 'contactos':('Contactos', 80),
            'creado':    ('Creado', 90),
        }
        for col, (txt, w) in hdrs.items():
            self._tree.heading(col, text=txt)
            self._tree.column(col, width=w, minwidth=50)

        vsb = ttk.Scrollbar(frame_tabla, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y', pady=8, padx=(0, 8))
        self._tree.pack(fill='both', expand=True, padx=8, pady=8)
        self._tree.bind('<<TreeviewSelect>>', self._on_select)
        self._tree.bind('<Double-1>', lambda e: self._ver_empresa())

        self._ids: list[int] = []

    def cargar(self):
        busq = self._var_buscar.get().strip()
        rows = db.listar_empresas(busqueda=busq)

        for item in self._tree.get_children():
            self._tree.delete(item)
        self._ids = []

        for r in rows:
            n_contactos = db.contar_contactos_empresa(r['id'])
            self._tree.insert('', 'end', values=(
                r.get('nombre', ''), r.get('ruc') or '—',
                r.get('industria') or '—', r.get('email') or '—',
                r.get('telefono') or '—', n_contactos,
                (r.get('created_at') or '')[:10]
            ))
            self._ids.append(r['id'])

        self._lbl_total.configure(text=f"{len(rows)} empresa(s)")
        self._sel_id = None

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if sel:
            idx = self._tree.index(sel[0])
            self._sel_id = self._ids[idx] if idx < len(self._ids) else None

    def _ver_empresa(self):
        if not self._sel_id:
            messagebox.showwarning("Sin selección", "Selecciona una empresa primero.", parent=self)
            return
        VistaEmpresa(self, self.C, empresa_id=self._sel_id)

    def _nueva(self):
        FormEmpresa(self, self.C, on_guardar=self.cargar)

    def _editar(self):
        if not self._sel_id:
            messagebox.showwarning("Sin selección", "Selecciona una empresa primero.", parent=self)
            return
        rows = db.listar_empresas()
        datos = next((r for r in rows if r['id'] == self._sel_id), None)
        if datos:
            FormEmpresa(self, self.C, datos=datos, on_guardar=self.cargar)

    def _eliminar(self):
        if not self._sel_id:
            messagebox.showwarning("Sin selección", "Selecciona una empresa primero.", parent=self)
            return
        rows = db.listar_empresas()
        emp = next((r for r in rows if r['id'] == self._sel_id), None)
        nombre = emp['nombre'] if emp else 'esta empresa'
        n = db.contar_contactos_empresa(self._sel_id)
        aviso = f"¿Eliminar '{nombre}'?"
        if n > 0:
            aviso += f"\n\nTiene {n} contacto(s) asociado(s). Los contactos quedarán sin empresa."
        if messagebox.askyesno("Confirmar", aviso, parent=self):
            db.eliminar_empresa(self._sel_id)
            self._sel_id = None
            self.cargar()


# ══════════════════════════════════════════════════════════════════════════════
#  FORMULARIO EMPRESA
# ══════════════════════════════════════════════════════════════════════════════

class FormEmpresa(ctk.CTkToplevel):
    def __init__(self, master, C: dict, datos: dict = None, on_guardar=None):
        super().__init__(master)
        self.C = C
        self.datos = datos
        self.on_guardar = on_guardar
        self._es_edicion = datos is not None

        self.title("Editar empresa" if self._es_edicion else "Nueva empresa")
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

        ctk.CTkLabel(self,
                     text="Editar empresa" if self._es_edicion else "Nueva empresa",
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=C['heading']).pack(pady=(20, 4), padx=24, anchor='w')
        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=24, pady=(0, 12))

        scroll = ctk.CTkScrollableFrame(self, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=24)

        d = self.datos or {}

        def campo(label, config_key, default='', ancho=460):
            ctk.CTkLabel(scroll, text=label, font=ctk.CTkFont(size=12, weight='bold'),
                         text_color=C['text2']).pack(anchor='w', pady=(8, 2))
            e = ctk.CTkEntry(scroll, width=ancho, height=36, corner_radius=8,
                             fg_color=C['surface0'], border_color=C['border'],
                             border_width=1, text_color=C['text'], font=ctk.CTkFont(size=13))
            e.insert(0, d.get(config_key, default))
            e.bind('<FocusIn>',  lambda ev: e.configure(border_color=C['accent']))
            e.bind('<FocusOut>', lambda ev: e.configure(border_color=C['border']))
            e.pack(anchor='w')
            return e

        self._e_nombre    = campo("Nombre de la empresa *", 'nombre')
        self._e_ruc       = campo("RUC / Número de identificación", 'ruc')

        # Industria
        ctk.CTkLabel(scroll, text="Industria", font=ctk.CTkFont(size=12, weight='bold'),
                     text_color=C['text2']).pack(anchor='w', pady=(8, 2))
        self._var_ind = tk.StringVar(value=d.get('industria') or INDUSTRIAS[0])
        ctk.CTkOptionMenu(scroll, values=INDUSTRIAS, variable=self._var_ind,
                          width=460, height=36, corner_radius=8, fg_color=C['surface0'],
                          button_color=C['surface1'], button_hover_color=C['surface2'],
                          dropdown_fg_color=C['surface0'], text_color=C['text'],
                          font=ctk.CTkFont(size=12)).pack(anchor='w')

        self._e_sitio = campo("Sitio web", 'sitio_web')
        self._e_email = campo("Email", 'email')
        self._e_tel   = campo("Teléfono", 'telefono')
        self._e_dir   = campo("Dirección", 'direccion')

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

        kwargs = dict(
            nombre=nombre,
            ruc=self._e_ruc.get().strip(),
            industria=self._var_ind.get(),
            sitio_web=self._e_sitio.get().strip(),
            email=self._e_email.get().strip(),
            telefono=self._e_tel.get().strip(),
            direccion=self._e_dir.get().strip(),
            notas=self._txt_notas.get('1.0', 'end-1c').strip()
        )

        if self._es_edicion:
            db.actualizar_empresa(self.datos['id'], **kwargs)
        else:
            db.crear_empresa(**kwargs)

        if self.on_guardar:
            self.on_guardar()
        self.destroy()
