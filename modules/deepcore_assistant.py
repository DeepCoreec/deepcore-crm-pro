"""
deepcore_assistant.py — Alisson para DeepCore CRM Pro.
Inyecta datos reales del CRM en cada respuesta para contexto dinámico.
"""
import os as _os
import sys as _sys
from datetime import datetime as _dt

_HERE = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_DEEPCORE_ROOT = _os.path.dirname(_HERE)
for _path in (_HERE, _DEEPCORE_ROOT):
    if _path not in _sys.path:
        _sys.path.insert(0, _path)

try:
    from alisson import Alisson as _Alisson
    _ALISSON_OK = True
except ImportError:
    _ALISSON_OK = False


class AriaCRM:
    """Alisson — Asistente IA de DeepCore CRM Pro con contexto dinámico."""

    _ACCIONES = (
        "ACCIONES QUE PUEDES EJECUTAR (informa al usuario cuando las mencione):\n"
        "- Consultar contactos y clientes registrados\n"
        "- Ver oportunidades del pipeline de ventas\n"
        "- Revisar actividades pendientes del día\n"
        "- Analizar valor del pipeline y probabilidades de cierre\n"
        "- Recomendar acciones de seguimiento para clientes\n"
        "- Generar resumen de actividad semanal\n"
        "- Exportar reportes en PDF o Excel\n\n"
        "EJEMPLOS DE LO QUE EL USUARIO PUEDE PEDIRTE:\n"
        "  '¿Cuántas oportunidades tengo abiertas?'\n"
        "  'Resume mis actividades de hoy'\n"
        "  'Qué clientes llevan más de 30 días sin contacto'\n"
        "  '¿Cuál es el valor total de mi pipeline?'"
    )

    _CRM_INTEL = (
        "\n\nCONOCIMIENTO DE CRM Y VENTAS:\n"
        "Pipeline y seguimiento:\n"
        "  - Etapas: Prospecto(10%) → Calificado(25%) → Propuesta(50%) → Negociación(75%) → Ganado(100%)/Perdido(0%)\n"
        "  - El valor ponderado del pipeline = Σ(valor × probabilidad)\n"
        "  - Regla 80/20: el 20% de los contactos generan el 80% de los ingresos\n"
        "Señales de alerta para mencionar al usuario:\n"
        "  - Oportunidades en 'Propuesta' o 'Negociación' sin actividad reciente → riesgo de perder\n"
        "  - Contactos sin ninguna actividad registrada → relación fría\n"
        "  - Pipeline con pocas oportunidades en 'Prospecto' → falta de prospección\n"
        "Buenas prácticas de ventas B2B en Ecuador:\n"
        "  - Seguimiento cada 3-5 días en etapa de negociación\n"
        "  - Propuestas formales con validez de 15-30 días\n"
        "  - Registrar SIEMPRE el resultado de cada llamada o reunión\n"
        "IVA vigente Ecuador (desde abril 2024):\n"
        "  - Tarifa general: 15%\n"
        "  - Calcular precio con IVA: precio_neto × 1.15\n"
    )

    def __init__(self, api_key: str = '', empresa: str = 'Mi Empresa'):
        self.empresa = empresa
        self._activa = False
        if _ALISSON_OK:
            try:
                self._ia = _Alisson(
                    api_key=api_key,
                    programa="CRM Pro",
                    contexto=self._build_contexto(),
                )
                self._activa = True
            except Exception:
                self._ia = None
        else:
            self._ia = None

    def set_api_key(self, api_key: str):
        if self._ia:
            self._ia.set_api_key(api_key)

    @property
    def activa(self) -> bool:
        return bool(self._ia and self._activa)

    @property
    def modo(self) -> str:
        if not self._ia:
            return 'no_disponible'
        return getattr(self._ia, 'modo', 'local')

    def _get_stats(self) -> dict:
        try:
            import database as _db
            return _db.stats_dashboard()
        except Exception:
            return {}

    def _build_contexto(self) -> str:
        stats = self._get_stats()
        ahora = _dt.now().strftime('%Y-%m-%d %H:%M')
        return (
            f"Eres Alisson, asistente IA de {self.empresa} usando DeepCore CRM Pro.\n"
            f"Fecha y hora actual: {ahora}\n\n"
            f"ESTADO ACTUAL DEL CRM:\n"
            f"  Contactos totales:    {stats.get('contactos', 0)}\n"
            f"  Empresas:             {stats.get('empresas', 0)}\n"
            f"  Oportunidades abiertas: {stats.get('oportunidades', 0)}\n"
            f"  Valor pipeline:       ${stats.get('valor_pipeline', 0):,.2f}\n"
            f"  Actividades hoy:      {stats.get('act_hoy', 0)} pendiente(s)\n\n"
            + self._ACCIONES + self._CRM_INTEL
        )

    def chat(self, mensaje: str) -> str:
        if not self._ia:
            return (
                "Alisson no está disponible en este momento.\n"
                "Configura tu API key de Claude en Configuración para activar el asistente IA."
            )
        try:
            self._ia._contexto = self._build_contexto()
            return self._ia.chat(mensaje)
        except Exception as e:
            return f"Error al procesar tu consulta: {e}"

    def respuesta_rapida(self, tipo: str) -> str:
        prompts = {
            'resumen':    "Dame un resumen ejecutivo del estado actual de mi pipeline de ventas.",
            'pendientes': "¿Qué actividades tengo pendientes hoy? Recomienda por cuál empezar.",
            'alertas':    "Identifica oportunidades en riesgo de perderse y qué hacer.",
            'consejo':    "Dame un consejo de ventas práctico para esta semana.",
        }
        return self.chat(prompts.get(tipo, "Hola, ¿cómo puedes ayudarme hoy?"))
