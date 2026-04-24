"""DeepCore CRM Pro — Motor de agente con tool_use (Claude API + Ollama)."""
import json
import requests
from modules.agent_tools import TOOLS, ejecutar_herramienta, NOMBRES_LEGIBLES

_CLAUDE_URL  = "https://api.anthropic.com/v1/messages"
_OLLAMA_URL  = "http://localhost:11434/v1/chat/completions"
_OLLAMA_TAGS = "http://localhost:11434/api/tags"

_CLAUDE_HEADERS = {
    "anthropic-version": "2023-06-01",
    "content-type":      "application/json",
}
_MODELOS_CLAUDE = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}
_MAX_ITER = 8

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

_ESCRIBE = {
    'crear_contacto', 'crear_empresa', 'crear_oportunidad',
    'actualizar_etapa_oportunidad', 'crear_actividad'
}


# ── Utilidades Ollama ────────────────────────────────────────────────────────

def ollama_disponible() -> bool:
    """Retorna True si Ollama está corriendo localmente."""
    try:
        r = requests.get(_OLLAMA_TAGS, timeout=2)
        return r.ok
    except Exception:
        return False


def ollama_modelos() -> list[str]:
    """Lista modelos instalados en Ollama."""
    try:
        r = requests.get(_OLLAMA_TAGS, timeout=3)
        if r.ok:
            return [m['name'] for m in r.json().get('models', [])]
    except Exception:
        pass
    return []


def _tools_to_openai(tools: list) -> list:
    """Convierte TOOLS de formato Claude a formato OpenAI (Ollama)."""
    return [
        {
            "type": "function",
            "function": {
                "name":        t["name"],
                "description": t.get("description", ""),
                "parameters":  t.get("input_schema", {"type": "object", "properties": {}}),
            }
        }
        for t in tools
    ]


# ── Motor principal ───────────────────────────────────────────────────────────

class AgentEngine:
    """Ejecuta el loop de tool_use — soporta Claude API y Ollama (local)."""

    def __init__(
        self,
        api_key:           str  = '',
        modelo:            str  = 'haiku',
        backend:           str  = 'claude',   # 'claude' | 'ollama'
        ollama_modelo:     str  = 'llama3.2',
        on_tool_start      = None,
        on_tool_done       = None,
        on_datos_cambiados = None,
    ):
        self.api_key            = api_key
        self.modelo             = _MODELOS_CLAUDE.get(modelo, _MODELOS_CLAUDE['haiku'])
        self.backend            = backend
        self.ollama_modelo      = ollama_modelo
        self.on_tool_start      = on_tool_start
        self.on_tool_done       = on_tool_done
        self.on_datos_cambiados = on_datos_cambiados

    # ── API pública ───────────────────────────────────────────────────────────

    def ejecutar(self, mensaje: str, historial: list | None = None) -> str:
        if self.backend == 'ollama':
            return self._ejecutar_ollama(mensaje, historial)
        return self._ejecutar_claude(mensaje, historial)

    # ── Backend Claude ────────────────────────────────────────────────────────

    def _ejecutar_claude(self, mensaje: str, historial: list | None) -> str:
        if not self.api_key or len(self.api_key) < 10:
            return (
                "Para activar el Agente IA necesitas configurar tu API key de Claude.\n"
                "Ve a Configuración → API key y pega tu clave de Anthropic Console.\n\n"
                "También puedes usar Ollama (gratis, sin internet) si lo tienes instalado."
            )

        messages = list(historial or [])
        messages.append({"role": "user", "content": mensaje})
        content  = []

        for _ in range(_MAX_ITER):
            response    = self._llamar_claude(messages)
            stop_reason = response.get('stop_reason')
            content     = response.get('content', [])
            messages.append({"role": "assistant", "content": content})

            if stop_reason == 'end_turn':
                return self._extraer_texto_claude(content)

            if stop_reason == 'tool_use':
                tool_results = []
                for bloque in content:
                    if bloque.get('type') != 'tool_use':
                        continue
                    nombre  = bloque['name']
                    params  = bloque.get('input', {})
                    tool_id = bloque['id']
                    legible = NOMBRES_LEGIBLES.get(nombre, nombre)

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
            break

        return self._extraer_texto_claude(content)

    def _llamar_claude(self, messages: list) -> dict:
        headers = {**_CLAUDE_HEADERS, "x-api-key": self.api_key}
        payload = {
            "model":      self.modelo,
            "max_tokens": 4096,
            "system":     _SYSTEM,
            "tools":      TOOLS,
            "messages":   messages,
        }
        resp = requests.post(_CLAUDE_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 401:
            raise RuntimeError("API key inválida. Verifica tu clave en Configuración.")
        if resp.status_code == 429:
            raise RuntimeError("Límite de uso alcanzado. Intenta en unos segundos.")
        if not resp.ok:
            raise RuntimeError(f"Error API {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    @staticmethod
    def _extraer_texto_claude(content: list) -> str:
        partes = [b.get('text', '') for b in content if b.get('type') == 'text']
        return '\n'.join(partes).strip() or '(Sin respuesta)'

    # ── Backend Ollama ────────────────────────────────────────────────────────

    def _ejecutar_ollama(self, mensaje: str, historial: list | None) -> str:
        # Construir historial en formato OpenAI
        messages = [{"role": "system", "content": _SYSTEM}]
        for h in (historial or []):
            role    = h.get("role", "user")
            content = h.get("content", "")
            if isinstance(content, list):
                # Convertir content list de Claude a texto plano para Ollama
                content = ' '.join(
                    b.get('text', '') for b in content if b.get('type') == 'text'
                ).strip()
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": mensaje})

        last_msg = {}
        for _ in range(_MAX_ITER):
            last_msg = self._llamar_ollama(messages)
            tool_calls = last_msg.get("tool_calls") or []

            if not tool_calls:
                return last_msg.get("content") or "(Sin respuesta)"

            # Agregar respuesta del asistente (con tool_calls) al historial
            messages.append({
                "role":       "assistant",
                "content":    last_msg.get("content", "") or "",
                "tool_calls": tool_calls,
            })

            # Ejecutar cada herramienta
            for tc in tool_calls:
                fn      = tc.get("function", {})
                nombre  = fn.get("name", "")
                try:
                    params = json.loads(fn.get("arguments") or "{}")
                except Exception:
                    params = {}
                tool_id = tc.get("id", nombre)
                legible = NOMBRES_LEGIBLES.get(nombre, nombre)

                if self.on_tool_start:
                    self.on_tool_start(legible)

                resultado = ejecutar_herramienta(nombre, params)
                ok = "error" not in resultado

                if ok and nombre in _ESCRIBE and self.on_datos_cambiados:
                    self.on_datos_cambiados()

                if self.on_tool_done:
                    self.on_tool_done(legible, ok)

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_id,
                    "content":      json.dumps(resultado, ensure_ascii=False),
                })

        return last_msg.get("content") or "(Sin respuesta)"

    def _llamar_ollama(self, messages: list) -> dict:
        payload = {
            "model":    self.ollama_modelo,
            "messages": messages,
            "tools":    _tools_to_openai(TOOLS),
            "stream":   False,
        }
        resp = requests.post(_OLLAMA_URL, json=payload, timeout=120)
        if not resp.ok:
            raise RuntimeError(
                f"Error Ollama ({resp.status_code}). "
                "Asegúrate de que Ollama esté corriendo: ollama serve"
            )
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {})
