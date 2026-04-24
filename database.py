"""DeepCore CRM Pro — Base de datos SQLite local cifrada."""
import sqlite3, os, sys, json, base64, platform, uuid
from datetime import datetime, date

# ── Cifrado XOR + base64 (clave derivada del hardware) ────────────────────────
def _clave() -> bytes:
    raw = f"{platform.node()}|{uuid.getnode()}|DC_CRM"
    import hashlib
    return hashlib.sha256(raw.encode()).digest()

def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def cifrar(texto: str) -> str:
    if not texto:
        return texto
    enc = _xor(texto.encode('utf-8'), _clave())
    return 'enc1:' + base64.b64encode(enc).decode()

def descifrar(valor: str) -> str:
    if not valor or not valor.startswith('enc1:'):
        return valor
    try:
        raw = base64.b64decode(valor[5:])
        return _xor(raw, _clave()).decode('utf-8')
    except Exception:
        return valor

# ── Ruta base de datos ─────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _BASE = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'DeepCore CRM Pro')
    os.makedirs(_BASE, exist_ok=True)
else:
    _BASE = os.path.dirname(__file__)

DB_PATH = os.path.join(_BASE, 'crm.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ══════════════════════════════════════════════════════════════════════════════
#  INICIALIZACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def inicializar():
    with get_conn() as c:
        c.executescript("""
        -- Empresas
        CREATE TABLE IF NOT EXISTS empresas (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre     TEXT NOT NULL,
            ruc        TEXT DEFAULT '',
            industria  TEXT DEFAULT '',
            sitio_web  TEXT DEFAULT '',
            email      TEXT DEFAULT '',
            telefono   TEXT DEFAULT '',
            direccion  TEXT DEFAULT '',
            notas      TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        -- Contactos
        CREATE TABLE IF NOT EXISTS contactos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT NOT NULL,
            apellido    TEXT DEFAULT '',
            empresa_id  INTEGER REFERENCES empresas(id) ON DELETE SET NULL,
            cargo       TEXT DEFAULT '',
            email       TEXT DEFAULT '',
            telefono    TEXT DEFAULT '',
            estado      TEXT DEFAULT 'Activo',
            fuente      TEXT DEFAULT '',
            notas       TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            updated_at  TEXT DEFAULT (datetime('now','localtime'))
        );

        -- Oportunidades (pipeline)
        CREATE TABLE IF NOT EXISTS oportunidades (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre        TEXT NOT NULL,
            contacto_id   INTEGER REFERENCES contactos(id) ON DELETE SET NULL,
            empresa_id    INTEGER REFERENCES empresas(id) ON DELETE SET NULL,
            valor         REAL DEFAULT 0,
            etapa         TEXT DEFAULT 'Prospecto',
            probabilidad  INTEGER DEFAULT 10,
            fecha_cierre  TEXT DEFAULT '',
            notas         TEXT DEFAULT '',
            created_at    TEXT DEFAULT (datetime('now','localtime')),
            updated_at    TEXT DEFAULT (datetime('now','localtime'))
        );

        -- Actividades
        CREATE TABLE IF NOT EXISTS actividades (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo            TEXT DEFAULT 'Nota',
            titulo          TEXT NOT NULL,
            descripcion     TEXT DEFAULT '',
            contacto_id     INTEGER REFERENCES contactos(id) ON DELETE CASCADE,
            oportunidad_id  INTEGER REFERENCES oportunidades(id) ON DELETE SET NULL,
            fecha           TEXT DEFAULT (datetime('now','localtime')),
            completada      INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now','localtime'))
        );

        -- Configuración
        CREATE TABLE IF NOT EXISTS config (
            clave TEXT PRIMARY KEY,
            valor TEXT
        );
        """)

        # Config por defecto
        defaults = [
            ('empresa',   'Mi Empresa'),
            ('moneda',    '$'),
            ('api_key',   ''),
            ('acento',    '#10B981'),
        ]
        for k, v in defaults:
            c.execute("INSERT OR IGNORE INTO config VALUES (?,?)", (k, v))


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════

def get_config(clave: str, default: str = '') -> str:
    try:
        with get_conn() as c:
            row = c.execute("SELECT valor FROM config WHERE clave=?", (clave,)).fetchone()
            return row['valor'] if row else default
    except Exception:
        return default

def set_config(clave: str, valor: str):
    with get_conn() as c:
        c.execute("INSERT OR REPLACE INTO config VALUES (?,?)", (clave, valor))


# ══════════════════════════════════════════════════════════════════════════════
#  EMPRESAS
# ══════════════════════════════════════════════════════════════════════════════

def crear_empresa(nombre, ruc='', industria='', sitio_web='', email='', telefono='', direccion='', notas='') -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO empresas (nombre,ruc,industria,sitio_web,email,telefono,direccion,notas) VALUES (?,?,?,?,?,?,?,?)",
            (nombre, ruc, industria, sitio_web, email, telefono, direccion, notas)
        )
        return cur.lastrowid

def listar_empresas(busqueda: str = '') -> list:
    with get_conn() as c:
        if busqueda:
            rows = c.execute(
                "SELECT * FROM empresas WHERE nombre LIKE ? OR ruc LIKE ? OR industria LIKE ? ORDER BY nombre",
                (f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%')
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM empresas ORDER BY nombre").fetchall()
        return [dict(r) for r in rows]

def actualizar_empresa(id: int, **campos):
    if not campos:
        return
    sets = ', '.join(f"{k}=?" for k in campos)
    vals = list(campos.values()) + [id]
    with get_conn() as c:
        c.execute(f"UPDATE empresas SET {sets} WHERE id=?", vals)

def eliminar_empresa(id: int):
    with get_conn() as c:
        c.execute("DELETE FROM empresas WHERE id=?", (id,))

def contar_contactos_empresa(empresa_id: int) -> int:
    with get_conn() as c:
        row = c.execute("SELECT COUNT(*) as n FROM contactos WHERE empresa_id=?", (empresa_id,)).fetchone()
        return row['n'] if row else 0


# ══════════════════════════════════════════════════════════════════════════════
#  CONTACTOS
# ══════════════════════════════════════════════════════════════════════════════

def crear_contacto(nombre, apellido='', empresa_id=None, cargo='', email='', telefono='',
                   estado='Activo', fuente='', notas='') -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO contactos (nombre,apellido,empresa_id,cargo,email,telefono,estado,fuente,notas) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (nombre, apellido, empresa_id, cargo, email, telefono, estado, fuente, notas)
        )
        return cur.lastrowid

def listar_contactos(busqueda: str = '', empresa_id: int = None, estado: str = '') -> list:
    sql = """
        SELECT c.*, e.nombre as empresa_nombre
        FROM contactos c
        LEFT JOIN empresas e ON c.empresa_id = e.id
        WHERE 1=1
    """
    params = []
    if busqueda:
        sql += " AND (c.nombre LIKE ? OR c.apellido LIKE ? OR c.email LIKE ? OR c.telefono LIKE ?)"
        params += [f'%{busqueda}%'] * 4
    if empresa_id:
        sql += " AND c.empresa_id = ?"
        params.append(empresa_id)
    if estado:
        sql += " AND c.estado = ?"
        params.append(estado)
    sql += " ORDER BY c.nombre, c.apellido"

    with get_conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]

def obtener_contacto(id: int) -> dict | None:
    with get_conn() as c:
        row = c.execute("""
            SELECT c.*, e.nombre as empresa_nombre
            FROM contactos c LEFT JOIN empresas e ON c.empresa_id=e.id
            WHERE c.id=?
        """, (id,)).fetchone()
        return dict(row) if row else None

def actualizar_contacto(id: int, **campos):
    if not campos:
        return
    campos['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sets = ', '.join(f"{k}=?" for k in campos)
    vals = list(campos.values()) + [id]
    with get_conn() as c:
        c.execute(f"UPDATE contactos SET {sets} WHERE id=?", vals)

def eliminar_contacto(id: int):
    with get_conn() as c:
        c.execute("DELETE FROM contactos WHERE id=?", (id,))

def total_contactos() -> int:
    with get_conn() as c:
        return c.execute("SELECT COUNT(*) FROM contactos").fetchone()[0]


# ══════════════════════════════════════════════════════════════════════════════
#  OPORTUNIDADES / PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

ETAPAS = ['Prospecto', 'Calificado', 'Propuesta', 'Negociación', 'Ganado', 'Perdido']
PROB_ETAPA = {'Prospecto': 10, 'Calificado': 25, 'Propuesta': 50, 'Negociación': 75, 'Ganado': 100, 'Perdido': 0}

def crear_oportunidad(nombre, contacto_id=None, empresa_id=None, valor=0,
                      etapa='Prospecto', fecha_cierre='', notas='') -> int:
    prob = PROB_ETAPA.get(etapa, 10)
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO oportunidades (nombre,contacto_id,empresa_id,valor,etapa,probabilidad,fecha_cierre,notas) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (nombre, contacto_id, empresa_id, valor, etapa, prob, fecha_cierre, notas)
        )
        return cur.lastrowid

def listar_oportunidades(etapa: str = '', busqueda: str = '') -> list:
    sql = """
        SELECT o.*, c.nombre as contacto_nombre, c.apellido as contacto_apellido,
               e.nombre as empresa_nombre
        FROM oportunidades o
        LEFT JOIN contactos c ON o.contacto_id = c.id
        LEFT JOIN empresas  e ON o.empresa_id  = e.id
        WHERE 1=1
    """
    params = []
    if etapa:
        sql += " AND o.etapa=?"
        params.append(etapa)
    if busqueda:
        sql += " AND (o.nombre LIKE ? OR c.nombre LIKE ? OR e.nombre LIKE ?)"
        params += [f'%{busqueda}%'] * 3
    sql += " ORDER BY o.created_at DESC"

    with get_conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]

def actualizar_oportunidad(id: int, **campos):
    if not campos:
        return
    if 'etapa' in campos:
        campos['probabilidad'] = PROB_ETAPA.get(campos['etapa'], 10)
    campos['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sets = ', '.join(f"{k}=?" for k in campos)
    vals = list(campos.values()) + [id]
    with get_conn() as c:
        c.execute(f"UPDATE oportunidades SET {sets} WHERE id=?", vals)

def eliminar_oportunidad(id: int):
    with get_conn() as c:
        c.execute("DELETE FROM oportunidades WHERE id=?", (id,))

def stats_pipeline() -> dict:
    with get_conn() as c:
        rows = c.execute("""
            SELECT etapa, COUNT(*) as n, COALESCE(SUM(valor),0) as total
            FROM oportunidades GROUP BY etapa
        """).fetchall()
        result = {r['etapa']: {'n': r['n'], 'total': r['total']} for r in rows}
        abiertas = c.execute(
            "SELECT COUNT(*) FROM oportunidades WHERE etapa NOT IN ('Ganado','Perdido')"
        ).fetchone()[0]
        valor_pipe = c.execute(
            "SELECT COALESCE(SUM(valor*probabilidad/100.0),0) FROM oportunidades WHERE etapa NOT IN ('Ganado','Perdido')"
        ).fetchone()[0]
        return {'por_etapa': result, 'abiertas': abiertas, 'valor_ponderado': valor_pipe}


# ══════════════════════════════════════════════════════════════════════════════
#  ACTIVIDADES
# ══════════════════════════════════════════════════════════════════════════════

TIPOS_ACTIVIDAD = ['Nota', 'Llamada', 'Email', 'Reunión', 'Tarea']

def crear_actividad(tipo, titulo, descripcion='', contacto_id=None, oportunidad_id=None,
                    fecha=None, completada=False) -> int:
    if fecha is None:
        fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO actividades (tipo,titulo,descripcion,contacto_id,oportunidad_id,fecha,completada) "
            "VALUES (?,?,?,?,?,?,?)",
            (tipo, titulo, descripcion, contacto_id, oportunidad_id, fecha, int(completada))
        )
        return cur.lastrowid

def listar_actividades(contacto_id: int = None, oportunidad_id: int = None,
                       tipo: str = '', completada: int = -1, limite: int = 100) -> list:
    sql = """
        SELECT a.*, c.nombre as contacto_nombre, c.apellido as contacto_apellido,
               o.nombre as oportunidad_nombre
        FROM actividades a
        LEFT JOIN contactos c ON a.contacto_id = c.id
        LEFT JOIN oportunidades o ON a.oportunidad_id = o.id
        WHERE 1=1
    """
    params = []
    if contacto_id:
        sql += " AND a.contacto_id=?"
        params.append(contacto_id)
    if oportunidad_id:
        sql += " AND a.oportunidad_id=?"
        params.append(oportunidad_id)
    if tipo:
        sql += " AND a.tipo=?"
        params.append(tipo)
    if completada >= 0:
        sql += " AND a.completada=?"
        params.append(completada)
    sql += f" ORDER BY a.fecha DESC LIMIT {limite}"

    with get_conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]

def completar_actividad(id: int):
    with get_conn() as c:
        c.execute("UPDATE actividades SET completada=1 WHERE id=?", (id,))

def eliminar_actividad(id: int):
    with get_conn() as c:
        c.execute("DELETE FROM actividades WHERE id=?", (id,))

def actividades_pendientes_hoy() -> int:
    hoy = date.today().strftime('%Y-%m-%d')
    with get_conn() as c:
        return c.execute(
            "SELECT COUNT(*) FROM actividades WHERE completada=0 AND fecha LIKE ?",
            (f'{hoy}%',)
        ).fetchone()[0]


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD STATS
# ══════════════════════════════════════════════════════════════════════════════

def stats_dashboard() -> dict:
    with get_conn() as c:
        contactos  = c.execute("SELECT COUNT(*) FROM contactos").fetchone()[0]
        empresas   = c.execute("SELECT COUNT(*) FROM empresas").fetchone()[0]
        pipe       = stats_pipeline()
        act_hoy    = actividades_pendientes_hoy()
        ult_actvs  = listar_actividades(limite=8)
        prox_ops   = listar_oportunidades()
        prox_ops   = [o for o in prox_ops if o['etapa'] not in ('Ganado', 'Perdido')][:6]
        return {
            'contactos':       contactos,
            'empresas':        empresas,
            'oportunidades':   pipe['abiertas'],
            'valor_pipeline':  pipe['valor_ponderado'],
            'act_hoy':         act_hoy,
            'ultimas_act':     ult_actvs,
            'proximas_ops':    prox_ops,
        }
