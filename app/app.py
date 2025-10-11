from flask import Flask, render_template, request, redirect, url_for, session
import xmlrpc.client
from datetime import datetime
import base64
import json
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Necesario para usar session

def format_number(value):
    """Format a number with thousand separators"""
    try:
        # Convert to integer first
        num = int(float(value))
        # Format with thousand separators
        return "{:,}".format(num)
    except (ValueError, TypeError):
        return value

# Register the filter with Jinja2
app.jinja_env.filters['format_number'] = format_number

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
def production_grid():
    try:
        models, uid = connect_odoo()
        if not uid:
            return "Error de autenticación con Odoo", 500
        
        manufacturing_orders = obtener_ordenes_activas(models, uid)
        if not manufacturing_orders:
            return "No hay órdenes de fabricación activas", 404

        categories = get_manufac_totals_by_category(models, uid, manufacturing_orders)
        
        # Obtener productos seleccionados de la sesión
        display_products = session.get('display_products', [])
        
        # Si hay productos seleccionados, filtrar las categorías
        if display_products:
            for category in categories.values():
                filtered_total = {pid: qty for pid, qty in category['total'].items() 
                               if pid in display_products}
                filtered_names = {pid: name for pid, name in category['names'].items() 
                                if pid in display_products}
                category['total'] = filtered_total
                category['names'] = filtered_names
        
        # Determinar qué sección tiene más tarjetas
        section_counts = {
            'inyeccion': len(categories['inyeccion']['total']),
            'ensamble': len(categories['ensamble']['total']),
            'cepillo': len(categories['cepillo']['total'])
        }
        
        largest_section = max(section_counts.items(), key=lambda x: x[1])[0]
        
        return render_template('production_grid.html', body_class='no-scroll', 
                             categories=categories, 
                             largest_section=largest_section)
        
        manufacturing_orders = obtener_ordenes_activas(models, uid)
        if not manufacturing_orders:
            return "No hay órdenes de fabricación activas", 404

        categories = get_manufac_totals_by_category(models, uid, manufacturing_orders)
        
        return render_template('production_grid.html', categories=categories)
    except Exception as e:
        app.logger.error(f"Error al procesar las órdenes de fabricación: {e}")
        return f"Error del servidor: {e}", 500

@app.route('/list')
def list_view():
    try:
        models, uid = connect_odoo()
        orders = obtener_ordenes_activas(models, uid)
        
        if not orders:
            return "No hay órdenes de fabricación activas", 404
            
        # Usar la función existente para clasificar órdenes
        categorias = get_manufac_totals_by_category(models, uid, orders)
        
        # Convertir el formato de datos para que coincida con la plantilla
        formatted_categorias = {
            'inyeccion': [
                {'product_id': (pid, categorias['inyeccion']['names'][pid]), 
                 'product_qty': qty} 
                for pid, qty in categorias['inyeccion']['total'].items()
            ],
            'ensamble': [
                {'product_id': (pid, categorias['ensamble']['names'][pid]), 
                 'product_qty': qty} 
                for pid, qty in categorias['ensamble']['total'].items()
            ],
            'cepillo': [
                {'product_id': (pid, categorias['cepillo']['names'][pid]), 
                 'product_qty': qty} 
                for pid, qty in categorias['cepillo']['total'].items()
            ]
        }
        
        # Obtener los productos seleccionados de la sesión
        display_settings = session.get('display_products', [])
        
        return render_template('list_view.html', body_class='scrollable',
                             categorias=formatted_categorias,
                             display_settings=display_settings)
    except Exception as e:
        app.logger.error(f"Error en list_view: {e}")
        return f"Error: {str(e)}", 500

@app.route('/update-display', methods=['POST'])
def update_display_settings():
    try:
        # Obtener los IDs de productos seleccionados
        selected_products = request.form.getlist('display_products')
        
        # Guardar en la sesión
        session['display_products'] = [int(pid) for pid in selected_products]
        
        return redirect(url_for('production_grid'))
    except Exception as e:
        app.logger.error(f"Error actualizando configuración: {e}")
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)