from flask import Flask, render_template
import xmlrpc.client
from datetime import datetime
import base64
import json
import os

app = Flask(__name__)

# Configuración de Odoo
ODOO_URL = 'http://192.168.1.160:8070/'
ODOO_DB = 'ppg'
ODOO_USERNAME = 'admin'
ODOO_PASSWORD = 'odooppg'

def connect_odoo():
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
    return models, uid

def obtener_ordenes_activas(models, uid):
    """Obtiene las órdenes de fabricación activas desde Odoo."""
    fields_mrp = ['name', 'product_id', 'product_qty', 'state', 'date_start']
    domain_mrp_active = [
        ('state', 'in', ['confirmed','progress','to_close']),
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

def get_manufac_totals_by_category(models, uid, manufacturing_orders):
    categories = {
        'ensamble': {'total': {}, 'names': {}},
        'cepillo': {'total': {}, 'names': {}},
        'inyeccion': {'total': {}, 'names': {}}
    }
    
    # Obtener categorías de los productos
    product_ids = [orden['product_id'][0] for orden in manufacturing_orders]
    product_categories = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'product.product', 'read',
        [product_ids],
        {'fields': ['categ_id']}
    )
    
    # Mapear producto a categoría
    product_to_category = {}
    for product in product_categories:
        categ_name = product['categ_id'][1].lower() if product.get('categ_id') else ''
        if 'ensamble' in categ_name or 'pincel' in categ_name:
            product_to_category[product['id']] = 'ensamble'
        elif 'cepillo' in categ_name:
            product_to_category[product['id']] = 'cepillo'
        else:
            product_to_category[product['id']] = 'inyeccion'
    
    # Agrupar por categoría
    for orden in manufacturing_orders:
        producto_info = orden['product_id']
        cantidad = orden['product_qty']
        estado = orden['state']
        product_id = producto_info[0]

        if estado in ['confirmed', 'progress', 'to_close']:
            category = product_to_category.get(product_id, 'inyeccion')
            
            if product_id in categories[category]['total']:
                categories[category]['total'][product_id] += cantidad
            else:
                categories[category]['total'][product_id] = cantidad
                categories[category]['names'][product_id] = producto_info[1]
    
    return categories

def format_quantity(quantity):
    """Formatea la cantidad con separadores de miles."""
    return "{:,.2f}".format(quantity).replace(",", "X").replace(".", ",").replace("X", ".")

@app.route('/')
def vista_agrupada():
    try:
        models, uid = connect_odoo()
        if not uid:
            return "Error de autenticación con Odoo", 500
        
        manufacturing_orders = obtener_ordenes_activas(models, uid)
        if not manufacturing_orders:
            return "No hay órdenes de fabricación activas", 404

        categories = get_manufac_totals_by_category(models, uid, manufacturing_orders)
        all_product_ids = []
        for category in categories.values():
            all_product_ids.extend(category['total'].keys())
        
        image_dict = obtener_imagenes_productos(models, uid, all_product_ids)

        # Procesar cada categoría
        slides_data = {}
        for category_name, category_data in categories.items():
            sorted_items = sorted(
                [{
                    'name': category_data['names'].get(pid, 'Producto sin nombre'),
                    'quantity': format_quantity(category_data['total'][pid]),
                    'image': image_dict.get(pid, ''),
                    'pid': pid
                } for pid in category_data['total'].keys()],
                key=lambda x: float(x['quantity'].replace('.', '').replace(',', '.')),
                reverse=True
            )
            
            # Agrupar en slides de 10 items
            group_size = 10
            slides_data[category_name] = [
                sorted_items[i:i + group_size] 
                for i in range(0, len(sorted_items), group_size)
            ]

        return render_template('vista_agrupada.html', 
                            slides_ensamble=slides_data['ensamble'],
                            slides_cepillo=slides_data['cepillo'],
                            slides_inyeccion=slides_data['inyeccion'])
    except Exception as e:
        app.logger.error(f"Error al procesar las órdenes de fabricación: {e}")
        return f"Error del servidor: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)