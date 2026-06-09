# -*- coding: utf-8 -*-
"""Simulación de Bucket Storage – Blueprint Flask."""
from flask import Blueprint, send_from_directory, jsonify
import os
import tempfile

bp = Blueprint("bucket", __name__, url_prefix="/bucket")

BUCKET_DIR = os.path.join(tempfile.gettempdir(), "facturas")

@bp.route("/facturas/<filename>", methods=["GET"])
def descargar_archivo(filename):
    """
    Simula la descarga pública desde un bucket S3/Supabase Storage.
    Retorna el archivo solicitado si existe.
    """
    if os.path.exists(os.path.join(BUCKET_DIR, filename)):
        return send_from_directory(BUCKET_DIR, filename, as_attachment=False)
    else:
        return jsonify({"success": False, "message": "Archivo no encontrado"}), 404
