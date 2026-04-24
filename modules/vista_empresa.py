"""DeepCore CRM Pro — Vista 360° de una empresa (contactos + oportunidades)."""
import customtkinter as ctk
from tkinter import ttk
import tkinter as tk
import database as db

ETAPA_COLORES = {
    'Prospecto':   '#60A5FA',
    'Calificado':  '#818CF8',
    'Propuesta':   '#F59E0B',
    'Negociación': '#FB923C',
    'Ganado':      '#10B981',
    'Perdido':     '#EF4444',
}


class VistaEmpresa(ctk.CTkToplevel):
    """Modal 360° que muestra contactos y oportunidades de una empresa."""

    def __init__(self, master, C: dict, empresa_id: int):
        super().__init__(master)
        self.C = C
        self._emp_id = empresa_id

        emp_rows = db.listar_empresas()
        self._emp = next((e for e in emp_rows if e['id'] == empresa_id), {})

        nombre = self._emp.get('nombre', 'Empresa')
        self.title(f"Vista — {nombre}")
        self.geometry("760x560")
        self.configure(fg_color=C['base'])
        self.resizable(True, True)
        self.grab_set()

        px, py = master.winfo_rootx(), master.winfo_rooty()
        pw, ph = master.winfo_width(), master.winfo_height()
        self.geometry(f"+{max(0, px + pw//2 - 380)}+{max(0, py + ph//2 - 280)}")

        self._build()
        self._cargar()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        C = self.C
        emp = self._emp

        # Franja de color
        ctk.CTkFrame(self, fg_color=C['accent'], height=3).pack(fill='x')

        # Cabecera empresa
        hdr = ctk.CTkFrame(self, fg_color=C['surface0'], corner_radius=0)
        hdr.pack(fill='x')

        info_col = ctk.CTkFrame(hdr, fg_color='transparent')
        info_col.pack(side='left', padx=24, pady=16, fill='x', expand=True)

        ctk.CTkLabel(info_col,
                     text=emp.get('nombre', '—'),
                     font=ctk.CTkFont(size=20, weight='bold'),
                     text_color=C['heading']).pack(anchor='w')

        meta = '  ·  '.join(filter(None, [
            emp.get('industria') or '',
            emp.get('ruc') or '',
            emp.get('email') or '',
            emp.get('telefono') or '',
        ]))
        if meta:
            ctk.CTkLabel(info_col, text=meta,
                         font=ctk.CTkFont(size=11),
                         text_color=C['overlay2']).pack(anchor='w', pady=(2, 0))

        # KPIs rápidos en cabecera
        kpi_col = ctk.CTkFrame(hdr, fg_color='transparent')
        kpi_col.pack(side='right', padx=24, pady=12)

        self._lbl_kpi_contactos = self._kpi_widget(kpi_col, '—', 'Contactos', C['accent'])
        self._lbl_kpi_opor      = self._kpi_widget(kpi_col, '—', 'Oportunidades', C['blue'])
        self._lbl_kpi_pipeline  = self._kpi_widget(kpi_col, '—', 'Pipeline', C['green'])

        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x')

        # Tabs
        tab_bar = ctk.CTkFrame(self, fg_color='transparent')
        tab_bar.pack(fill='x', padx=24, pady=(12, 0))

        self._tab_btns: dict[str, ctk.CTkButton] = {}
        for label in ('Contactos', 'Oportunidades'):
            btn = ctk.CTkButton(tab_bar, text=label, width=130, height=32, corner_radius=8,
                                fg_color='transparent', hover_color=C['surface1'],
                                text_color=C['text2'], font=ctk.CTkFont(size=12),
                                command=lambda l=label: self._cambiar_tab(l))
            btn.pack(side='left', padx=(0, 6))
            self._tab_btns[label] = btn

        # Contenedor de tabs
        self._contenedor = ctk.CTkFrame(self, fg_color='transparent')
        self._contenedor.pack(fill='both', expand=True, padx=24, pady=8)

        # Panel Contactos
        self._panel_contactos = self._build_tabla_contactos()
        # Panel Oportunidades
        self._panel_opor = self._build_tabla_opor()

        self._cambiar_tab('Contactos')

    def _kpi_widget(self, parent, valor, etiqueta, color):
        f = ctk.CTkFrame(parent, fg_color='transparent')
        f.pack(side='left', padx=12)
        lbl_val = ctk.CTkLabel(f, text=valor,
                                font=ctk.CTkFont(size=22, weight='bold'),
                                text_color=color)
        lbl_val.pack()
        ctk.CTkLabel(f, text=etiqueta,
                     font=ctk.CTkFont(size=10), text_color=self.C['overlay2']).pack()
        return lbl_val

    def _estilo_tree(self, style_name: str):
        C = self.C
        s = ttk.Style()
        s.theme_use('clam')
        s.configure(style_name,
                    background=C['surface0'], foreground=C['text'],
                    fieldbackground=C['surface0'], rowheight=28, borderwidth=0,
                    font=('Segoe UI', 11))
        s.configure(f'{style_name}.Heading',
                    background=C['mantle'], foreground=C['accent'],
                    font=('Segoe UI', 11, 'bold'), relief='flat')
        s.map(style_name,
              background=[('selected', C['surface1'])],
              foreground=[('selected', C['text'])])

    def _build_tabla_contactos(self) -> ctk.CTkFrame:
        C = self.C
        frame = ctk.CTkFrame(self._contenedor, fg_color=C['surface0'],
                             corner_radius=10, border_width=1, border_color=C['border'])
        self._estilo_tree('VE_CTK.Treeview')
        cols = ('nombre', 'cargo', 'email', 'telefono', 'estado')
        tree = ttk.Treeview(frame, columns=cols, show='headings',
                            style='VE_CTK.Treeview', selectmode='browse')
        hdrs = {'nombre': ('Nombre', 180), 'cargo': ('Cargo', 130),
                'email': ('Email', 170), 'telefono': ('Teléfono', 110),
                'estado': ('Estado', 90)}
        for col, (txt, w) in hdrs.items():
            tree.heading(col, text=txt)
            tree.column(col, width=w, minwidth=50)
        vsb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y', pady=6, padx=(0, 6))
        tree.pack(fill='both', expand=True, padx=6, pady=6)
        self._tree_contactos = tree
        return frame

    def _build_tabla_opor(self) -> ctk.CTkFrame:
        C = self.C
        frame = ctk.CTkFrame(self._contenedor, fg_color=C['surface0'],
                             corner_radius=10, border_width=1, border_color=C['border'])
        self._estilo_tree('VE_OPR.Treeview')
        cols = ('nombre', 'contacto', 'etapa', 'valor', 'cierre')
        tree = ttk.Treeview(frame, columns=cols, show='headings',
                            style='VE_OPR.Treeview', selectmode='browse')
        hdrs = {'nombre': ('Oportunidad', 180), 'contacto': ('Contacto', 140),
                'etapa': ('Etapa', 110), 'valor': ('Valor', 90), 'cierre': ('Cierre', 90)}
        for col, (txt, w) in hdrs.items():
            tree.heading(col, text=txt)
            tree.column(col, width=w, minwidth=40)
        vsb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y', pady=6, padx=(0, 6))
        tree.pack(fill='both', expand=True, padx=6, pady=6)
        self._tree_opor = tree
        return frame

    # ── Navegación tabs ───────────────────────────────────────────────────────

    def _cambiar_tab(self, label: str):
        C = self.C
        for k, btn in self._tab_btns.items():
            if k == label:
                btn.configure(fg_color=C['surface1'], text_color=C['accent'],
                              font=ctk.CTkFont(size=12, weight='bold'))
            else:
                btn.configure(fg_color='transparent', text_color=C['text2'],
                              font=ctk.CTkFont(size=12))
        for w in self._contenedor.winfo_children():
            w.pack_forget()
        if label == 'Contactos':
            self._panel_contactos.pack(fill='both', expand=True)
        else:
            self._panel_opor.pack(fill='both', expand=True)

    # ── Datos ─────────────────────────────────────────────────────────────────

    def _cargar(self):
        # Contactos
        contactos = db.listar_contactos(empresa_id=self._emp_id)
        for item in self._tree_contactos.get_children():
            self._tree_contactos.delete(item)
        for c in contactos:
            nombre = f"{c.get('nombre', '')} {c.get('apellido', '')}".strip()
            self._tree_contactos.insert('', 'end', values=(
                nombre,
                c.get('cargo') or '—',
                c.get('email') or '—',
                c.get('telefono') or '—',
                c.get('estado') or '—',
            ))

        # Oportunidades
        opors = db.listar_oportunidades(empresa_id=self._emp_id)
        for item in self._tree_opor.get_children():
            self._tree_opor.delete(item)
        pipeline_total = 0.0
        for o in opors:
            contacto_n = f"{o.get('contacto_nombre', '')} {o.get('contacto_apellido', '')}".strip() or '—'
            valor = o.get('valor') or 0
            pipeline_total += valor
            self._tree_opor.insert('', 'end', values=(
                o.get('nombre') or '—',
                contacto_n,
                o.get('etapa') or '—',
                f"${valor:,.0f}",
                (o.get('fecha_cierre') or '')[:10] or '—',
            ))

        # KPIs
        self._lbl_kpi_contactos.configure(text=str(len(contactos)))
        self._lbl_kpi_opor.configure(text=str(len(opors)))
        self._lbl_kpi_pipeline.configure(text=f"${pipeline_total:,.0f}")
