# -*- coding: utf-8 -*-
"""CRUD de Compras – Blueprint Flask."""
from flask import Blueprint, jsonify, request
from db.connection import get_connection, return_connection
from zeep import Client
import os
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

bp = Blueprint("purchases", __name__, url_prefix="/compras")

BUCKET_DIR = os.path.join(tempfile.gettempdir(), "facturas")
os.makedirs(BUCKET_DIR, exist_ok=True)

@bp.route("", methods=["GET"])
def listar_compras():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT compra_id, usuario_id, producto_id, cantidad, total, fecha_compra, clave_acceso_sri, estado_factura "
            "FROM public.compras ORDER BY fecha_compra DESC"
        )
        rows = cursor.fetchall()
        data = [
            {
                "compra_id": r[0],
                "usuario_id": r[1],
                "producto_id": str(r[2]) if r[2] is not None else "PRODUCTO_ELIMINADO",
                "cantidad": r[3],
                "total": float(r[4]) if r[4] is not None else 0.0,
                "fecha_compra": r[5].isoformat() if r[5] else None,
                "clave_acceso_sri": r[6],
                "estado_factura": r[7]
            }
            for r in rows
        ]
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

@bp.route("", methods=["POST"])
def registrar_compra():
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        usuario_id = data.get("usuario_id")
        producto_id = data.get("producto_id")
        cantidad = data.get("cantidad")
        total = data.get("total")

        if not usuario_id or not producto_id or not cantidad or total is None:
            return jsonify({"success": False, "message": "Faltan campos obligatorios"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # Verificar stock con bloqueo de fila
        cursor.execute(
            "SELECT stock FROM public.productos WHERE producto_id = %s FOR UPDATE",
            (producto_id,),
        )
        res = cursor.fetchone()
        if not res:
            return jsonify({"success": False, "message": "El producto no existe"}), 404

        stock_actual = res[0]
        if stock_actual < cantidad:
            return jsonify({"success": False, "message": f"Stock insuficiente. Disponible: {stock_actual}"}), 400

        # Reducir stock e insertar compra
        cursor.execute(
            "UPDATE public.productos SET stock = stock - %s WHERE producto_id = %s",
            (cantidad, producto_id),
        )
        cursor.execute(
            "INSERT INTO public.compras (usuario_id, producto_id, cantidad, total, fecha_compra) "
            "VALUES (%s, %s, %s, %s, NOW() AT TIME ZONE 'UTC') RETURNING compra_id",
            (usuario_id, producto_id, cantidad, total),
        )
        nueva_compra_id = cursor.fetchone()[0]
        conn.commit()

        # Llamada SOAP
        wsdl_url = request.host_url.rstrip("/") + "/facturacion?wsdl"
        try:
            client = Client(wsdl=wsdl_url)
            # Pasamos el idCompra, los demás campos el SOAP los ignora/busca de DB
            response = client.service.GenerarFacturaXML(
                idCompra=str(nueva_compra_id),
                cliente="cliente_temporal",
                correo="correo_temporal",
                telefono="tel_temporal"
            )
            xml_generado = response
        except Exception as e:
            # En caso de error de red con Zeep, podemos fallar amigablemente
            xml_generado = f"<RespuestaFactura><Estado>ERROR</Estado><Mensaje>{str(e)}</Mensaje></RespuestaFactura>"

        clave_acceso = f"FAC-2026-{str(nueva_compra_id).zfill(5)}"
        
        # Guardar XML en el "Bucket" (carpeta local)
        xml_filename = f"compra_{nueva_compra_id}.xml"
        xml_path = os.path.join(BUCKET_DIR, xml_filename)
        with open(xml_path, "w", encoding="utf-8") as f:
            if isinstance(xml_generado, dict) and "xmlGenerado" in xml_generado:
                f.write(str(xml_generado["xmlGenerado"]))
            else:
                f.write(str(xml_generado))

        # Generar PDF "bonito" y guardar en "Bucket"
        pdf_filename = f"compra_{nueva_compra_id}.pdf"
        pdf_path = os.path.join(BUCKET_DIR, pdf_filename)
        
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, f"Factura Electrónica (SRI)")
        c.drawString(100, 730, f"Clave Acceso: {clave_acceso}")
        c.drawString(100, 710, f"Compra ID: {nueva_compra_id}")
        c.drawString(100, 690, f"Total: ${total}")
        c.drawString(100, 670, f"Producto ID: {producto_id}")
        c.drawString(100, 650, f"Cantidad: {cantidad}")
        c.save()

        # Actualizar tabla compras
        cursor.execute(
            "UPDATE public.compras SET clave_acceso_sri = %s, estado_factura = %s WHERE compra_id = %s",
            (clave_acceso, "AUTORIZADO", nueva_compra_id)
        )
        conn.commit()

        # Retornar respuesta al Flutter
        return jsonify({
            "status": 200, 
            "mensaje": "Compra exitosa", 
            "factura_url": f"{request.host_url.rstrip('/')}/bucket/facturas/{pdf_filename}",
            "xml_url": f"{request.host_url.rstrip('/')}/bucket/facturas/{xml_filename}"
        }), 200

    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)
