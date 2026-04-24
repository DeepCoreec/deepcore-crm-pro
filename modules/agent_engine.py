"""DeepCore CRM Pro — Motor de agente con tool_use (Claude API)."""
import json
import requests
from modules.agent_tools import TOOLS, ejecutar_herramienta, NOMBRES_LEGIBLES

_API_URL  = "https://api.anthropic.com/v1/messages"
_HEADERS  = {
    "anthropic-version": "2023-06-01",
    "content-type":      "application/json",
}
_MODELOS  = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}
_MAX_ITER = 8   # máximo de rondas tool_use por consulta

_SYSTEM = """Eres el Agente IA de DeepCore CRM Pro. Trabajas directamente dentro del CRM del usuario.

IDENTIDAD
- Nombre: Aria (Agente CRM)
- Idioma: español, tono profesional y conciso
- Empresa que te usa: la empresa del usuario que tiene licencia DeepCore

CAPACIDADES
Tienes herramientas reales que EJECUTAN acciones en el CRM. Cuando el usuario pida algo que puedas hacer, HAZLO inmediatamente — no le pidas confirmación innecesaria para operaciones simples como crear un contacto o buscar información.

REGLAS DE USO DE HERRAMIENTAS
1. Si el usuario pide crear algo, usa PRIMERO buscar para verificar que no exista duplicado.
2. Siempre confirma los datos importantes DESPUÉS de crear (nombre, ID asignado).
3. Para oportunidades: si el usuario menciona empresa/contacto por nombre, busca el ID primero.
4. Reporta con claridad qué hiciste: "Creé el contacto X con ID Y."
5. Si falta un dato obligatorio, créalo con valores razonables o pide solo lo mínimo.

FORMATO DE RESPUESTA
- Respuestas cortas y directas
- Usa listas cuando hay múltiples items
- Al final de cada acción ejecutada, confirma brevemente lo que hiciste
- Si hay errores, explica qué falló y cómo resolverlo

NO PUEDES
- Eliminar registros (eso requiere confirmación manual del usuario en la interfaz)
- Acceder a datos fuera del CRM
- Inventar información que no esté en las herramientas
"""


class AgentEngine:
    """Ejecuta el loop de tool_use de Claude API.

    Callbacks:
        on_tool_start(nombre_legible: str) → se llama cuando Claude solicita una herramienta
        on_tool_done(nombre_legible: str, ok: bool) → se llama cuando la herramienta termina
        on_datos_cambiados() → se llama cuando hay una operación de escritura
    """

    def __init__(
        self,
        api_key:          str  = '',
        modelo:           str  = 'haiku',
        on_tool_start     = None,
        on_tool_done      = None,
        on_datos_cambiados = None,
    ):
        self.api_key           = api_key
        self.modelo            = _MODELOS.get(modelo, _MODELOS['haiku'])
        self.on_tool_start     = on_tool_start
        self.on_tool_done      = on_tool_done
        self.on_datos_cambiados = on_datos_cambiados

    # ── API pública ───────────────────────────────────────────────────────────

    def ejecutar(self, mensaje: str, historial: list | None = None) -> str:
        """Ejecuta una consulta completa con loop tool_use.

        Returns:
            Texto final de respuesta del agente.
        Raises:
            RuntimeError: Si la API key es inválida o hay error de red.
        """
        if not self.api_key or len(self.api_key) < 10:
            return (
                "Para activar el Agente IA necesitas configurar tu API key de Claude.\n"
                "Ve a Configuración → API key y pega tu clave de Anthropic Console."
            )

        messages = list(historial or [])
        messages.append({"role": "user", "content": mensaje})

        _ESCRIBE = {
            'crear_contacto', 'crear_empresa', 'crear_oportunidad',
            'actualizar_etapa_oportunidad', 'crear_actividad'
        }

        for _ in range(_MAX_ITER):
            response = self._llamar_api(messages)

            stop_reason = response.get('stop_reason')
            content     = response.get('content', [])

            # Agregar turno del asistente al historial
            messages.append({"role": "assistant", "content": content})

            if stop_reason == 'end_turn':
                return self._extraer_texto(content)

            if stop_reason == 'tool_use':
                tool_results = []
                for bloque in content:
                    if bloque.get('type') != 'tool_use':
                        continue

                    nombre      = bloque['name']
                    params      = bloque.get('input', {})
                    tool_id     = bloque['id']
                    legible     = NOMBRES_LEGIBLES.get(nombre, nombre)

                    if self.on_tool_start:
                        self.on_tool_start(legible)

                    resultado = ejecutar_herramienta(nombre, params)
                    ok = 'error' not in resultado

                    if ok and nombre in _ESCRIBE and self.on_datos_cambiados:
                        self.on_datos_cambiados()

                    if self.on_tool_done:
                        self.on_tool_done(legible, ok)

                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": tool_id,
                        "content":     json.dumps(resultado, ensure_ascii=False)
                    })

                messages.append({"role": "user", "content": tool_results})
                continue

            # stop_reason inesperado
            break

        return self._extraer_texto(content)

    # ── Internos ──────────────────────────────────────────────────────────────

    def _llamar_api(self, messages: list) -> dict:
        headers = {**_HEADERS, "x-api-key": self.api_key}
        payload = {
            "model":      self.modelo,
            "max_tokens": 4096,
            "system":     _SYSTEM,
            "tools":      TOOLS,
            "messages":   messages,
        }
        resp = requests.post(_API_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 401:
            raise RuntimeError("API key inválida. Verifica tu clave en Configuración.")
        if resp.status_code == 429:
            raise RuntimeError("Límite de uso alcanzado. Intenta en unos segundos.")
        if not resp.ok:
            raise RuntimeError(f"Error API {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    @staticmethod
    def _extraer_texto(content: list) -> str:
        partes = [b.get('text', '') for b in content if b.get('type') == 'text']
        return '\n'.join(partes).strip() or '(Sin respuesta)'
