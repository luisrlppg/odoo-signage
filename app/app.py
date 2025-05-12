from flask import Flask, render_template
import xmlrpc.client
from datetime import datetime
import base64
import json
import os

app = Flask(__name__)

# Configuración de Odoo
ODOO_HOST = os.environ.get('ODOO_HOST', 'localhost')
ODOO_PORT = int(os.environ.get('ODOO_PORT', '8069'))
ODOO_DB = os.environ.get('ODOO_DB', 'postgres')
ODOO_USER = os.environ.get('ODOO_USER', 'odoo')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'odoo')

def connect_odoo():
    common = xmlrpc.client.ServerProxy(f'http://{ODOO_HOST}:{ODOO_PORT}/xmlrpc/2/common')
    models = xmlrpc.client.ServerProxy(f'http://{ODOO_HOST}:{ODOO_PORT}/xmlrpc/2/object')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    return models, uid

def obtener_ordenes_activas(models, uid):
    """Obtiene las órdenes de fabricación activas desde Odoo."""
    fields_mrp = ['name', 'product_id', 'product_qty', 'state', 'date_start']
    domain_mrp_active = [
        ('state', 'in', ['confirmed', 'progress']),
        ('name', 'not like', 'SBC%')
    ]
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'mrp.production', 'search_read',
        [domain_mrp_active],
        {'fields': fields_mrp}
    )

def obtener_imagenes_productos(models, uid, product_ids):
    """Obtiene las imágenes de los productos asociados a las órdenes."""
    image_dict = {}
    if product_ids:
        product_images = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'product.product', 'read',
            [list(product_ids)],
            {'fields': ['image_1920']}
        )
        image_dict = {p['id']: p['image_1920'] for p in product_images if p.get('image_1920')}
    return image_dict

def get_manufac_totals(manufacturing_orders):
    total = {}
    names = {}

    for orden in manufacturing_orders:
        producto_info = orden['product_id']
        cantidad = orden['product_qty']
        estado = orden['state']

        if estado == 'confirmed':
            id = producto_info[0]

            if id in total:
                total[id] += cantidad
            else:
                total[id] = cantidad
                names[id] = producto_info[1]

    return total, names

def format_quantity(quantity):
    """Formatea la cantidad con separadores de miles."""
    return "{:,.2f}".format(quantity).replace(",", "X").replace(".", ",").replace("X", ".")

@app.route('/')
def carrusel():
    try:
        models, uid = connect_odoo()
        if not uid:
            return "Error de autenticación con Odoo", 500

        manufacturing_orders = obtener_ordenes_activas(models, uid)
        if not manufacturing_orders:
            return "No hay órdenes de fabricación activas", 404

        total, names = get_manufac_totals(manufacturing_orders)
        image_dict = obtener_imagenes_productos(models, uid, total.keys())

        # Preparar los slides para la plantilla
        slides = []
        for pid in total.keys():
            slides.append({
                'name': names.get(pid, 'Producto sin nombre'),
                'quantity': format_quantity(total[pid]),
                'image': image_dict.get(pid, '')
            })

        return render_template('carrusel.html', slides=slides)

    except Exception as e:
        app.logger.error(f"Error al procesar las órdenes de fabricación: {e}")
        return f"Error del servidor: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)