# -*- coding: utf-8 -*-
import os
import smtplib
import tempfile
from email.message import EmailMessage
from db.connection import get_connection, return_connection
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def obtener_datos_usuario(usuario_id, conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT email, nombre_completo
        FROM public.usuarios
        WHERE id = %s
    """, (usuario_id,))
    row = cursor.fetchone()
    cursor.close()
    return row

def generar_xml_factura(compra_id, nombre_cliente, total, producto_id, cantidad):
    clave_acceso = f"FAC-2026-{str(compra_id).zfill(5)}"
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<RespuestaFactura>
    <Estado>VALIDADA</Estado>
    <ClaveAcceso>{clave_acceso}</ClaveAcceso>
    <Cliente>{nombre_cliente}</Cliente>
    <Total>{total}</Total>
    <Productos>
        <Producto>
            <Id>{producto_id}</Id>
            <Cantidad>{cantidad}</Cantidad>
            <Subtotal>{total}</Subtotal>
        </Producto>
    </Productos>
</RespuestaFactura>"""
    return xml_content

def generar_pdf_factura(compra_id, nombre_cliente, total, producto_id, cantidad):
    clave_acceso = f"FAC-2026-{str(compra_id).zfill(5)}"
    temp_dir = tempfile.gettempdir()
    pdf_file = os.path.join(temp_dir, f"factura_compra_{compra_id}.pdf")
    
    c = canvas.Canvas(pdf_file, pagesize=letter)
    c.drawString(100, 750, f"Factura Electrónica - {clave_acceso}")
    c.drawString(100, 730, f"Cliente: {nombre_cliente}")
    c.drawString(100, 710, f"Total: ${total}")
    c.drawString(100, 690, f"Producto: {producto_id} - Cant: {cantidad} - Subtotal: ${total}")
    c.save()
    return pdf_file

def generar_y_enviar_factura(compra_id, usuario_id, producto_id, cantidad, total):
    """Genera XML y PDF de la compra y la envía por correo."""
    conn = None
    pdf_file = None
    try:
        conn = get_connection()
        row = obtener_datos_usuario(usuario_id, conn)
        if not row:
            return False
            
        email_cliente, nombre_cliente = row
        clave_acceso = f"FAC-2026-{str(compra_id).zfill(5)}"

        # Generar XML y PDF
        xml_content = generar_xml_factura(compra_id, nombre_cliente, total, producto_id, cantidad)
        pdf_file = generar_pdf_factura(compra_id, nombre_cliente, total, producto_id, cantidad)

        # Enviar correo
        msg = EmailMessage()
        msg['Subject'] = f'Factura Electrónica - TechStore 360 - {clave_acceso}'
        
        smtp_user = os.getenv("SMTP_USER") or "test@example.com"
        msg['From'] = smtp_user
        msg['To'] = email_cliente
        msg.set_content(f'Hola {nombre_cliente},\n\nGracias por tu compra. Adjuntamos tu factura en XML y PDF.\n\nTotal: ${total}\nClave de acceso: {clave_acceso}')

        # Adjuntar XML
        msg.add_attachment(xml_content.encode('utf-8'), maintype='application', subtype='xml', filename=f'factura_{compra_id}.xml')

        # Adjuntar PDF
        with open(pdf_file, 'rb') as f:
            pdf_data = f.read()
            msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=f'factura_{compra_id}.pdf')

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
