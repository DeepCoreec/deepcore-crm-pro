"""
DeepCore — Sistema de Licencias Universal v2
=============================================
Una sola clave funciona para todos los programas DeepCore,
pero está bloqueada al hardware de la computadora donde se activa.

Flujo de validación:
  1. Online: consulta el servidor con (clave + hardware_id + programa)
  2. Sin internet: usa caché local (válida 3 días)
  3. Sin caché: fallback HMAC local (valida formato, avisa offline)
"""
import base64, hashlib, hmac, json, os, platform, sys, time, urllib.request, uuid
from datetime import date

_SERVER = base64.b64decode(
    b'aHR0cHM6Ly93ZWItcHJvZHVjdGlvbi0yNThjYi51cC5yYWlsd2F5LmFwcA=='
).decode()
_SECRET  = base64.b64decode(b'RENfTUFTVEVSXzIwMjZfJEsjbVA5IXhady1VTklWRVJTQUw=')
_PROG_ID = 'CRM'
_CACHE_TTL = 3 * 24 * 3600
DIAS_GRACIA = 14


def get_hardware_id() -> str:
    try:
        raw = '|'.join([platform.node(), str(uuid.getnode()), platform.processor() or platform.machine()])
        return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    except Exception:
        return hashlib.sha256(platform.node().encode()).hexdigest()[:16].upper()


def _cache_path() -> str:
    base = os.environ.get('APPDATA', os.path.expanduser('~'))
    d = os.path.join(base, 'DeepCore CRM Pro')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'lic_cache.json')


def _normalizar(key: str) -> str:
    return key.upper().replace('-', '').replace(' ', '')


def _leer_cache(key: str):
    try:
        with open(_cache_path(), encoding='utf-8') as f:
            c = json.load(f)
        if (c.get('clave') == _normalizar(key)
                and c.get('hw') == get_hardware_id()
                and time.time() - c.get('ts', 0) < _CACHE_TTL):
            return c
    except Exception:
        pass
    return None


def _guardar_cache(key: str, data: dict):
    try:
        d = dict(data)
        d['clave'] = _normalizar(key)
        d['hw']    = get_hardware_id()
        d['ts']    = time.time()
        with open(_cache_path(), 'w', encoding='utf-8') as f:
            json.dump(d, f)
    except Exception:
        pass


def _llave_guardada_path() -> str:
    base = os.environ.get('APPDATA', os.path.expanduser('~'))
    return os.path.join(base, 'DeepCore CRM Pro', 'key.dat')


def llave_guardada() -> str:
    try:
        with open(_llave_guardada_path(), encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ''


def guardar_llave(key: str):
    try:
        p = _llave_guardada_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(key.strip())
    except Exception:
        pass


def validar_online(key: str) -> dict | None:
    try:
        hw  = get_hardware_id()
        url = f'{_SERVER}/api/validar?clave={_normalizar(key)}&hw={hw}&prog={_PROG_ID}'
        req = urllib.request.Request(url, headers={'User-Agent': f'DeepCore-{_PROG_ID}-Pro/2.0'})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read())
        _guardar_cache(key, data)
        return data
    except Exception:
        return None


def _validar_formato(key: str) -> tuple:
    key = _normalizar(key)
    if len(key) != 16:
        return False, 0, "Formato de clave inválido (debe ser XXXX-XXXX-XXXX-XXXX)"
    payload      = key[:8]
    mac_recibido = key[8:]
    mac_esperado = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:8].upper()
    if mac_recibido != mac_esperado:
        return False, 0, "Clave de licencia inválida."
    try:
        year  = int(payload[0:4])
        month = int(payload[4:6])
        meses = int(payload[6:8])
        inicio = date(year, month, 1)
        end_month = month + meses
        end_year  = year + (end_month - 1) // 12
        end_month = (end_month - 1) % 12 + 1
        fin = date(end_year, end_month, 1)
        hoy = date.today()
        if hoy < inicio:
            return False, 0, f"Esta licencia aún no ha iniciado. Válida desde: {inicio.strftime('%d/%m/%Y')}"
        if hoy >= fin:
            dias_venc = (hoy - fin).days
            if dias_venc <= DIAS_GRACIA:
                return True, -dias_venc, f"Licencia expirada hace {dias_venc} día(s). Renueva pronto."
            return False, -dias_venc, "Licencia expirada. Contacta a DeepCore Systems para renovar."
        return True, (fin - hoy).days, f"Licencia válida — {(fin-hoy).days} días restantes (sin conexión)"
    except (ValueError, OverflowError):
        return False, 0, "No se pudo leer la información de la clave."


def estado_licencia(key: str) -> dict:
    hw = get_hardware_id()

    # 1. Online
    data = validar_online(key)
    if data:
        valida = data.get('valida', False)
        dias   = data.get('dias', 0)
        msg    = data.get('mensaje', '')
        return {
            'valida': valida, 'dias': dias, 'mensaje': msg,
            'color': '#10B981' if valida else '#EF4444',
            'icono': '●' if valida else '○',
            'advertir': valida and dias < 14,
            'hardware_id': hw, 'fuente': 'online',
        }

    # 2. Caché
    cache = _leer_cache(key)
    if cache:
        valida = cache.get('valida', False)
        dias   = cache.get('dias', 0)
        return {
            'valida': valida, 'dias': dias,
            'mensaje': cache.get('mensaje', '') + ' (caché offline)',
            'color': '#F59E0B' if valida else '#EF4444',
            'icono': '●' if valida else '○',
            'advertir': True, 'hardware_id': hw, 'fuente': 'cache',
        }

    # 3. Fallback HMAC
    valida, dias, msg = _validar_formato(key)
    return {
        'valida': valida, 'dias': dias, 'mensaje': msg + ' [SIN CONEXIÓN]',
        'color': '#F59E0B' if valida else '#EF4444',
        'icono': '●' if valida else '○',
        'advertir': True, 'hardware_id': hw, 'fuente': 'local',
    }


def validar_llave(key: str) -> tuple[bool, str]:
    r = estado_licencia(key)
    return r['valida'], r['mensaje']
