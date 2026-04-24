"""DeepCore CRM Pro — Importador de clientes desde DeepCore POS."""
import os, sys, sqlite3
import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
import database as db


def _buscar_pos_db() -> str | None:
    """Busca pos.db en AppData y luego en carpeta hermana del exe."""
    candidatos = [
        os.path.join(os.environ.get('APPDATA', ''), 'DeepCore POS', 'pos.db'),
    ]
    # Si corremos desde fuente, buscar carpeta hermana
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hermana = os.path.join(os.path.dirname(raiz), 'DeepCore POS', 'pos.db')
    candidatos.append(hermana)

    for ruta in candidatos:
        if os.path.isfile(ruta):
            return ruta
    return None


def leer_clientes_pos(ruta_db: str) -> list[dict]:
    """Lee clientes únicos del POS (excluye 'Consumidor Final' y vacíos).

    Retorna lista de dicts con: nombre, compras, ultimo_pedido, total_gastado.
    """
    try:
        conn = sqlite3.connect(ruta_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT cliente,
                   COUNT(*)          AS compras,
                   MAX(fecha)        AS ultimo_pedido,
                   SUM(total)        AS total_gastado
            FROM ventas
            WHERE cliente IS NOT NULL
              AND TRIM(cliente) != ''
              AND LOWER(TRIM(cliente)) != 'consumidor final'
            GROUP BY LOWER(TRIM(cliente))
            ORDER BY compras DESC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        raise RuntimeError(f"No se pudo leer la base de datos del POS:\n{e}")


# ══════════════════════════════════════════════════════════════════════════════
#  DIÁLOGO DE IMPORTACIÓN
# ══════════════════════════════════════════════════════════════════════════════

class DialogImportarPOS(ctk.CTkToplevel):
    def __init__(self, master, C: dict, on_importar=None):
        super().__init__(master)
        self.C = C
        self.on_importar = on_importar
        self._vars: list[tk.BooleanVar] = []
        self._clientes: list[dict] = []
        self._ruta_db: str | None = None

        self.title("Importar clientes desde POS")
        self.geometry("560x540")
        self.configure(fg_color=C['base'])
        self.resizable(False, False)
        self.grab_set()

        px, py = master.winfo_rootx(), master.winfo_rooty()
        pw, ph = master.winfo_width(), master.winfo_height()
        self.geometry(f"+{px + pw//2 - 280}+{py + ph//2 - 270}")

        self._build()
        self._detectar_pos()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self):
        C = self.C
        ctk.CTkFrame(self, fg_color=C['accent'], height=3).pack(fill='x')

        ctk.CTkLabel(self,
                     text="Importar desde DeepCore POS",
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=C['heading']).pack(pady=(20, 2), padx=24, anchor='w')
        ctk.CTkLabel(self,
                     text="Los clientes importados se crean con fuente 'POS'. Los duplicados se omiten.",
                     font=ctk.CTkFont(size=11), text_color=C['overlay2']).pack(
                         padx=24, anchor='w')
        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=24, pady=12)

        # Ruta DB
        ruta_row = ctk.CTkFrame(self, fg_color='transparent')
        ruta_row.pack(fill='x', padx=24, pady=(0, 8))
        self._lbl_ruta = ctk.CTkLabel(ruta_row,
                                       text="Buscando base de datos del POS...",
                                       font=ctk.CTkFont(size=11),
                                       text_color=C['text2'], wraplength=380, justify='left')
        self._lbl_ruta.pack(side='left', expand=True, fill='x')
        ctk.CTkButton(ruta_row, text="Buscar", width=80, height=30, corner_radius=8,
                      fg_color=C['surface1'], hover_color=C['surface2'],
                      text_color=C['text'], font=ctk.CTkFont(size=12),
                      command=self._buscar_manual).pack(side='right')

        # Lista de clientes
        self._frame_lista = ctk.CTkScrollableFrame(
            self, fg_color=C['surface0'], corner_radius=10,
            border_width=1, border_color=C['border'])
        self._frame_lista.pack(fill='both', expand=True, padx=24, pady=(0, 8))

        self._lbl_estado = ctk.CTkLabel(self._frame_lista,
                                         text="Buscando...",
                                         font=ctk.CTkFont(size=12),
                                         text_color=C['overlay2'])
        self._lbl_estado.pack(pady=20)

        # Selección rápida + botones
        ctrl = ctk.CTkFrame(self, fg_color='transparent')
        ctrl.pack(fill='x', padx=24, pady=(0, 4))
        ctk.CTkButton(ctrl, text="Seleccionar todo", width=120, height=28, corner_radius=8,
                      fg_color='transparent', border_width=1, border_color=C['border'],
                      text_color=C['text2'], font=ctk.CTkFont(size=11),
                      command=self._sel_todo).pack(side='left')
        ctk.CTkButton(ctrl, text="Deseleccionar", width=110, height=28, corner_radius=8,
                      fg_color='transparent', border_width=1, border_color=C['border'],
                      text_color=C['text2'], font=ctk.CTkFont(size=11),
                      command=self._desel_todo).pack(side='left', padx=(6, 0))

        btns = ctk.CTkFrame(self, fg_color='transparent')
        btns.pack(fill='x', padx=24, pady=12)
        ctk.CTkButton(btns, text="Cancelar", width=110, height=38, corner_radius=8,
                      fg_color=C['surface1'], hover_color=C['surface2'],
                      text_color=C['text'], font=ctk.CTkFont(size=13),
                      command=self.destroy).pack(side='right', padx=(8, 0))
        ctk.CTkButton(btns, text="Importar seleccionados", width=180, height=38,
                      corner_radius=8, fg_color=C['green'], hover_color=C['teal'],
                      text_color='#000000', font=ctk.CTkFont(size=13, weight='bold'),
                      command=self._importar).pack(side='right')

    # ── Lógica ────────────────────────────────────────────────────────────────

    def _detectar_pos(self):
        ruta = _buscar_pos_db()
        if ruta:
            self._cargar_db(ruta)
        else:
            self._lbl_ruta.configure(
                text="No se encontró DeepCore POS instalado. Haz clic en 'Buscar' para localizar pos.db manualmente.",
                text_color=self.C['yellow'])
            self._lbl_estado.configure(text="Selecciona el archivo pos.db para continuar.")

    def _buscar_manual(self):
        ruta = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar base de datos del POS",
            filetypes=[("Base de datos SQLite", "*.db"), ("Todos los archivos", "*.*")]
        )
        if ruta:
            self._cargar_db(ruta)

    def _cargar_db(self, ruta: str):
        self._ruta_db = ruta
        nombre_corto = "..." + ruta[-50:] if len(ruta) > 50 else ruta
        self._lbl_ruta.configure(text=f"DB: {nombre_corto}", text_color=self.C['green'])
        try:
            self._clientes = leer_clientes_pos(ruta)
        except RuntimeError as e:
            messagebox.showerror("Error", str(e), parent=self)
            self._lbl_estado.configure(text="Error al leer el archivo.")
            return
        self._poblar_lista()

    def _poblar_lista(self):
        C = self.C
        for w in self._frame_lista.winfo_children():
            w.destroy()
        self._vars = []

        if not self._clientes:
            ctk.CTkLabel(self._frame_lista,
                         text="No se encontraron clientes con nombre en el POS.",
                         font=ctk.CTkFont(size=12), text_color=C['overlay2']).pack(pady=20)
            return

        # Encabezado
        hdr = ctk.CTkFrame(self._frame_lista, fg_color='transparent')
        hdr.pack(fill='x', padx=8, pady=(8, 4))
        ctk.CTkLabel(hdr, text="Cliente", font=ctk.CTkFont(size=11, weight='bold'),
                     text_color=C['text2'], width=220, anchor='w').pack(side='left')
        ctk.CTkLabel(hdr, text="Compras", font=ctk.CTkFont(size=11, weight='bold'),
                     text_color=C['text2'], width=70, anchor='center').pack(side='left')
        ctk.CTkLabel(hdr, text="Total", font=ctk.CTkFont(size=11, weight='bold'),
                     text_color=C['text2'], width=90, anchor='center').pack(side='left')

        ctk.CTkFrame(self._frame_lista, fg_color=C['border'], height=1).pack(fill='x', padx=8, pady=4)

        # Filas
        existentes = {r['nombre'].lower() for r in db.listar_contactos()}

        for cli in self._clientes:
            nombre = cli['nombre'] or ''
            es_dup = nombre.lower() in existentes

            fila = ctk.CTkFrame(self._frame_lista, fg_color='transparent')
            fila.pack(fill='x', padx=8, pady=2)

            var = tk.BooleanVar(value=not es_dup)
            self._vars.append(var)

            chk = ctk.CTkCheckBox(fila, text='', variable=var, width=24,
                                   checkbox_width=18, checkbox_height=18,
                                   fg_color=C['green'], hover_color=C['teal'],
                                   border_color=C['border'])
            chk.pack(side='left')

            color_nombre = C['overlay2'] if es_dup else C['text']
            lbl_nombre = ctk.CTkLabel(fila, text=nombre + (' (ya existe)' if es_dup else ''),
                                       font=ctk.CTkFont(size=12),
                                       text_color=color_nombre, width=210, anchor='w')
            lbl_nombre.pack(side='left', padx=(4, 0))

            ctk.CTkLabel(fila, text=str(cli.get('compras', 0)),
                         font=ctk.CTkFont(size=12), text_color=C['text2'],
                         width=70, anchor='center').pack(side='left')
            total = cli.get('total_gastado') or 0
            ctk.CTkLabel(fila, text=f"${total:,.2f}",
                         font=ctk.CTkFont(size=12), text_color=C['accent'],
                         width=90, anchor='center').pack(side='left')

    def _sel_todo(self):
        for v in self._vars:
            v.set(True)

    def _desel_todo(self):
        for v in self._vars:
            v.set(False)

    def _importar(self):
        seleccionados = [c for c, v in zip(self._clientes, self._vars) if v.get()]
        if not seleccionados:
            messagebox.showwarning("Sin selección",
                                   "Selecciona al menos un cliente para importar.", parent=self)
            return

        importados = 0
        omitidos   = 0
        existentes = {r['nombre'].lower() for r in db.listar_contactos()}

        for cli in seleccionados:
            nombre = (cli.get('nombre') or '').strip()
            if not nombre or nombre.lower() in existentes:
                omitidos += 1
                continue

            partes = nombre.split(' ', 1)
            nombre_p  = partes[0]
            apellido_p = partes[1] if len(partes) > 1 else ''

            db.crear_contacto(
                nombre=nombre_p,
                apellido=apellido_p,
                cargo='',
                empresa_id=None,
                email='',
                telefono='',
                estado='Cliente',
                fuente='POS',
                notas=f"Importado desde DeepCore POS. Compras: {cli.get('compras', 0)}"
            )
            existentes.add(nombre.lower())
            importados += 1

        msg = f"Se importaron {importados} contacto(s) exitosamente."
        if omitidos:
            msg += f"\n{omitidos} omitido(s) por ser duplicados o inválidos."
        messagebox.showinfo("Importación completa", msg, parent=self)

        if self.on_importar:
            self.on_importar()
        self.destroy()
