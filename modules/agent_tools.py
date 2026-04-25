"""DeepCore CRM Pro — Definición de herramientas del agente IA."""
import database as db
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════════════
#  ESQUEMA DE HERRAMIENTAS (formato Claude API tool_use)
# ══════════════════════════════════════════════════════════════════════════════

TOOLS = [
    {
        "name": "buscar_contactos",
        "description": (
            "Busca contactos en el CRM por nombre, apellido, email o empresa. "
            "Úsalo siempre ANTES de crear uno para verificar que no exista. "
            "También úsalo cuando el usuario pida ver, listar o encontrar contactos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "busqueda": {"type": "string", "description": "Texto a buscar en nombre, email o empresa"},
                "estado":   {"type": "string", "description": "Filtrar por: Activo, Lead, Cliente, Inactivo, Ex-cliente (opcional)"}
            }
        }
    },
    {
        "name": "crear_contacto",
        "description": (
            "Crea un nuevo contacto en el CRM. Si el usuario menciona empresa, "
            "busca primero la empresa con buscar_empresas y pasa su ID. "
            "Fuente por defecto 'Asistente IA'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre":        {"type": "string",  "description": "Nombre (requerido)"},
                "apellido":      {"type": "string",  "description": "Apellido"},
                "empresa_id":    {"type": "integer", "description": "ID de la empresa (usa buscar_empresas para obtenerlo)"},
                "cargo":         {"type": "string",  "description": "Cargo o puesto"},
                "email":         {"type": "string",  "description": "Email"},
                "telefono":      {"type": "string",  "description": "Teléfono"},
                "estado":        {"type": "string",  "description": "Activo, Lead, Cliente"},
                "notas":         {"type": "string",  "description": "Notas adicionales"}
            },
            "required": ["nombre"]
        }
    },
    {
        "name": "buscar_empresas",
        "description": "Busca empresas registradas en el CRM. Úsalo para obtener el ID antes de crear contactos u oportunidades.",
        "input_schema": {
            "type": "object",
            "properties": {
                "busqueda": {"type": "string", "description": "Nombre, RUC o industria a buscar"}
            }
        }
    },
    {
        "name": "crear_empresa",
        "description": "Crea una nueva empresa en el CRM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre":    {"type": "string", "description": "Nombre de la empresa (requerido)"},
                "ruc":       {"type": "string", "description": "RUC o número de identificación"},
                "industria": {"type": "string", "description": "Sector: Tecnología, Comercio, Manufactura, Salud, Educación, Construcción, Finanzas, Servicios, Otro"},
                "email":     {"type": "string", "description": "Email corporativo"},
                "telefono":  {"type": "string", "description": "Teléfono"},
                "sitio_web": {"type": "string", "description": "Sitio web"},
                "notas":     {"type": "string", "description": "Notas"}
            },
            "required": ["nombre"]
        }
    },
    {
        "name": "buscar_oportunidades",
        "description": "Lista oportunidades del pipeline. Úsalo para ver el estado de ventas, filtrar por etapa o buscar una oportunidad específica.",
        "input_schema": {
            "type": "object",
            "properties": {
                "etapa":    {"type": "string",  "description": "Filtrar por: Prospecto, Calificado, Propuesta, Negociación, Ganado, Perdido"},
                "busqueda": {"type": "string",  "description": "Texto en nombre o empresa"}
            }
        }
    },
    {
        "name": "crear_oportunidad",
        "description": (
            "Crea una nueva oportunidad de venta en el pipeline. "
            "Etapas válidas: Prospecto, Calificado, Propuesta, Negociación, Ganado, Perdido."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre":       {"type": "string",  "description": "Nombre/descripción de la oportunidad (requerido)"},
                "valor":        {"type": "number",  "description": "Valor monetario estimado en USD"},
                "etapa":        {"type": "string",  "description": "Etapa inicial (default: Prospecto)"},
                "empresa_id":   {"type": "integer", "description": "ID de la empresa"},
                "contacto_id":  {"type": "integer", "description": "ID del contacto principal"},
                "fecha_cierre": {"type": "string",  "description": "Fecha estimada de cierre YYYY-MM-DD"},
                "notas":        {"type": "string",  "description": "Notas adicionales"}
            },
            "required": ["nombre"]
        }
    },
    {
        "name": "actualizar_etapa_oportunidad",
        "description": "Mueve una oportunidad a otra etapa del pipeline. Úsalo cuando el usuario diga que avanzó o perdió una venta.",
        "input_schema": {
            "type": "object",
            "properties": {
                "oportunidad_id": {"type": "integer", "description": "ID de la oportunidad"},
                "etapa":          {"type": "string",  "description": "Nueva etapa: Prospecto, Calificado, Propuesta, Negociación, Ganado, Perdido"}
            },
            "required": ["oportunidad_id", "etapa"]
        }
    },
    {
        "name": "crear_actividad",
        "description": "Registra una actividad: llamada, reunión, email, tarea o nota. Úsalo cuando el usuario quiera dejar registro de una interacción o programar una tarea.",
        "input_schema": {
            "type": "object",
            "properties": {
                "titulo":        {"type": "string",  "description": "Descripción de la actividad (requerido)"},
                "tipo":          {"type": "string",  "description": "Nota, Llamada, Email, Reunión, Tarea"},
                "contacto_id":   {"type": "integer", "description": "ID del contacto relacionado"},
                "oportunidad_id":{"type": "integer", "description": "ID de la oportunidad relacionada"},
                "fecha":         {"type": "string",  "description": "Fecha YYYY-MM-DD (default: hoy)"},
                "notas":         {"type": "string",  "description": "Detalle de la actividad"}
            },
            "required": ["titulo"]
        }
    },
    {
        "name": "listar_pendientes",
        "description": "Lista actividades pendientes del usuario. Úsalo para ver qué hay que hacer hoy, esta semana, o qué está vencido.",
        "input_schema": {
            "type": "object",
            "properties": {
                "solo_vencidas": {"type": "boolean", "description": "true = solo actividades con fecha pasada"},
                "limite":        {"type": "integer", "description": "Máximo de resultados (default 10)"}
            }
        }
    },
    {
        "name": "obtener_resumen_crm",
        "description": "Obtiene estadísticas generales del CRM: total contactos, empresas, pipeline, actividades. Úsalo para resúmenes ejecutivos.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "buscar_en_documentos",
        "description": (
            "Busca información dentro de los documentos adjuntos al CRM (contratos, propuestas, PDFs, etc.). "
            "Úsalo cuando el usuario pregunte por el contenido de un contrato, una propuesta o cualquier archivo. "
            "Si hay Ollama corriendo, usa IA semántica; sino usa búsqueda de texto."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query":      {"type": "string",  "description": "Pregunta o texto a buscar en los documentos (requerido)"},
                "empresa_id": {"type": "integer", "description": "Limitar búsqueda a una empresa específica (opcional)"}
            },
            "required": ["query"]
        }
    }
]


# ══════════════════════════════════════════════════════════════════════════════
#  EJECUTOR DE HERRAMIENTAS
# ══════════════════════════════════════════════════════════════════════════════

def ejecutar_herramienta(nombre: str, params: dict) -> dict:
    """Ejecuta una herramienta y retorna el resultado como dict."""
    try:
        return _EJECUTORES[nombre](params)
    except KeyError:
        return {"error": f"Herramienta desconocida: {nombre}"}
    except Exception as e:
        return {"error": str(e)}


def _buscar_contactos(p: dict) -> dict:
    rows = db.listar_contactos(busqueda=p.get('busqueda', ''), estado=p.get('estado', ''))
    return {
        "total": len(rows),
        "contactos": [
            {
                "id": r['id'],
                "nombre": f"{r.get('nombre','')} {r.get('apellido','')}".strip(),
                "empresa": r.get('empresa_nombre') or '—',
                "cargo": r.get('cargo') or '—',
                "email": r.get('email') or '—',
                "telefono": r.get('telefono') or '—',
                "estado": r.get('estado') or '—'
            }
            for r in rows[:20]
        ]
    }


def _crear_contacto(p: dict) -> dict:
    cid = db.crear_contacto(
        nombre=p.get('nombre', ''),
        apellido=p.get('apellido', ''),
        empresa_id=p.get('empresa_id'),
        cargo=p.get('cargo', ''),
        email=p.get('email', ''),
        telefono=p.get('telefono', ''),
        estado=p.get('estado', 'Lead'),
        fuente=p.get('fuente', 'Asistente IA'),
        notas=p.get('notas', '')
    )
    nombre_completo = f"{p.get('nombre','')} {p.get('apellido','')}".strip()
    return {"ok": True, "id": cid, "mensaje": f"Contacto '{nombre_completo}' creado con ID {cid}."}


def _buscar_empresas(p: dict) -> dict:
    rows = db.listar_empresas(busqueda=p.get('busqueda', ''))
    return {
        "total": len(rows),
        "empresas": [
            {
                "id": r['id'],
                "nombre": r.get('nombre', ''),
                "ruc": r.get('ruc') or '—',
                "industria": r.get('industria') or '—'
            }
            for r in rows[:10]
        ]
    }


def _crear_empresa(p: dict) -> dict:
    eid = db.crear_empresa(
        nombre=p.get('nombre', ''),
        ruc=p.get('ruc', ''),
        industria=p.get('industria', 'Otro'),
        sitio_web=p.get('sitio_web', ''),
        email=p.get('email', ''),
        telefono=p.get('telefono', ''),
        notas=p.get('notas', '')
    )
    return {"ok": True, "id": eid, "mensaje": f"Empresa '{p.get('nombre','')}' creada con ID {eid}."}


def _buscar_oportunidades(p: dict) -> dict:
    rows = db.listar_oportunidades(etapa=p.get('etapa', ''), busqueda=p.get('busqueda', ''))
    total_pipeline = sum(r.get('valor') or 0 for r in rows)
    return {
        "total": len(rows),
        "valor_total_pipeline": round(total_pipeline, 2),
        "oportunidades": [
            {
                "id": r['id'],
                "nombre": r.get('nombre', ''),
                "etapa": r.get('etapa', ''),
                "valor": r.get('valor') or 0,
                "empresa": r.get('empresa_nombre') or '—',
                "contacto": f"{r.get('contacto_nombre','')} {r.get('contacto_apellido','')}".strip() or '—',
                "fecha_cierre": (r.get('fecha_cierre') or '')[:10] or '—'
            }
            for r in rows[:15]
        ]
    }


def _crear_oportunidad(p: dict) -> dict:
    oid = db.crear_oportunidad(
        nombre=p.get('nombre', ''),
        valor=p.get('valor') or 0,
        etapa=p.get('etapa', 'Prospecto'),
        empresa_id=p.get('empresa_id'),
        contacto_id=p.get('contacto_id'),
        fecha_cierre=p.get('fecha_cierre', ''),
        notas=p.get('notas', '')
    )
    return {"ok": True, "id": oid, "mensaje": f"Oportunidad '{p.get('nombre','')}' creada en etapa {p.get('etapa','Prospecto')}."}


def _actualizar_etapa(p: dict) -> dict:
    db.actualizar_oportunidad(p['oportunidad_id'], etapa=p['etapa'])
    return {"ok": True, "mensaje": f"Oportunidad {p['oportunidad_id']} movida a etapa '{p['etapa']}'."}


def _crear_actividad(p: dict) -> dict:
    fecha = p.get('fecha') or datetime.now().strftime('%Y-%m-%d')
    aid = db.crear_actividad(
        titulo=p.get('titulo', ''),
        tipo=p.get('tipo', 'Nota'),
        contacto_id=p.get('contacto_id'),
        oportunidad_id=p.get('oportunidad_id'),
        fecha=fecha,
        notas=p.get('notas', '')
    )
    return {"ok": True, "id": aid, "mensaje": f"Actividad '{p.get('titulo','')}' registrada para {fecha}."}


def _listar_pendientes(p: dict) -> dict:
    limite = min(p.get('limite', 10), 25)
    rows = db.listar_actividades(estado='Pendiente')
    hoy = datetime.now().date().isoformat()

    if p.get('solo_vencidas'):
        rows = [r for r in rows if (r.get('fecha') or '') < hoy]

    resultado = []
    for r in rows[:limite]:
        fecha = (r.get('fecha') or '')[:10]
        vencida = fecha < hoy if fecha else False
        resultado.append({
            "id": r['id'],
            "titulo": r.get('titulo', ''),
            "tipo": r.get('tipo', ''),
            "fecha": fecha or '—',
            "vencida": vencida,
            "contacto": r.get('contacto_nombre') or '—'
        })

    return {"total": len(rows), "mostrando": len(resultado), "actividades": resultado}


def _obtener_resumen(p: dict) -> dict:
    stats = db.stats_dashboard()
    return {
        "contactos_totales": stats.get('contactos', 0),
        "empresas_totales": stats.get('empresas', 0),
        "oportunidades_abiertas": stats.get('oportunidades', 0),
        "valor_pipeline_usd": round(stats.get('valor_pipeline', 0), 2),
        "actividades_pendientes_hoy": stats.get('act_hoy', 0),
        "fecha_consulta": datetime.now().strftime('%Y-%m-%d %H:%M')
    }


def _buscar_en_documentos(p: dict) -> dict:
    from modules.doc_indexer import buscar_con_ia, ollama_disponible
    query      = p.get('query', '')
    empresa_id = p.get('empresa_id')

    # Búsqueda FTS5 siempre disponible
    hits = db.buscar_documentos_fts(query, empresa_id=empresa_id, limite=5)

    if not hits:
        return {"encontrado": False, "mensaje": "No se encontraron documentos con ese contenido."}

    # Intentar IA semántica si Ollama está corriendo
    if ollama_disponible():
        doc_ids = [h['doc_id'] for h in hits]
        documentos = []
        for did in doc_ids:
            doc = db.get_documento(did)
            if doc and doc.get('texto'):
                documentos.append({'nombre': doc['nombre'], 'texto': doc['texto']})

        respuesta_ia = buscar_con_ia(query, documentos)
        if respuesta_ia:
            return {
                "encontrado": True,
                "modo": "IA semántica (Ollama)",
                "respuesta": respuesta_ia,
                "documentos_analizados": [h['nombre'] for h in hits],
            }

    # Fallback: resultados FTS5
    return {
        "encontrado": True,
        "modo": "búsqueda de texto (FTS5)",
        "resultados": [
            {"documento": h['nombre'], "fragmento": h['fragmento'], "fecha": h['fecha']}
            for h in hits
        ],
    }


_EJECUTORES = {
    'buscar_contactos':            _buscar_contactos,
    'crear_contacto':              _crear_contacto,
    'buscar_empresas':             _buscar_empresas,
    'crear_empresa':               _crear_empresa,
    'buscar_oportunidades':        _buscar_oportunidades,
    'crear_oportunidad':           _crear_oportunidad,
    'actualizar_etapa_oportunidad':_actualizar_etapa,
    'crear_actividad':             _crear_actividad,
    'listar_pendientes':           _listar_pendientes,
    'obtener_resumen_crm':         _obtener_resumen,
    'buscar_en_documentos':        _buscar_en_documentos,
}

# Nombres legibles para el UI
NOMBRES_LEGIBLES = {
    'buscar_contactos':             'Buscando contactos',
    'crear_contacto':               'Creando contacto',
    'buscar_empresas':              'Buscando empresas',
    'crear_empresa':                'Creando empresa',
    'buscar_oportunidades':         'Buscando oportunidades',
    'crear_oportunidad':            'Creando oportunidad',
    'actualizar_etapa_oportunidad': 'Actualizando pipeline',
    'crear_actividad':              'Registrando actividad',
    'listar_pendientes':            'Consultando pendientes',
    'obtener_resumen_crm':          'Analizando CRM',
    'buscar_en_documentos':         'Analizando documentos',
}
