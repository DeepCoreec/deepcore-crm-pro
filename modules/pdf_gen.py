"""DeepCore CRM Pro — Generación de reportes PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime

VERDE  = colors.HexColor('#10B981')
OSCURO = colors.HexColor('#0c0c0e')
GRIS   = colors.HexColor('#F5F5F5')
GRIS2  = colors.HexColor('#EEEEEE')
BLANCO = colors.white
AZUL   = colors.HexColor('#60A5FA')


def _estilos():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle('Titulo',    fontSize=20, textColor=BLANCO,   alignment=TA_LEFT, fontName='Helvetica-Bold'))
    s.add(ParagraphStyle('Sub',       fontSize=10, textColor=BLANCO,   alignment=TA_LEFT))
    s.add(ParagraphStyle('SecHeader', fontSize=12, textColor=OSCURO,   fontName='Helvetica-Bold', spaceAfter=4))
    s.add(ParagraphStyle('Normal2',   fontSize=9,  textColor=colors.HexColor('#333333')))
    s.add(ParagraphStyle('Derecha',   fontSize=9,  alignment=TA_RIGHT, textColor=colors.HexColor('#333333')))
    s.add(ParagraphStyle('Total',     fontSize=12, fontName='Helvetica-Bold', alignment=TA_RIGHT, textColor=OSCURO))
    return s


def _header(empresa: str, ruc: str = '') -> Table:
    s = _estilos()
    sub_txt = f'RUC: {ruc}' if ruc else 'DeepCore CRM Pro'
    data = [[
        Paragraph(f'<b>{empresa}</b>', s['Titulo']),
        Paragraph(f'{sub_txt}<br/>Reporte generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}', s['Sub'])
    ]]
    t = Table(data, colWidths=[10*cm, 8.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), OSCURO),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING',    (0,0), (-1,-1), 14),
        ('ROUNDEDCORNERS', [6]),
    ]))
    return t


def generar_reporte_contactos(contactos: list, config: dict, ruta: str) -> str:
    doc = SimpleDocTemplate(ruta, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    s   = _estilos()
    story = []

    empresa = config.get('empresa', 'Mi Empresa')
    ruc     = config.get('ruc', '')

    story.append(_header(empresa, ruc))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("REPORTE DE CONTACTOS", s['SecHeader']))
    story.append(HRFlowable(width='100%', thickness=1, color=VERDE, spaceAfter=8))
    story.append(Spacer(1, 0.3*cm))

    if not contactos:
        story.append(Paragraph("No hay contactos registrados.", s['Normal2']))
    else:
        headers = ['Nombre', 'Empresa', 'Cargo', 'Email', 'Teléfono', 'Estado']
        data = [headers]
        for c in contactos:
            nombre = f"{c.get('nombre','')} {c.get('apellido','')}".strip()
            data.append([
                nombre,
                c.get('empresa_nombre') or '—',
                c.get('cargo') or '—',
                c.get('email') or '—',
                c.get('telefono') or '—',
                c.get('estado') or '—',
            ])

        colWidths = [4*cm, 3.5*cm, 3*cm, 4*cm, 2.5*cm, 2*cm]
        t = Table(data, colWidths=colWidths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,0),  OSCURO),
            ('TEXTCOLOR',   (0,0), (-1,0),  BLANCO),
            ('FONTNAME',    (0,0), (-1,0),  'Helvetica-Bold'),
            ('FONTSIZE',    (0,0), (-1,0),  9),
            ('BACKGROUND',  (0,1), (-1,-1), BLANCO),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[BLANCO, GRIS]),
            ('FONTSIZE',    (0,1), (-1,-1), 8),
            ('FONTNAME',    (0,1), (-1,-1), 'Helvetica'),
            ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
            ('ROWHEIGHT',   (0,0), (-1,-1), 18),
            ('PADDING',     (0,0), (-1,-1), 4),
        ]))
        story.append(t)

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"Total: {len(contactos)} contacto(s)", s['Total']))

    doc.build(story)
    return ruta


def generar_reporte_pipeline(oportunidades: list, config: dict, ruta: str) -> str:
    doc = SimpleDocTemplate(ruta, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    s       = _estilos()
    story   = []
    empresa = config.get('empresa', 'Mi Empresa')
    moneda  = config.get('moneda', '$')

    story.append(_header(empresa))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("REPORTE DE PIPELINE DE VENTAS", s['SecHeader']))
    story.append(HRFlowable(width='100%', thickness=1, color=VERDE, spaceAfter=8))
    story.append(Spacer(1, 0.3*cm))

    if not oportunidades:
        story.append(Paragraph("No hay oportunidades registradas.", s['Normal2']))
    else:
        headers = ['Oportunidad', 'Contacto', 'Valor', 'Etapa', 'Prob.', 'Cierre']
        data = [headers]
        total_valor = 0
        for o in oportunidades:
            contacto = f"{o.get('contacto_nombre','') or ''} {o.get('contacto_apellido','') or ''}".strip() or '—'
            valor    = o.get('valor', 0) or 0
            total_valor += valor
            data.append([
                o.get('nombre', ''),
                contacto,
                f"{moneda}{valor:,.2f}",
                o.get('etapa', ''),
                f"{o.get('probabilidad',0)}%",
                o.get('fecha_cierre', '') or '—',
            ])

        colWidths = [5*cm, 3.5*cm, 2.5*cm, 2.5*cm, 1.5*cm, 3*cm]
        t = Table(data, colWidths=colWidths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,0),  OSCURO),
            ('TEXTCOLOR',   (0,0), (-1,0),  BLANCO),
            ('FONTNAME',    (0,0), (-1,0),  'Helvetica-Bold'),
            ('FONTSIZE',    (0,0), (-1,0),  9),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[BLANCO, GRIS]),
            ('FONTSIZE',    (0,1), (-1,-1), 8),
            ('FONTNAME',    (0,1), (-1,-1), 'Helvetica'),
            ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
            ('ROWHEIGHT',   (0,0), (-1,-1), 18),
            ('PADDING',     (0,0), (-1,-1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"Valor total pipeline: {moneda}{total_valor:,.2f}", s['Total']))

    doc.build(story)
    return ruta
