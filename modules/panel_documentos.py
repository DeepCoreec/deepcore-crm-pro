"""panel_documentos.py — Panel de gestión de documentos para una empresa en CRM Pro."""
import os
import shutil
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime
import database as db
from modules.doc_indexer import extraer_texto


_EXTENSIONES_PERMITIDAS = (
    ('Documentos', '*.pdf *.txt *.docx *.doc'),
    ('PDF',        '*.pdf'),
    ('Texto',      '*.txt'),
    ('Word',       '*.docx *.doc'),
    ('Todos',      '*.*'),
)


class PanelDocumentos(ctk.CTkFrame):
    """Panel que muestra y gestiona documentos adjuntos a una empresa."""

    def __init__(self, parent, C: dict, empresa_id: int, docs_dir: str):
        super().__init__(parent, fg_color='transparent')
        self.C          = C
        self._emp_id    = empresa_id
        self._docs_dir  = docs_dir
        os.makedirs(docs_dir, exist_ok=True)
        self._build()
        self._cargar()

    # ── Layout ──────────────────────────────────────────────────────────────────

    def _build(self):
        C = self.C

        # Toolbar
        bar = ctk.CTkFrame(self, fg_color='transparent')
        bar.pack(fill='x', pady=(0, 8))

        ctk.CTkLabel(bar, text="Documentos adjuntos",
                     font=ctk.CTkFont(size=13, weight='bold'),
                     text_color=C['text']).pack(side='left')

        ctk.CTkButton(bar, text="Subir documento", width=140, height=32,
                      corner_radius=8, fg_color=C['accent'],
                      hover_color=C.get('green', '#22C55E'),
                      text_color='#000000', font=ctk.CTkFont(size=12, weight='bold'),
                      command=self._subir).pack(side='right')

        # Búsqueda
        busq = ctk.CTkFrame(self, fg_color=C['surface0'], corner_radius=8,
                            border_width=1, border_color=C['border'])
        busq.pack(fill='x', pady=(0, 8))
        self._e_buscar = ctk.CTkEntry(
            busq, placeholder_text="Buscar en documentos...",
            fg_color='transparent', border_width=0,
            text_color=C['text'], height=34,
            font=ctk.CTkFont(size=12)
        )
        self._e_buscar.pack(side='left', fill='both', expand=True, padx=10)
        self._e_buscar.bind('<Return>', lambda e: self._buscar())
        ctk.CTkButton(busq, text="Buscar", width=80, height=28,
                      corner_radius=6, fg_color=C['surface1'],
                      text_color=C['text'], font=ctk.CTkFont(size=11),
                      command=self._buscar).pack(side='right', padx=6, pady=3)

        # Lista de documentos
        self._lista = ctk.CTkScrollableFrame(
            self, fg_color=C['surface0'], corner_radius=10,
            border_width=1, border_color=C['border'],
            scrollbar_fg_color=C['surface1']
        )
        self._lista.pack(fill='both', expand=True)
        self._lista.columnconfigure(0, weight=1)

        # Estado vacío
        self._lbl_vacio = ctk.CTkLabel(
            self._lista, text="Sin documentos adjuntos.\nUsa 'Subir documento' para agregar PDFs, Word o TXT.",
            text_color=C['overlay0'], font=ctk.CTkFont(size=12), justify='center'
        )

    # ── Datos ────────────────────────────────────────────────────────────────────

    def _cargar(self):
        self._limpiar_lista()
        docs = db.listar_documentos(self._emp_id)
        if not docs:
            self._lbl_vacio.pack(pady=40)
            return
        for doc in docs:
            self._fila_documento(doc)

    def _limpiar_lista(self):
        for w in self._lista.winfo_children():
            w.destroy()

    def _fila_documento(self, doc: dict):
        C = self.C
        fila = ctk.CTkFrame(self._lista, fg_color=C['surface1'], corner_radius=8)
        fila.pack(fill='x', padx=6, pady=3)

        # Icono tipo
        tipos_color = {'pdf': C.get('red', '#EF4444'),
                       'txt': C.get('blue', '#60A5FA'),
                       'docx': C.get('blue', '#60A5FA'),
                       'doc': C.get('blue', '#60A5FA')}
        tipo  = doc.get('tipo', 'pdf')
        color = tipos_color.get(tipo, C['overlay0'])

        badge = ctk.CTkFrame(fila, fg_color=color, width=36, height=36, corner_radius=6)
        badge.pack(side='left', padx=(10, 8), pady=8)
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text=tipo.upper()[:3],
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color='#000000').place(relx=0.5, rely=0.5, anchor='center')

        # Info
        info = ctk.CTkFrame(fila, fg_color='transparent')
        info.pack(side='left', fill='both', expand=True, pady=6)
        ctk.CTkLabel(info, text=doc['nombre'],
                     font=ctk.CTkFont(size=12, weight='bold'),
                     text_color=C['text'], anchor='w').pack(anchor='w')
        meta = f"{doc.get('created_at','')[:10]}  ·  {doc.get('tamanio_kb', 0)} KB"
        if doc.get('texto'):
            preview = doc['texto'][:80].replace('\n', ' ')
            meta += f"  ·  {preview}..."
        ctk.CTkLabel(info, text=meta, font=ctk.CTkFont(size=10),
                     text_color=C['overlay0'], anchor='w').pack(anchor='w')

        # Acciones
        acc = ctk.CTkFrame(fila, fg_color='transparent')
        acc.pack(side='right', padx=8)
        ctk.CTkButton(acc, text="Abrir", width=64, height=28, corner_radius=6,
                      fg_color='transparent', border_width=1, border_color=C['border'],
                      text_color=C['text'], font=ctk.CTkFont(size=11),
                      command=lambda r=doc.get('ruta', ''): self._abrir(r)
                      ).pack(side='left', padx=2)
        ctk.CTkButton(acc, text="Borrar", width=64, height=28, corner_radius=6,
                      fg_color='transparent', border_width=1, border_color=C.get('red', '#EF4444'),
                      text_color=C.get('red', '#EF4444'), font=ctk.CTkFont(size=11),
                      command=lambda did=doc['id'], r=doc.get('ruta', ''): self._eliminar(did, r)
                      ).pack(side='left', padx=2)

    # ── Acciones ─────────────────────────────────────────────────────────────────

    def _subir(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar documento",
            filetypes=_EXTENSIONES_PERMITIDAS
        )
        if not ruta:
            return

        nombre   = os.path.basename(ruta)
        ext      = os.path.splitext(nombre)[1].lower().lstrip('.')
        tamanio  = max(1, os.path.getsize(ruta) // 1024)
        destino  = os.path.join(self._docs_dir, f"{self._emp_id}_{nombre}")

        # Copiar al directorio de la app
        try:
            shutil.copy2(ruta, destino)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo copiar el archivo:\n{e}")
            return

        # Extraer texto en hilo para no bloquear la UI
        self._btn_estado("Procesando...")
        threading.Thread(
            target=self._procesar_doc,
            args=(nombre, destino, ext, tamanio),
            daemon=True
        ).start()

    def _procesar_doc(self, nombre, ruta, tipo, tamanio_kb):
        texto = extraer_texto(ruta)
        db.guardar_documento(
            empresa_id=self._emp_id,
            nombre=nombre,
            ruta=ruta,
            texto=texto,
            tipo=tipo,
            tamanio_kb=tamanio_kb,
        )
        self.after(0, self._cargar)
        self.after(0, lambda: self._btn_estado(None))

    def _btn_estado(self, msg: str | None):
        pass  # podría actualizar un label de estado

    def _abrir(self, ruta: str):
        if not ruta or not os.path.exists(ruta):
            messagebox.showerror("Error", "Archivo no encontrado en el sistema.")
            return
        import subprocess, sys
        if sys.platform == 'win32':
            os.startfile(ruta)
        elif sys.platform == 'darwin':
            subprocess.call(['open', ruta])
        else:
            subprocess.call(['xdg-open', ruta])

    def _eliminar(self, doc_id: int, ruta: str):
        if not messagebox.askyesno("Confirmar", "¿Eliminar este documento del CRM?\n(El archivo original no se borra)"):
            return
        db.eliminar_documento(doc_id)
        self._cargar()

    def _buscar(self):
        query = self._e_buscar.get().strip()
        if not query:
            self._cargar()
            return
        self._limpiar_lista()
        hits = db.buscar_documentos_fts(query, empresa_id=self._emp_id, limite=10)
        if not hits:
            C = self.C
            ctk.CTkLabel(self._lista,
                         text=f"Sin resultados para: '{query}'",
                         text_color=C['overlay0'],
                         font=ctk.CTkFont(size=12)).pack(pady=30)
            return
        C = self.C
        for h in hits:
            doc = db.get_documento(h['doc_id'])
            if doc:
                fila = ctk.CTkFrame(self._lista, fg_color=C['surface1'], corner_radius=8)
                fila.pack(fill='x', padx=6, pady=3)
                ctk.CTkLabel(fila, text=h['nombre'],
                             font=ctk.CTkFont(size=12, weight='bold'),
                             text_color=C['text']).pack(anchor='w', padx=12, pady=(8, 2))
                ctk.CTkLabel(fila, text=h['fragmento'],
                             font=ctk.CTkFont(size=11),
                             text_color=C['overlay0'],
                             wraplength=500, justify='left').pack(anchor='w', padx=12, pady=(0, 8))
