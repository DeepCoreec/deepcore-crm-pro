"""
DeepCore CRM Pro v1.0
Sistema de Gestión de Clientes y Relaciones Comerciales
"""
import ctypes as _ctypes, sys as _sys
if _sys.platform == 'win32':
    _cw = _ctypes.windll.kernel32.GetConsoleWindow()
    if _cw: _ctypes.windll.user32.ShowWindow(_cw, 0)

_APP_SIG = 'e70b3e36856fdb783ff221c6fc1293d3f545c4127a451ea27e98a86e3f5394c2'

import sys, os, json, hashlib, threading, webbrowser, urllib.request as _urllib
from datetime import datetime, date

APP_VERSION    = "1.0.0"
_REPO_RELEASES = "https://api.github.com/repos/DeepCoreec/deepcore-crm-pro/releases/latest"

# ── Ruta raíz de DeepCore (para acceder a alisson, deepcore_monitor, etc.) ───
_DEEPCORE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _DEEPCORE_ROOT not in sys.path:
    sys.path.insert(0, _DEEPCORE_ROOT)

import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk

import database as db
from theme import theme
from modules.licencia import validar_llave, estado_licencia, llave_guardada, guardar_llave, get_hardware_id
from modules.contactos   import ContactosPanel
from modules.empresas    import EmpresasPanel
from modules.pipeline    import PipelinePanel
from modules.actividades import ActividadesPanel
from modules.reportes    import ReportesPanel
from modules.deepcore_assistant import AriaCRM
from modules.agent_panel import AgentPanel

try:
    from deepcore_monitor import crear_monitor as _crear_monitor
except Exception:
    _crear_monitor = None

# ── Tema ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
C = theme.C

FONT_TITLE = ('Segoe UI', 26, 'bold')
FONT_BODY  = ('Segoe UI', 14)
FONT_SMALL = ('Segoe UI', 13)
FONT_BOLD  = ('Segoe UI', 14, 'bold')

# ── Widgets base ──────────────────────────────────────────────────────────────
def _lbl(parent, text, size=13, bold=False, color=None, **kw):
    font = ctk.CTkFont(size=size, weight='bold' if bold else 'normal')
    return ctk.CTkLabel(parent, text=text, font=font,
                        text_color=color or C['text'], **kw)

def _btn(parent, text, cmd=None, color=None, width=120, height=36, **kw):
    return ctk.CTkButton(parent, text=text, command=cmd,
                         fg_color=color or C['accent'],
                         hover_color=C['teal'], text_color='#000000',
                         font=ctk.CTkFont(size=13, weight='bold'),
                         width=width, height=height, corner_radius=8, **kw)


# ══════════════════════════════════════════════════════════════════════════════
#  PANEL DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

class DashboardPanel(ctk.CTkFrame):
    def __init__(self, parent, C: dict):
        super().__init__(parent, fg_color='transparent')
        self.C = C
        self._build()
        self.refrescar()

    def _build(self):
        # Cabecera
        hdr = ctk.CTkFrame(self, fg_color='transparent')
        hdr.pack(fill='x', padx=24, pady=(20, 0))
        ctk.CTkLabel(hdr, text="Dashboard",
                     font=ctk.CTkFont(size=22, weight='bold'),
                     text_color=self.C['heading']).pack(side='left')
        ctk.CTkLabel(hdr, text="Vista general del CRM",
                     font=ctk.CTkFont(size=12), text_color=self.C['overlay2']).pack(
                         side='left', padx=(12, 0), pady=(6, 0))
        ctk.CTkButton(hdr, text="Actualizar", width=100, height=30,
                      corner_radius=8, fg_color=self.C['surface1'],
                      hover_color=self.C['surface2'], text_color=self.C['text'],
                      font=ctk.CTkFont(size=12),
                      command=self.refrescar).pack(side='right')

        ctk.CTkFrame(self, fg_color=self.C['border'], height=1).pack(fill='x', padx=24, pady=12)

        # KPI cards
        self._frame_kpis = ctk.CTkFrame(self, fg_color='transparent')
        self._frame_kpis.pack(fill='x', padx=24, pady=(0, 16))
        for i in range(4):
            self._frame_kpis.columnconfigure(i, weight=1, uniform='kpi')

        # Barra de pipeline
        self._frame_pipe_bar = ctk.CTkFrame(self, fg_color=self.C['surface0'],
                                            corner_radius=12, border_width=1,
                                            border_color=self.C['border'])
        self._frame_pipe_bar.pack(fill='x', padx=24, pady=(8, 0))

        # Tablas inferiores
        cols = ctk.CTkFrame(self, fg_color='transparent')
        cols.pack(fill='both', expand=True, padx=24, pady=(8, 16))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        self._frame_act = ctk.CTkFrame(cols, fg_color=self.C['surface0'],
                                       corner_radius=12, border_width=1,
                                       border_color=self.C['border'])
        self._frame_act.grid(row=0, column=0, padx=(0, 8), sticky='nsew')

        self._frame_ops = ctk.CTkFrame(cols, fg_color=self.C['surface0'],
                                       corner_radius=12, border_width=1,
                                       border_color=self.C['border'])
        self._frame_ops.grid(row=0, column=1, padx=(8, 0), sticky='nsew')

    def _kpi_card(self, parent, titulo, valor, color, col, icono=''):
        card = ctk.CTkFrame(parent, fg_color=self.C['surface0'], corner_radius=12,
                            border_width=1, border_color=self.C['border'])
        card.grid(row=0, column=col, padx=6, pady=0, sticky='nsew')

        # Barra superior de color
        ctk.CTkFrame(card, fg_color=color, height=3,
                     corner_radius=0).pack(fill='x')

        inner = ctk.CTkFrame(card, fg_color='transparent')
        inner.pack(fill='both', expand=True, padx=16, pady=12)

        # Fila superior: label + ícono circular
        top = ctk.CTkFrame(inner, fg_color='transparent')
        top.pack(fill='x')
        ctk.CTkLabel(top, text=titulo, font=ctk.CTkFont(size=11),
                     text_color=self.C['text2']).pack(side='left')
        ico_bg = ctk.CTkFrame(top, fg_color=color + '22' if len(color) == 7 else self.C['surface1'],
                              corner_radius=16, width=32, height=32)
        ico_bg.pack(side='right')
        ico_bg.pack_propagate(False)
        ctk.CTkLabel(ico_bg, text=icono, font=ctk.CTkFont(size=13, weight='bold'),
                     text_color=color).place(relx=0.5, rely=0.5, anchor='center')

        # Número grande
        ctk.CTkLabel(inner, text=str(valor),
                     font=ctk.CTkFont(size=28, weight='bold'),
                     text_color=color, anchor='w').pack(fill='x', pady=(8, 0))

    def _tabla_simple(self, frame, titulo, filas: list, cols_labels: list):
        for w in frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(frame, text=titulo, font=ctk.CTkFont(size=14, weight='bold'),
                     text_color=self.C['heading']).pack(anchor='w', padx=16, pady=(14, 0))
        ctk.CTkFrame(frame, fg_color=self.C['border'], height=1).pack(fill='x', padx=16, pady=8)

        # Header
        hdr = ctk.CTkFrame(frame, fg_color=self.C['mantle'], corner_radius=6)
        hdr.pack(fill='x', padx=12, pady=(0, 4))
        for i, (lbl, w) in enumerate(cols_labels):
            ctk.CTkLabel(hdr, text=lbl.upper(), font=ctk.CTkFont(size=9, weight='bold'),
                         text_color=self.C['overlay2'], width=w, anchor='w').grid(
                             row=0, column=i, padx=8, pady=6, sticky='w')

        scroll = ctk.CTkScrollableFrame(frame, fg_color='transparent', height=160)
        scroll.pack(fill='both', expand=True, padx=12, pady=(0, 8))

        if not filas:
            ctk.CTkLabel(scroll, text="Sin registros recientes",
                         font=ctk.CTkFont(size=12), text_color=self.C['overlay2']).pack(pady=20)
            return

        for fila in filas:
            row_fr = ctk.CTkFrame(scroll, fg_color='transparent')
            row_fr.pack(fill='x', pady=1)
            ctk.CTkFrame(row_fr, fg_color=self.C['border'], height=1).pack(fill='x')
            datos_fr = ctk.CTkFrame(scroll, fg_color='transparent')
            datos_fr.pack(fill='x')
            for i, (val, w) in enumerate(zip(fila, [c[1] for c in cols_labels])):
                ctk.CTkLabel(datos_fr, text=str(val)[:30],
                             font=ctk.CTkFont(size=12), text_color=self.C['text'],
                             width=w, anchor='w').grid(row=0, column=i, padx=8, pady=5, sticky='w')

    def _build_pipeline_bar(self, stats: dict):
        """Barra horizontal con segmentos coloreados por etapa del pipeline."""
        for w in self._frame_pipe_bar.winfo_children():
            w.destroy()

        COLORES = {
            'Prospecto': '#60A5FA', 'Calificado': '#818CF8',
            'Propuesta': '#F59E0B', 'Negociación': '#FB923C',
            'Ganado':    '#10B981', 'Perdido':     '#EF4444',
        }
        por_etapa = stats.get('valor_pipeline', 0)

        hdr = ctk.CTkFrame(self._frame_pipe_bar, fg_color='transparent')
        hdr.pack(fill='x', padx=16, pady=(10, 6))
        ctk.CTkLabel(hdr, text="Pipeline por etapa",
                     font=ctk.CTkFont(size=13, weight='bold'),
                     text_color=self.C['heading']).pack(side='left')

        # Obtener conteos reales
        pipe_stats = db.stats_pipeline()
        etapas_data = pipe_stats.get('por_etapa', {})
        total_ops = sum(v['n'] for v in etapas_data.values()) or 1

        etapas_fr = ctk.CTkFrame(self._frame_pipe_bar, fg_color='transparent')
        etapas_fr.pack(fill='x', padx=16, pady=(0, 10))

        for etapa in ['Prospecto', 'Calificado', 'Propuesta', 'Negociación', 'Ganado', 'Perdido']:
            datos = etapas_data.get(etapa, {'n': 0, 'total': 0})
            color = COLORES.get(etapa, self.C['accent'])
            pct   = datos['n'] / total_ops

            col_fr = ctk.CTkFrame(etapas_fr, fg_color='transparent')
            col_fr.pack(side='left', expand=True, padx=4)

            ctk.CTkLabel(col_fr, text=str(datos['n']),
                         font=ctk.CTkFont(size=16, weight='bold'),
                         text_color=color).pack()

            bar = ctk.CTkProgressBar(col_fr, height=6, corner_radius=3,
                                     fg_color=self.C['surface1'],
                                     progress_color=color, width=80)
            bar.pack(pady=2)
            bar.set(max(pct, 0.02) if datos['n'] > 0 else 0)

            ctk.CTkLabel(col_fr, text=etapa,
                         font=ctk.CTkFont(size=9), text_color=self.C['text2']).pack()

    def cargar(self):
        self.refrescar()

    def refrescar(self):
        stats  = db.stats_dashboard()
        moneda = db.get_config('moneda', '$')

        # KPIs (5 tarjetas: Contactos, Empresas, Oportunidades, Pipeline $, Act.hoy)
        for w in self._frame_kpis.winfo_children():
            w.destroy()
        for i in range(5):
            self._frame_kpis.columnconfigure(i, weight=1, uniform='kpi')

        n_empresas = len(db.listar_empresas())
        kpis = [
            ("Contactos",     stats['contactos'],              self.C['blue'],   "C"),
            ("Empresas",      n_empresas,                      self.C['sky'],    "E"),
            ("Oportunidades", stats['oportunidades'],           self.C['amber'],  "O"),
            (f"Pipeline ({moneda})", f"{stats['valor_pipeline']:,.0f}", self.C['green'], "$"),
            ("Act. pendientes hoy", stats['act_hoy'],           self.C['indigo'], "!"),
        ]
        for col, (titulo, valor, color, icono) in enumerate(kpis):
            self._kpi_card(self._frame_kpis, titulo, valor, color, col, icono)

        # Barra visual del pipeline por etapa
        self._build_pipeline_bar(stats)

        # Últimas actividades
        act_filas = []
        for a in stats.get('ultimas_act', []):
            contacto = f"{a.get('contacto_nombre','') or '—'}"
            fecha    = (a.get('fecha',''))[:10]
            act_filas.append((a.get('tipo',''), a.get('titulo','')[:28], contacto, fecha))
        self._tabla_simple(self._frame_act, "Últimas actividades", act_filas,
                           [('Tipo',60),('Título',160),('Contacto',120),('Fecha',80)])

        # Oportunidades próximas
        ops_filas = []
        for o in stats.get('proximas_ops', []):
            contacto = f"{o.get('contacto_nombre','') or '—'}"
            ops_filas.append((o.get('nombre','')[:28], contacto, o.get('etapa',''),
                              f"{moneda}{o.get('valor',0):,.0f}"))
        self._tabla_simple(self._frame_ops, "Oportunidades activas", ops_filas,
                           [('Oportunidad',160),('Contacto',110),('Etapa',90),(f'Valor',80)])


# ══════════════════════════════════════════════════════════════════════════════
#  PANEL CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

class ConfigPanel(ctk.CTkFrame):
    def __init__(self, parent, C: dict, aria: AriaCRM, on_cambio=None):
        super().__init__(parent, fg_color='transparent')
        self.C = C
        self._aria = aria
        self._on_cambio = on_cambio
        self._build()

    def _build(self):
        C = self.C

        hdr = ctk.CTkFrame(self, fg_color='transparent')
        hdr.pack(fill='x', padx=24, pady=(20, 0))
        ctk.CTkLabel(hdr, text="Configuración",
                     font=ctk.CTkFont(size=22, weight='bold'),
                     text_color=C['heading']).pack(side='left')

        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=24, pady=12)

        scroll = ctk.CTkScrollableFrame(self, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=24, pady=(0, 16))

        def seccion(texto):
            ctk.CTkLabel(scroll, text=texto, font=ctk.CTkFont(size=9, weight='bold'),
                         text_color=C['overlay2']).pack(anchor='w', pady=(20, 4))
            ctk.CTkFrame(scroll, fg_color=C['border'], height=1).pack(fill='x', pady=(0, 12))

        def campo(label, config_key, default='', ancho=400):
            ctk.CTkLabel(scroll, text=label, font=ctk.CTkFont(size=12, weight='bold'),
                         text_color=C['text2']).pack(anchor='w', pady=(0, 4))
            e = ctk.CTkEntry(scroll, width=ancho, height=36, corner_radius=8,
                             fg_color=C['surface0'], border_color=C['border'],
                             border_width=1, text_color=C['text'], font=ctk.CTkFont(size=13))
            e.insert(0, db.get_config(config_key, default))
            e.bind('<FocusIn>',  lambda ev: e.configure(border_color=C['accent']))
            e.bind('<FocusOut>', lambda ev: e.configure(border_color=C['border']))
            e.pack(anchor='w', pady=(0, 12))
            return e, config_key

        seccion("DATOS DE LA EMPRESA")
        self._campos = []
        self._campos.append(campo("Nombre de la empresa", "empresa", "Mi Empresa"))
        self._campos.append(campo("RUC", "ruc", ""))
        self._campos.append(campo("Moneda (símbolo)", "moneda", "$", ancho=120))

        seccion("ASISTENTE IA — ALISSON")
        ctk.CTkLabel(scroll, text="API Key de Claude (Anthropic)",
                     font=ctk.CTkFont(size=12, weight='bold'), text_color=C['text2']).pack(anchor='w', pady=(0, 4))
        self._e_apikey = ctk.CTkEntry(scroll, width=400, height=36, corner_radius=8,
                                      fg_color=C['surface0'], border_color=C['border'],
                                      border_width=1, text_color=C['text'],
                                      placeholder_text="sk-ant-...",
                                      show='*', font=ctk.CTkFont(size=13))
        self._e_apikey.insert(0, db.get_config('api_key', ''))
        self._e_apikey.pack(anchor='w', pady=(0, 6))

        ctk.CTkLabel(scroll, text="La API key activa el asistente IA Alisson con contexto real de tu CRM.",
                     font=ctk.CTkFont(size=11), text_color=C['overlay2']).pack(anchor='w', pady=(0, 12))

        seccion("HARDWARE")
        hw = get_hardware_id()
        hw_frame = ctk.CTkFrame(scroll, fg_color=C['surface0'], corner_radius=8,
                                border_width=1, border_color=C['border'])
        hw_frame.pack(fill='x', pady=(0, 12))
        ctk.CTkLabel(hw_frame, text=f"ID de Hardware: {hw}",
                     font=ctk.CTkFont(size=12, family='Consolas'), text_color=C['text2']).pack(
                         padx=16, pady=12, anchor='w')

        # Guardar
        ctk.CTkButton(scroll, text="Guardar configuración", width=200, height=40,
                      corner_radius=8, fg_color=C['green'], hover_color=C['teal'],
                      text_color='#000000', font=ctk.CTkFont(size=13, weight='bold'),
                      command=self._guardar).pack(anchor='w', pady=(8, 0))

    def _guardar(self):
        for (e, key) in self._campos:
            db.set_config(key, e.get().strip())
        api_key = self._e_apikey.get().strip()
        db.set_config('api_key', api_key)
        if self._aria:
            self._aria.set_api_key(api_key)
        if self._on_cambio:
            self._on_cambio()
        messagebox.showinfo("Guardado", "Configuración guardada correctamente.", parent=self)


# ══════════════════════════════════════════════════════════════════════════════
#  PANEL CHAT IA
# ══════════════════════════════════════════════════════════════════════════════

class ChatIAPanel(ctk.CTkFrame):
    def __init__(self, parent, C: dict, aria: AriaCRM):
        super().__init__(parent, fg_color='transparent')
        self.C    = C
        self._aria = aria
        self._build()

    def _build(self):
        C = self.C

        hdr = ctk.CTkFrame(self, fg_color='transparent')
        hdr.pack(fill='x', padx=24, pady=(20, 0))
        ctk.CTkLabel(hdr, text="Asistente IA",
                     font=ctk.CTkFont(size=22, weight='bold'),
                     text_color=C['heading']).pack(side='left')

        modo_color = C['green'] if self._aria.activa else C['amber']
        modo_txt   = f"● {self._aria.modo.title()}"
        ctk.CTkLabel(hdr, text=modo_txt, font=ctk.CTkFont(size=12),
                     text_color=modo_color).pack(side='right')

        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=24, pady=12)

        # Botones rápidos
        rpds = ctk.CTkFrame(self, fg_color='transparent')
        rpds.pack(fill='x', padx=24, pady=(0, 10))
        for label, tipo in [('Resumen pipeline','resumen'),('Actividades hoy','pendientes'),
                             ('Alertas','alertas'),('Consejo del día','consejo')]:
            ctk.CTkButton(rpds, text=label, width=140, height=30,
                          corner_radius=8, fg_color=C['surface1'],
                          hover_color=C['surface2'], text_color=C['text'],
                          font=ctk.CTkFont(size=11),
                          command=lambda t=tipo: self._rapida(t)).pack(side='left', padx=(0, 8))

        # Chat display
        self._txt = ctk.CTkTextbox(self, fg_color=C['surface0'], corner_radius=12,
                                   border_width=1, border_color=C['border'],
                                   text_color=C['text'], font=ctk.CTkFont(size=13),
                                   state='disabled', wrap='word')
        self._txt.pack(fill='both', expand=True, padx=24, pady=(0, 10))

        # Input
        inp = ctk.CTkFrame(self, fg_color='transparent')
        inp.pack(fill='x', padx=24, pady=(0, 16))
        self._e_msg = ctk.CTkEntry(inp, placeholder_text="Escribe tu consulta...",
                                   height=40, corner_radius=8,
                                   fg_color=C['surface0'], border_color=C['border'],
                                   border_width=1, text_color=C['text'],
                                   placeholder_text_color=C['overlay2'],
                                   font=ctk.CTkFont(size=13))
        self._e_msg.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self._e_msg.bind('<Return>', lambda e: self._enviar())
        self._e_msg.bind('<FocusIn>',  lambda e: self._e_msg.configure(border_color=C['accent']))
        self._e_msg.bind('<FocusOut>', lambda e: self._e_msg.configure(border_color=C['border']))

        ctk.CTkButton(inp, text="Enviar", width=90, height=40, corner_radius=8,
                      fg_color=C['green'], hover_color=C['teal'],
                      text_color='#000000', font=ctk.CTkFont(size=13, weight='bold'),
                      command=self._enviar).pack(side='right')

        self._agregar("Sistema", "Hola, soy Alisson, tu asistente de CRM. ¿En qué puedo ayudarte?", C['accent'])

    def _agregar(self, rol: str, texto: str, color: str = None):
        self._txt.configure(state='normal')
        ts = datetime.now().strftime('%H:%M')
        self._txt.insert('end', f"\n[{ts}] {rol}:\n", 'rol')
        self._txt.insert('end', texto + '\n')
        self._txt.see('end')
        self._txt.configure(state='disabled')

    def _enviar(self):
        msg = self._e_msg.get().strip()
        if not msg:
            return
        self._e_msg.delete(0, 'end')
        self._agregar("Tú", msg, self.C['text'])
        threading.Thread(target=self._responder, args=(msg,), daemon=True).start()

    def _responder(self, msg: str):
        resp = self._aria.chat(msg)
        self.after(0, lambda: self._agregar("Alisson", resp, self.C['accent']))

    def _rapida(self, tipo: str):
        self._agregar("Sistema", f"Consultando: {tipo}...", self.C['text2'])
        threading.Thread(target=lambda: self.after(0, lambda: self._agregar(
            "Alisson", self._aria.respuesta_rapida(tipo), self.C['accent']
        )), daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
#  VENTANA DE LOGIN / LICENCIA
# ══════════════════════════════════════════════════════════════════════════════

class VentanaLogin(ctk.CTkToplevel):
    def __init__(self, master, on_ok):
        super().__init__(master)
        self.on_ok = on_ok
        self.title("DeepCore CRM Pro — Activación")
        self.geometry("460x340")
        self.configure(fg_color=C['base'])
        self.resizable(False, False)
        self.grab_set()

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw-460)//2}+{(sh-340)//2}")

        self._build()

    def _build(self):
        ctk.CTkFrame(self, fg_color=C['accent'], height=3).pack(fill='x')

        badge = ctk.CTkFrame(self, fg_color=C['accent'], corner_radius=12,
                             width=52, height=40)
        badge.pack(pady=(24, 0))
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="CRM", font=ctk.CTkFont(size=16, weight='bold'),
                     text_color='#000000').place(relx=0.5, rely=0.5, anchor='center')

        ctk.CTkLabel(self, text="DeepCore CRM Pro",
                     font=ctk.CTkFont(size=20, weight='bold'),
                     text_color=C['heading']).pack(pady=(10, 2))
        ctk.CTkLabel(self, text="Ingresa tu clave de licencia para continuar",
                     font=ctk.CTkFont(size=12), text_color=C['text2']).pack()

        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=32, pady=16)

        self._e_key = ctk.CTkEntry(self, placeholder_text="XXXX-XXXX-XXXX-XXXX",
                                   width=340, height=42, corner_radius=10,
                                   fg_color=C['surface0'], border_color=C['border'],
                                   border_width=1, text_color=C['text'],
                                   font=ctk.CTkFont(size=15),
                                   validate='key',
                                   validatecommand=(self.register(lambda v: len(v) <= 25), '%P'))
        self._e_key.pack(pady=(0, 6))
        self._e_key.bind('<FocusIn>',  lambda e: self._e_key.configure(border_color=C['accent']))
        self._e_key.bind('<FocusOut>', lambda e: self._e_key.configure(border_color=C['border']))
        self._e_key.bind('<Return>', lambda e: self._validar())

        hw = get_hardware_id()
        ctk.CTkLabel(self, text=f"Hardware ID: {hw}",
                     font=ctk.CTkFont(size=10, family='Consolas'),
                     text_color=C['overlay2']).pack(pady=(0, 14))

        self._lbl_estado = ctk.CTkLabel(self, text="",
                                        font=ctk.CTkFont(size=12),
                                        text_color=C['text2'])
        self._lbl_estado.pack()

        ctk.CTkButton(self, text="Activar licencia", width=200, height=42,
                      corner_radius=10, fg_color=C['green'], hover_color=C['teal'],
                      text_color='#000000', font=ctk.CTkFont(size=14, weight='bold'),
                      command=self._validar).pack(pady=14)

        ctk.CTkLabel(self, text="DeepCore Systems  ·  deepcore.ec",
                     font=ctk.CTkFont(size=10), text_color=C['overlay2']).pack(pady=(0, 12))

    def _validar(self):
        key = self._e_key.get().strip()
        if not key:
            self._lbl_estado.configure(text="Ingresa una clave.", text_color=C['amber'])
            return
        self._lbl_estado.configure(text="Verificando...", text_color=C['text2'])
        self.update()
        ok, msg = validar_llave(key)
        if ok:
            guardar_llave(key)
            self._lbl_estado.configure(text=msg, text_color=C['green'])
            self.after(800, lambda: (self.destroy(), self.on_ok()))
        else:
            self._lbl_estado.configure(text=msg, text_color=C['red'])


# ══════════════════════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class DeepCoreCRM(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DeepCore CRM Pro")
        self.geometry("1280x780")
        self.minsize(1024, 640)
        self.configure(fg_color=C['base'])

        db.inicializar()

        self._aria: AriaCRM | None = None
        self._agent_panel: AgentPanel | None = None
        self._panel_activo: str = ''
        self._paneles: dict = {}

        self._build_topbar()
        self._build_body()

        self.after(400,  self._verificar_licencia)
        self.after(2000, self._verificar_actualizacion)
        self.after(3500, self._notificar_pendientes)

        if _crear_monitor:
            try:
                _crear_monitor(self)
            except Exception:
                pass

    # ── Topbar ────────────────────────────────────────────────────────────────

    def _build_topbar(self):
        tb = ctk.CTkFrame(self, fg_color=C['mantle'], height=58, corner_radius=0)
        tb.pack(side='top', fill='x')
        tb.pack_propagate(False)
        ctk.CTkFrame(tb, fg_color=C['border'], height=1).place(relx=0, rely=1.0, relwidth=1.0, anchor='sw')

        badge = ctk.CTkFrame(tb, fg_color=C['accent'], corner_radius=8, width=48, height=30)
        badge.pack(side='left', padx=(16, 10), pady=14)
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="CRM", font=ctk.CTkFont(size=13, weight='bold'),
                     text_color='#000000').place(relx=0.5, rely=0.5, anchor='center')

        ctk.CTkLabel(tb, text="DeepCore CRM Pro",
                     font=ctk.CTkFont(size=16, weight='bold'),
                     text_color=C['heading']).pack(side='left')

        empresa = db.get_config('empresa', 'Mi Empresa')
        self._lbl_empresa = ctk.CTkLabel(tb, text=empresa,
                                          font=ctk.CTkFont(size=12), text_color=C['text2'])
        self._lbl_empresa.pack(side='right', padx=16)

        ctk.CTkLabel(tb, text=f"v{APP_VERSION}",
                     font=ctk.CTkFont(size=11), text_color=C['overlay2']).pack(side='right', padx=(0, 8))

    # ── Body: sidebar + content ───────────────────────────────────────────────

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color='transparent', corner_radius=0)
        body.pack(fill='both', expand=True)

        # Sidebar
        sb = ctk.CTkFrame(body, width=210, fg_color=C['mantle'], corner_radius=0)
        sb.pack(side='left', fill='y')
        sb.pack_propagate(False)
        ctk.CTkFrame(body, fg_color=C['border'], width=1).pack(side='left', fill='y')

        # Secciones de nav
        ctk.CTkLabel(sb, text="MENÚ PRINCIPAL",
                     font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=C['overlay2']).pack(anchor='w', padx=20, pady=(20, 8))

        self._nav_btns: dict[str, ctk.CTkButton] = {}
        nav_items = [
            ('dashboard',   'Dashboard'),
            ('contactos',   'Contactos'),
            ('empresas',    'Empresas'),
            ('pipeline',    'Pipeline'),
            ('actividades', 'Actividades'),
            ('reportes',    'Reportes'),
        ]
        for key, label in nav_items:
            b = ctk.CTkButton(sb, text=label, anchor='w',
                              height=38, corner_radius=8,
                              fg_color='transparent', text_color=C['text2'],
                              hover_color=C['surface1'],
                              font=ctk.CTkFont(size=13),
                              command=lambda k=key: self._nav(k))
            b.pack(fill='x', padx=10, pady=2)
            self._nav_btns[key] = b

        ctk.CTkLabel(sb, text="INTELIGENCIA", font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=C['overlay2']).pack(anchor='w', padx=20, pady=(20, 8))

        b_ia = ctk.CTkButton(sb, text="Asistente IA", anchor='w',
                             height=38, corner_radius=8,
                             fg_color='transparent', text_color=C['text2'],
                             hover_color=C['surface1'], font=ctk.CTkFont(size=13),
                             command=lambda: self._nav('chatia'))
        b_ia.pack(fill='x', padx=10, pady=2)
        self._nav_btns['chatia'] = b_ia

        ctk.CTkLabel(sb, text="SISTEMA", font=ctk.CTkFont(size=9, weight='bold'),
                     text_color=C['overlay2']).pack(anchor='w', padx=20, pady=(20, 8))

        b_cfg = ctk.CTkButton(sb, text="Configuración", anchor='w',
                              height=38, corner_radius=8,
                              fg_color='transparent', text_color=C['text2'],
                              hover_color=C['surface1'], font=ctk.CTkFont(size=13),
                              command=lambda: self._nav('config'))
        b_cfg.pack(fill='x', padx=10, pady=2)
        self._nav_btns['config'] = b_cfg

        # Versión en el fondo
        ctk.CTkLabel(sb, text=f"DeepCore CRM Pro\nv{APP_VERSION}",
                     font=ctk.CTkFont(size=9), text_color=C['overlay2'],
                     justify='center').pack(side='bottom', pady=16)

        # Área de contenido
        self._content = ctk.CTkFrame(body, fg_color=C['base'], corner_radius=0)
        self._content.pack(side='left', fill='both', expand=True)

        # Inicializar Alisson
        api_key = db.get_config('api_key', '')
        empresa = db.get_config('empresa', 'Mi Empresa')
        self._aria = AriaCRM(api_key=api_key, empresa=empresa)

        # Ir al dashboard
        self._nav('dashboard')

    # ── Navegación ────────────────────────────────────────────────────────────

    def _nav(self, seccion: str):
        if self._panel_activo == seccion:
            return

        # Actualizar botones
        for key, btn in self._nav_btns.items():
            if key == seccion:
                btn.configure(fg_color=C['surface0'],
                              text_color=C['accent'],
                              font=ctk.CTkFont(size=13, weight='bold'))
            else:
                btn.configure(fg_color='transparent',
                              text_color=C['text2'],
                              font=ctk.CTkFont(size=13))

        # Ocultar panel anterior
        if self._panel_activo and self._panel_activo in self._paneles:
            self._paneles[self._panel_activo].pack_forget()

        self._panel_activo = seccion

        # Crear o mostrar panel
        if seccion not in self._paneles:
            panel = self._crear_panel(seccion)
            self._paneles[seccion] = panel
        self._paneles[seccion].pack(fill='both', expand=True)

    def _crear_panel(self, seccion: str) -> ctk.CTkFrame:
        if seccion == 'dashboard':
            return DashboardPanel(self._content, C)
        elif seccion == 'contactos':
            return ContactosPanel(self._content, C)
        elif seccion == 'empresas':
            return EmpresasPanel(self._content, C)
        elif seccion == 'pipeline':
            return PipelinePanel(self._content, C)
        elif seccion == 'actividades':
            return ActividadesPanel(self._content, C)
        elif seccion == 'reportes':
            return ReportesPanel(self._content, C)
        elif seccion == 'chatia':
            self._agent_panel = AgentPanel(
                self._content, C,
                on_datos_cambiados=self._refrescar_paneles_activos
            )
            return self._agent_panel
        elif seccion == 'config':
            return ConfigPanel(self._content, C, self._aria, on_cambio=self._on_config_cambio)
        return ctk.CTkFrame(self._content, fg_color='transparent')

    def _on_config_cambio(self):
        empresa = db.get_config('empresa', 'Mi Empresa')
        self._lbl_empresa.configure(text=empresa)
        # Propagar nueva API key al AgentPanel si está activo
        api_key = db.get_config('api_key', '')
        if hasattr(self, '_agent_panel') and self._agent_panel:
            try:
                self._agent_panel.actualizar_api_key(api_key)
            except Exception:
                pass

    def _refrescar_paneles_activos(self):
        """Refresca el panel activo cuando el agente modifica datos."""
        panel = self._paneles.get(self._panel_activo)
        if panel and hasattr(panel, 'cargar'):
            try:
                panel.cargar()
            except Exception:
                pass
        # Siempre refrescar el dashboard si está en memoria
        dashboard = self._paneles.get('dashboard')
        if dashboard and hasattr(dashboard, 'cargar') and self._panel_activo != 'dashboard':
            try:
                dashboard.cargar()
            except Exception:
                pass

    # ── Licencia ──────────────────────────────────────────────────────────────

    def _verificar_licencia(self):
        key = llave_guardada()
        if not key:
            self.withdraw()
            VentanaLogin(self, on_ok=self.deiconify)
            return
        st = estado_licencia(key)
        if not st['valida']:
            self.withdraw()
            VentanaLogin(self, on_ok=self.deiconify)
        elif st.get('advertir'):
            messagebox.showwarning(
                "Licencia",
                f"{st['mensaje']}\n\nRenueva tu licencia en deepcore.ec",
                parent=self
            )

    # ── Auto-updater ──────────────────────────────────────────────────────────

    def _verificar_actualizacion(self):
        def _check():
            try:
                url = _REPO_RELEASES
                if not url.startswith('https://api.github.com/'):
                    return
                req = _urllib.Request(url, headers={'User-Agent': 'DeepCore-CRM-Pro/1.0'})
                with _urllib.urlopen(req, timeout=6) as r:
                    data = json.loads(r.read(65536))
                tag = data.get('tag_name', '').lstrip('v')
                if tag and tag > APP_VERSION:
                    html_url = data.get('html_url', '')
                    self.after(0, lambda: self._notif_update(tag, html_url))
            except Exception:
                pass
        threading.Thread(target=_check, daemon=True).start()

    def _notificar_pendientes(self):
        """Avisa al usuario de actividades pendientes y vencidas al iniciar."""
        try:
            from datetime import datetime as _dt
            ahora = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
            vencidas = db.listar_actividades(completada=0, limite=200)
            vencidas = [a for a in vencidas if a.get('fecha', '') < ahora]
            if vencidas:
                n = len(vencidas)
                msg = (
                    f"Tienes {n} actividad{'es' if n > 1 else ''} pendiente{'s' if n > 1 else ''} "
                    f"vencida{'s' if n > 1 else ''}.\n\n"
                    + '\n'.join(
                        f"• {a.get('tipo','')}: {a.get('titulo','')}"
                        for a in vencidas[:5]
                    )
                    + ('\n  ...' if n > 5 else '')
                    + '\n\n¿Ir a Actividades ahora?'
                )
                if messagebox.askyesno("Actividades vencidas", msg, parent=self):
                    self._nav('actividades')
        except Exception:
            pass

    def _notif_update(self, nueva: str, url: str):
        if messagebox.askyesno(
            "Actualización disponible",
            f"Nueva versión disponible: v{nueva}\nVersión actual: v{APP_VERSION}\n\n¿Descargar ahora?",
            parent=self
        ):
            if url:
                webbrowser.open(url)


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app = DeepCoreCRM()
    app.mainloop()
