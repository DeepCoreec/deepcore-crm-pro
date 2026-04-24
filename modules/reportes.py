"""DeepCore CRM Pro — Panel de Reportes."""
import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import database as db
from modules.pdf_gen import generar_reporte_contactos, generar_reporte_pipeline
from modules.excel_gen import exportar_contactos_excel, exportar_pipeline_excel


class ReportesPanel(ctk.CTkFrame):
    def __init__(self, parent, C: dict):
        super().__init__(parent, fg_color='transparent')
        self.C = C
        self._build()

    def _build(self):
        C = self.C

        # Cabecera
        hdr = ctk.CTkFrame(self, fg_color='transparent')
        hdr.pack(fill='x', padx=24, pady=(20, 0))
        ctk.CTkLabel(hdr, text="Reportes",
                     font=ctk.CTkFont(size=22, weight='bold'),
                     text_color=C['heading']).pack(side='left')
        ctk.CTkLabel(hdr, text="Exporta tus datos en PDF o Excel",
                     font=ctk.CTkFont(size=12), text_color=C['overlay2']).pack(
                         side='left', padx=(12, 0), pady=(6, 0))

        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=24, pady=12)

        # Grid de tarjetas de reporte
        grid = ctk.CTkFrame(self, fg_color='transparent')
        grid.pack(fill='both', expand=True, padx=24, pady=8)
        grid.columnconfigure((0, 1), weight=1, uniform='rpt')

        reportes = [
            {
                'titulo':    'Contactos — PDF',
                'desc':      'Lista completa de contactos con empresa, cargo, email y teléfono.',
                'color':     C['green'],
                'formato':   'PDF',
                'cmd':       self._exportar_contactos_pdf,
            },
            {
                'titulo':    'Contactos — Excel',
                'desc':      'Exporta todos los contactos a una hoja de cálculo editable.',
                'color':     C['blue'],
                'formato':   'Excel',
                'cmd':       self._exportar_contactos_excel,
            },
            {
                'titulo':    'Pipeline — PDF',
                'desc':      'Reporte de oportunidades de venta con valor y probabilidad.',
                'color':     C['amber'],
                'formato':   'PDF',
                'cmd':       self._exportar_pipeline_pdf,
            },
            {
                'titulo':    'Pipeline — Excel',
                'desc':      'Exporta el pipeline completo con totales automáticos.',
                'color':     C['indigo'],
                'formato':   'Excel',
                'cmd':       self._exportar_pipeline_excel,
            },
        ]

        for i, r in enumerate(reportes):
            row, col = divmod(i, 2)
            self._card_reporte(grid, r, row, col)

    def _card_reporte(self, parent, datos: dict, row: int, col: int):
        C = self.C
        card = ctk.CTkFrame(parent, fg_color=C['surface0'], corner_radius=14,
                            border_width=1, border_color=C['border'])
        card.grid(row=row, column=col, padx=8, pady=8, sticky='nsew')

        # Franja de color
        ctk.CTkFrame(card, fg_color=datos['color'], height=3, corner_radius=2
                     ).pack(fill='x', padx=16, pady=(16, 12))

        ctk.CTkLabel(card, text=datos['titulo'],
                     font=ctk.CTkFont(size=16, weight='bold'),
                     text_color=datos['color']).pack(anchor='w', padx=16)

        ctk.CTkLabel(card, text=datos['desc'],
                     font=ctk.CTkFont(size=12), text_color=C['text2'],
                     wraplength=320, justify='left').pack(anchor='w', padx=16, pady=(6, 16))

        ctk.CTkButton(card, text=f"Exportar {datos['formato']}",
                      width=160, height=36, corner_radius=8,
                      fg_color=datos['color'], hover_color=C['teal'],
                      text_color='#000000', font=ctk.CTkFont(size=13, weight='bold'),
                      command=datos['cmd']).pack(anchor='w', padx=16, pady=(0, 20))

    # ── Exportaciones ──────────────────────────────────────────────────────────

    def _config(self) -> dict:
        return {
            'empresa': db.get_config('empresa', 'Mi Empresa'),
            'ruc':     db.get_config('ruc', ''),
            'moneda':  db.get_config('moneda', '$'),
        }

    def _exportar_contactos_pdf(self):
        ruta = filedialog.asksaveasfilename(
            defaultextension='.pdf',
            filetypes=[('PDF', '*.pdf')],
            initialfile='contactos_crm.pdf',
            parent=self
        )
        if not ruta:
            return
        try:
            contactos = db.listar_contactos()
            generar_reporte_contactos(contactos, self._config(), ruta)
            if messagebox.askyesno("Listo", f"PDF generado.\n¿Abrir ahora?", parent=self):
                os.startfile(ruta)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}", parent=self)

    def _exportar_contactos_excel(self):
        ruta = filedialog.asksaveasfilename(
            defaultextension='.xlsx',
            filetypes=[('Excel', '*.xlsx')],
            initialfile='contactos_crm.xlsx',
            parent=self
        )
        if not ruta:
            return
        try:
            contactos = db.listar_contactos()
            exportar_contactos_excel(contactos, self._config(), ruta)
            if messagebox.askyesno("Listo", f"Excel generado.\n¿Abrir ahora?", parent=self):
                os.startfile(ruta)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el Excel:\n{e}", parent=self)

    def _exportar_pipeline_pdf(self):
        ruta = filedialog.asksaveasfilename(
            defaultextension='.pdf',
            filetypes=[('PDF', '*.pdf')],
            initialfile='pipeline_crm.pdf',
            parent=self
        )
        if not ruta:
            return
        try:
            ops = db.listar_oportunidades()
            generar_reporte_pipeline(ops, self._config(), ruta)
            if messagebox.askyesno("Listo", "PDF generado.\n¿Abrir ahora?", parent=self):
                os.startfile(ruta)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}", parent=self)

    def _exportar_pipeline_excel(self):
        ruta = filedialog.asksaveasfilename(
            defaultextension='.xlsx',
            filetypes=[('Excel', '*.xlsx')],
            initialfile='pipeline_crm.xlsx',
            parent=self
        )
        if not ruta:
            return
        try:
            ops = db.listar_oportunidades()
            exportar_pipeline_excel(ops, self._config(), ruta)
            if messagebox.askyesno("Listo", "Excel generado.\n¿Abrir ahora?", parent=self):
                os.startfile(ruta)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el Excel:\n{e}", parent=self)
