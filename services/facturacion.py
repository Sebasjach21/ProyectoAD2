# -*- coding: utf-8 -*-
import os
import smtplib
import tempfile
import json
from email.message import EmailMessage
from db.connection import get_connection, return_connection
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def obtener_datos_factura(factura_id, conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.email, u.nombre_completo, f.total_general, 
               json_agg(json_build_object('producto_id', d.producto_id, 'cantidad', d.cantidad, 'precio', d.precio_unitario, 'subtotal', d.subtotal))
        FROM public.facturas f
        JOIN public.usuarios u ON f.usuario_id = u.id
        JOIN public.detalle_facturas d ON f.factura_id = d.factura_id
        WHERE f.factura_id = %s
        GROUP BY u.email, u.nombre_completo, f.total_general
    """, (factura_id,))
    row = cursor.fetchone()
    cursor.close()
    return row

def generar_xml_factura(factura_id, nombre_cliente, total, productos):
    clave_acceso = f"FAC-2026-{str(factura_id).zfill(5)}"
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<RespuestaFactura>
    <Estado>VALIDADA</Estado>
    <ClaveAcceso>{clave_acceso}</ClaveAcceso>
    <Cliente>{nombre_cliente}</Cliente>
    <Total>{total}</Total>
    <Productos>
"""
    for p in productos:
        xml_content += f"""        <Producto>
            <Id>{p['producto_id']}</Id>
            <Cantidad>{p['cantidad']}</Cantidad>
            <Precio>{p['precio']}</Precio>
            <Subtotal>{p['subtotal']}</Subtotal>
        </Producto>
"""
    xml_content += "    </Productos>\n</RespuestaFactura>"
    return xml_content

def generar_pdf_factura(factura_id, nombre_cliente, total, productos):
    clave_acceso = f"FAC-2026-{str(factura_id).zfill(5)}"
    temp_dir = tempfile.gettempdir()
    pdf_file = os.path.join(temp_dir, f"factura_{factura_id}.pdf")
    
    c = canvas.Canvas(pdf_file, pagesize=letter)
    c.drawString(100, 750, f"Factura Electrónica - {clave_acceso}")
    c.drawString(100, 730, f"Cliente: {nombre_cliente}")
    c.drawString(100, 710, f"Total: ${total}")
    y = 690
    for p in productos:
        c.drawString(100, y, f"Producto: {p['producto_id']} - Cant: {p['cantidad']} - Subtotal: ${p['subtotal']}")
        y -= 20
    c.save()
    return pdf_file

def generar_y_enviar_factura(factura_id):
    """Genera XML y PDF de la factura y la envía por correo."""
    conn = None
    pdf_file = None
    try:
        conn = get_connection()
        row = obtener_datos_factura(factura_id, conn)
        if not row:
            return False
            
        email_cliente, nombre_cliente, total, productos = row
        clave_acceso = f"FAC-2026-{str(factura_id).zfill(5)}"

        # Generar XML y PDF
        xml_content = generar_xml_factura(factura_id, nombre_cliente, total, productos)
        pdf_file = generar_pdf_factura(factura_id, nombre_cliente, total, productos)

        # Enviar correo
        msg = EmailMessage()
        msg['Subject'] = f'Factura Electrónica - TechStore 360 - {clave_acceso}'
        
        smtp_user = os.getenv("SMTP_USER") or "test@example.com"
        msg['From'] = smtp_user
        msg['To'] = email_cliente
        msg.set_content(f'Hola {nombre_cliente},\n\nGracias por tu compra. Adjuntamos tu factura en XML y PDF.\n\nTotal: ${total}\nClave de acceso: {clave_acceso}')

        # Adjuntar XML
        msg.add_attachment(xml_content.encode('utf-8'), maintype='application', subtype='xml', filename=f'factura_{factura_id}.xml')

        # Adjuntar PDF
        with open(pdf_file, 'rb') as f:
            pdf_data = f.read()
            msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=f'factura_{factura_id}.pdf')

        # Enviar
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = os.getenv("SMTP_PORT")
        smtp_pass = os.getenv("SMTP_PASS")
        
        if smtp_server and smtp_port and smtp_pass:
            with smtplib.SMTP(smtp_server, int(smtp_port)) as smtp:
                smtp.starttls()
                smtp.login(smtp_user, smtp_pass)
                smtp.send_message(msg)
        else:
            print("Variables SMTP no configuradas. Simulando envío.")
            
        return True
    except Exception as e:
        print(f"Error generando factura: {e}")
        return False
    finally:
        if conn: return_connection(conn)
        if pdf_file and os.path.exists(pdf_file):
            try:
                os.remove(pdf_file)
            except:
                pass
