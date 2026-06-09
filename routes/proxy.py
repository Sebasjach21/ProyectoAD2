# -*- coding: utf-8 -*-
"""Proxy para Imágenes con bloqueo CORS – Blueprint Flask."""
from flask import Blueprint, request, Response, jsonify
import requests

bp = Blueprint("proxy", __name__, url_prefix="/api")

@bp.route("/imagen", methods=["GET"])
def proxy_imagen():
    """
    Descarga una imagen de una URL externa y la sirve con los headers CORS correctos.
    Uso: /api/imagen?url=https://storage.googleapis.com/...
    """
    image_url = request.args.get("url")
    if not image_url:
        return jsonify({"success": False, "message": "Falta el parámetro 'url'"}), 400

    try:
        # Hacemos la petición a la URL original
        r = requests.get(image_url, stream=True, timeout=10)
        
        # Si la imagen no existe o da error, devolvemos el error
        if r.status_code != 200:
            return jsonify({"success": False, "message": f"No se pudo obtener la imagen (HTTP {r.status_code})"}), r.status_code

        # Creamos una respuesta en Flask usando el contenido binario de la imagen
        content_type = r.headers.get("Content-Type", "image/jpeg")
        
        response = Response(r.content, content_type=content_type)
        # Forzamos los headers CORS para que Flutter Web no se queje
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        
        return response

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
