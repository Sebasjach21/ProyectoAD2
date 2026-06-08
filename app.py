# -*- coding: utf-8 -*-
"""
app.py – Bootstrap principal de Flask.

Toda la lógica de rutas, CRUD y SOAP ahora vive en los paquetes:
  routes/       → blueprints de productos, usuarios, compras, facturación
  services/     → notificaciones (Twilio + Mailtrap), lógica SOAP
  db/           → pool de conexiones Supabase
  config/       → variables de entorno
"""
from flask import Flask, jsonify
from flask_cors import CORS
from routes import register_routes

app = Flask(__name__)

# CORS global – permite cualquier origen (ajustar en producción si se desea restringir)
CORS(
    app,
    resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    },
)

# Registrar todos los blueprints
register_routes(app)

# Health-check raíz – necesario para que Render y navegadores no reciban 404
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "TechStore API Replica",
        "version": "2.0",
        "endpoints": [
            "/productos",
            "/usuarios",
            "/compras",
            "/facturas"
        ]
    }), 200

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5002)