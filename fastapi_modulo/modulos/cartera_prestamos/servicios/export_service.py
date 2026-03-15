from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import StringIO

from fastapi_modulo.modulos.cartera_prestamos.repositorios import cartera_repository, cobranza_repository
from fastapi_modulo.modulos.cartera_prestamos.servicios.gestion_service import obtener_snapshot_gestion
from fastapi_modulo.modulos.cartera_prestamos.servicios.mesa_control_service import obtener_snapshot_mesa_control
from fastapi_modulo.modulos.cartera_prestamos.servicios.recuperacion_service import obtener_snapshot_recuperacion


def exportar_cartera_vencida_excel() -> bytes:
    db = cartera_repository.get_db()
    try:
        rows = []
        for credito in cartera_repository.list_creditos(db):
            if credito.dias_mora <= 0:
                continue
            saldo_total = Decimal(str(credito.saldo.saldo_total if credito.saldo else credito.saldo_capital or 0))
            rows.append(
                {
                    "Credito": credito.numero_credito,
                    "Cliente": credito.cliente.nombre_completo if credito.cliente else f"Cliente {credito.cliente_id}",
                    "Sucursal": credito.sucursal or "Sin sucursal",
                    "Asesor": credito.oficial or "Sin asesor",
                    "Producto": credito.producto or "Sin producto",
                    "Dias mora": credito.dias_mora,
                    "Bucket": credito.bucket_mora,
                    "Saldo vencido": saldo_total,
                }
            )
        rows.sort(key=lambda item: (item["Dias mora"], item["Saldo vencido"]), reverse=True)
        return _build_excel_worksheet("Cartera vencida", rows)
    finally:
        db.close()


def exportar_promesas_pago_excel() -> bytes:
    db = cartera_repository.get_db()
    try:
        rows = []
        for promesa in cobranza_repository.list_promesas_pago(db):
            credito = promesa.credito
            rows.append(
                {
                    "Credito": credito.numero_credito if credito else "",
                    "Cliente": credito.cliente.nombre_completo if credito and credito.cliente else "",
                    "Fecha compromiso": promesa.fecha_compromiso.isoformat(),
                    "Fecha promesa": promesa.fecha_promesa.isoformat(),
                    "Estado": promesa.estado,
                    "Monto comprometido": Decimal(str(promesa.monto_comprometido or 0)),
                    "Monto cumplido": Decimal(str(promesa.monto_cumplido or 0)),
                    "Observaciones": promesa.observaciones or "",
                }
            )
        return _build_excel_worksheet("Promesas de pago", rows)
    finally:
        db.close()


def exportar_seguimiento_por_gestor_excel() -> bytes:
    snapshot = obtener_snapshot_recuperacion()
    rows = [
        {
            "Gestor": item["gestor"],
            "Gestiones": item["gestiones"],
            "Efectividad": Decimal(str(item["efectividad"])),
        }
        for item in snapshot["efectividad_por_gestor"]
    ]
    return _build_excel_worksheet("Seguimiento por gestor", rows)


def exportar_aging_cartera_excel() -> bytes:
    snapshot = obtener_snapshot_mesa_control()
    rows = [
        {
            "Bucket": item["bucket"],
            "Casos": item["casos"],
            "Saldo": Decimal(str(item["saldo"])),
        }
        for item in snapshot["buckets_mora"]
    ]
    return _build_excel_worksheet("Aging cartera", rows)


def exportar_resumen_ejecutivo_pdf() -> bytes:
    mesa = obtener_snapshot_mesa_control()
    gestion = obtener_snapshot_gestion()
    recuperacion = obtener_snapshot_recuperacion()
    lines = [
        "Resumen ejecutivo de cartera",
        f"Fecha de corte: {date.today().isoformat()}",
        f"Cartera total: {_format_money(mesa['cartera_total'])}",
        f"Cartera vigente: {_format_money(mesa['cartera_vigente'])}",
        f"Cartera vencida: {_format_money(mesa['cartera_vencida'])}",
        f"Indice de morosidad: {_format_percent(mesa['indice_morosidad'])}",
        f"Cobertura: {_format_percent(mesa['cobertura'])}",
        f"Recuperacion del periodo: {_format_money(mesa['recuperacion_periodo'])}",
        f"Renovaciones: {gestion['renovaciones']}",
        f"Documentacion incompleta: {gestion['casos_documentacion_incompleta']}",
        f"Promesas activas: {recuperacion['promesas_pago_activas']}",
        f"Gestiones del dia: {recuperacion['gestiones_dia']}",
        f"Casos criticos: {len(recuperacion['casos_criticos'])}",
    ]
    return _build_simple_pdf(lines)


def _build_excel_worksheet(sheet_name: str, rows: list[dict]) -> bytes:
    headers = list(rows[0].keys()) if rows else []
    xml = StringIO()
    xml.write('<?xml version="1.0"?>')
    xml.write('<?mso-application progid="Excel.Sheet"?>')
    xml.write('<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" ')
    xml.write('xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">')
    xml.write(f'<Worksheet ss:Name="{_escape_xml(sheet_name)}"><Table>')
    if headers:
        xml.write("<Row>")
        for header in headers:
            xml.write(f'<Cell><Data ss:Type="String">{_escape_xml(str(header))}</Data></Cell>')
        xml.write("</Row>")
    for row in rows:
        xml.write("<Row>")
        for header in headers:
            value = row[header]
            cell_type = "Number" if isinstance(value, (int, float, Decimal)) else "String"
            if isinstance(value, Decimal):
                value = f"{value:.2f}"
            xml.write(f'<Cell><Data ss:Type="{cell_type}">{_escape_xml(str(value))}</Data></Cell>')
        xml.write("</Row>")
    xml.write("</Table></Worksheet></Workbook>")
    return xml.getvalue().encode("utf-8")


def _build_simple_pdf(lines: list[str]) -> bytes:
    objects = []
    content = ["BT", "/F1 16 Tf", "50 780 Td"]
    for index, line in enumerate(lines):
        if index == 0:
            content.append(f"({_escape_pdf(line)}) Tj")
            continue
        content.append("0 -22 Td")
        content.append(f"({_escape_pdf(line)}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n")
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(f"5 0 obj << /Length {len(stream)} >> stream\n".encode("latin-1") + stream + b"\nendstream endobj\n")

    buffer = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(buffer))
        buffer.extend(obj)
    xref_offset = len(buffer)
    buffer.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    buffer.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    buffer.extend(
        (
            f"trailer << /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("latin-1")
    )
    return bytes(buffer)


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _escape_pdf(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _format_money(value: float) -> str:
    return f"${value:,.2f}"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"
