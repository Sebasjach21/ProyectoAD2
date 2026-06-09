# -*- coding: utf-8 -*-
"""CRUD de Compras – Blueprint Flask."""
from flask import Blueprint, jsonify, request
from db.connection import get_connection, return_connection

bp = Blueprint("purchases", __name__, url_prefix="/compras")


@bp.route("", methods=["GET"])
def listar_compras():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT compra_id, usuario_id, producto_id, cantidad, total, fecha_compra "
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
            }
            for r in rows
        ]
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


@bp.route("", methods=["POST"])
def registrar_compra():
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        usuario_id = data.get("usuario_id")
        productos = data.get("productos")  # [{"producto_id": "uuid", "cantidad": 2}, ...]

        if not usuario_id or not productos:
            return jsonify({"success": False, "message": "Faltan datos (usuario_id o productos)"}), 400

        conn = get_connection()
        cursor = conn.cursor()
        total_general = 0
        detalles = []

        for item in productos:
            prod_id = item["producto_id"]
            cant = item["cantidad"]
            cursor.execute("SELECT precio, stock FROM public.productos WHERE producto_id = %s FOR UPDATE", (prod_id,))
            res = cursor.fetchone()
            if not res:
                return jsonify({"success": False, "message": f"Producto {prod_id} no existe"}), 404
            
            precio, stock = res
            if stock < cant:
                return jsonify({"success": False, "message": f"Stock insuficiente para el producto {prod_id}. Disponible: {stock}"}), 400
            
            subtotal = precio * cant
            total_general += subtotal
            detalles.append((prod_id, cant, precio, subtotal))

        # Crear factura
        cursor.execute(
            "INSERT INTO public.facturas (usuario_id, total_general) VALUES (%s, %s) RETURNING factura_id", 
            (usuario_id, total_general)
        )
        factura_id = cursor.fetchone()[0]

        # Insertar detalles y actualizar stock
        for prod_id, cant, precio, subtotal in detalles:
            cursor.execute(
                "INSERT INTO public.detalle_facturas (factura_id, producto_id, cantidad, precio_unitario, subtotal) VALUES (%s, %s, %s, %s, %s)", 
                (factura_id, prod_id, cant, precio, subtotal)
            )
            cursor.execute("UPDATE public.productos SET stock = stock - %s WHERE producto_id = %s", (cant, prod_id))

        conn.commit()

        # DISPARAR FACTURACIÓN
        from services.facturacion import generar_y_enviar_factura
        generar_y_enviar_factura(factura_id)

        return jsonify({"success": True, "message": "Compra registrada con éxito", "factura_id": factura_id, "total": total_general}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)
