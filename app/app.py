# app.py
import os
import io
import base64
import logging
from datetime import date
from functools import lru_cache

from flask import Flask, render_template, request, send_file, abort
import xmlrpc.client
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PIL import Image
from io import BytesIO

# ---------------------------
# Configuración
# ---------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Preferir variables de entorno para credenciales/URLs
ODOO_URL = os.environ.get("ODOO_URL", "http://192.168.1.160:8070")
DB = os.environ.get("ODOO_DB", "ppg")
USERNAME = os.environ.get("ODOO_USERNAME", "admin")
PASSWORD = os.environ.get("ODOO_PASSWORD", "odooppg")

# Tamaño etiqueta en mm -> usar reportlab units (mm*mm)
ANCHO_MM = 200
ALTO_MM = 102.1
ANCHO_PT = ANCHO_MM * mm  # reportlab.lib.units.mm
ALTO_PT = ALTO_MM * mm

app = Flask(__name__)

# ---------------------------
# Odoo: conexión y funciones
# (se hace bajo demanda y se cachea)
# ---------------------------
def get_odoo_models():
    """Crea y devuelve (common, models, uid). Lanza excepción si falla."""
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        raise RuntimeError("Autenticación Odoo fallida (uid vacío). Revisa credenciales.")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return common, models, uid

@lru_cache(maxsize=1)
def fetch_clientes():
    """Devuelve lista de clientes (cacheada)."""
    try:
        _, models, uid = get_odoo_models()
        res = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search_read', [[]],
                                {'fields': ['id','name','phone','street','street2','city','zip','email']})
        return res
    except Exception as e:
        logger.exception("Error obteniendo clientes desde Odoo")
        return []

@lru_cache(maxsize=1)
def fetch_productos():
    """Devuelve lista de productos con display_name e imagen (cacheada)."""
    try:
        _, models, uid = get_odoo_models()
        productos_raw = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'search_read', [[]],
                                          {'fields': ['id', 'image_1920']})
        productos = []
        for p in productos_raw:
            pid = p.get('id')
            # name_get para variantes / mostrar nombre correcto
            try:
                name = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'name_get', [[pid]])[0][1]
            except Exception:
                name = str(pid) if pid else "Producto"
            productos.append({
                'id': pid,
                'display_name': name,
                'image_1920': p.get('image_1920')
            })
        return productos
    except Exception:
        logger.exception("Error obteniendo productos desde Odoo")
        return []

# ---------------------------
# Util: texto envuelto
# ---------------------------
def draw_wrapped_text(c, text, x, y, max_width, font_name="Helvetica", font_size=8, leading=None):
    """
    Dibuja texto envuelto en el canvas `c` empezando en (x,y) hacia abajo.
    Retorna la coordenada Y justo debajo del último renglón.
    """
    if not text:
        return y
    if leading is None:
        leading = font_size + 2
    c.setFont(font_name, font_size)

    words = str(text).split()
    lines = []
    current = ""
    # Construir líneas respetando stringWidth
    for w in words:
        test = (current + " " + w).strip()
        if c.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)

    for i, line in enumerate(lines):
        c.drawString(x, y - i*leading, line)
    return y - (len(lines) * leading)

# ---------------------------
# Generación de PDF
# ---------------------------
def create_pdf(label_data):
    """
    Genera el PDF en memoria usando label_data dict y devuelve BytesIO listo para enviar.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(ANCHO_PT, ALTO_PT))
    pad = 8  # pts

    # Header
    header_y = ALTO_PT - pad - 5
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(ANCHO_PT / 2, header_y, label_data.get('header_text', "Plásticos Plasa de Guadalajara S.A. de C.V."))
    header_y -= 12
    c.setFont("Helvetica", 8)
    c.drawCentredString(ANCHO_PT / 2, header_y, label_data.get('empresa_direccion', "Calle Florentino Acosta #1090"))
    header_y -= 12
    c.drawCentredString(ANCHO_PT / 2, header_y, label_data.get('empresa_ciudad', "Guadalajara, Jalisco   C.P.44329"))
    header_y -= 12
    c.drawCentredString(ANCHO_PT / 2, header_y, label_data.get('empresa_contacto', "Teléfono: 33-3651-5424    www.plasticosplasa.com"))
    header_y -= 12

    # Línea separadora
    header_h = 0.18 * ALTO_PT
    line_y = ALTO_PT - header_h
    c.setLineWidth(0.5)
    c.line(pad/2, line_y, ANCHO_PT - pad/2, line_y)

    # Columnas
    col_w = [0.30 * ANCHO_PT, 0.30 * ANCHO_PT, 0.40 * ANCHO_PT]
    col_x = [0, col_w[0], col_w[0] + col_w[1]]
    col_top = line_y - pad
    col_bottom = pad
    available_h = col_top - col_bottom

    # ========== Columna izquierda ========== 
    left_x = col_x[0] + pad
    left_w = col_w[0] - 2*pad
    left_y = col_top - 20

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(left_x + left_w/2, left_y, label_data.get('fragil_text', "FRÁGIL"))
    left_y -= 12
    c.setFont("Helvetica", 12)
    c.drawCentredString(left_x + left_w/2, left_y, label_data.get('fragil_subtext', "Manejese con Cuidado"))
    left_y -= 6

    # Imagen fija si existe
    logo_path = os.path.join(app.root_path, "static", "fixed.png")
    LEFT_IMAGE_HEIGHT_RATIO = 0.6
    MAX_UPSCALE = 1.0
    max_img_h = available_h * LEFT_IMAGE_HEIGHT_RATIO
    try:
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            iw, ih = img.size
            scale_w = left_w / iw
            scale_h = max_img_h / ih
            scale = min(scale_w, scale_h) * MAX_UPSCALE
            if scale <= 0:
                scale = 1.0
            draw_w = iw * scale
            draw_h = ih * scale
            if draw_w > left_w:
                factor = left_w / draw_w
                draw_w *= factor
                draw_h *= factor
            img_buf = BytesIO()
            img.convert("RGBA").save(img_buf, format="PNG")
            img_buf.seek(0)
            img_x = left_x + (left_w - draw_w) / 2
            img_y = left_y - draw_h
            c.drawImage(ImageReader(img_buf), img_x, img_y, width=draw_w, height=draw_h, preserveAspectRatio=True)
            left_y -= draw_h + 5
        else:
            raise FileNotFoundError
    except Exception:
        c.setFont("Helvetica", 7)
        c.drawString(left_x, left_y - 10, "[Imagen fija no encontrada: coloca static/fixed.png]")
        left_y -= 20

    text_y = left_y - 10
    c.setFont("Helvetica", 12)
    c.drawCentredString(left_x + left_w/2, text_y, label_data.get('estiba_text', "ESTIBA MÁXIMA 3 CAJAS"))

    # ========== Columna central ========== 
    center_x = col_x[1] + pad
    center_w = col_w[1] - 2*pad
    cur_y = col_top - 20

    c.setFont("Helvetica-Bold", 9)
    c.drawString(center_x, cur_y - 8, label_data.get('cliente_info_title', "Información del cliente:"))
    y_client = cur_y - 28

    c.setFont("Helvetica-Bold", 12)
    y_client = draw_wrapped_text(c, label_data['cliente'].get('name', ''), center_x, y_client, center_w, font_name="Helvetica-Bold", font_size=12, leading=11)
    y_client -= 4
    c.setFont("Helvetica", 8)
    y_client = draw_wrapped_text(c, f"Tel: {label_data['cliente'].get('phone','')}", center_x, y_client, center_w, font_name="Helvetica", font_size=8, leading=9)
    y_client -= 2
    direccion = f"{label_data['cliente'].get('street','')} {label_data['cliente'].get('street2','')}, {label_data['cliente'].get('city','')} {label_data['cliente'].get('zip','')}"
    y_client = draw_wrapped_text(c, f"Dirección: {direccion}", center_x, y_client, center_w, font_name="Helvetica", font_size=8, leading=9)
    y_client -= 2
    y_client = draw_wrapped_text(c, f"Email: {label_data['cliente'].get('email','')}", center_x, y_client, center_w, font_name="Helvetica", font_size=8, leading=9)

    cur_y = y_client - 20
    c.setFont("Helvetica-Bold", 9)
    c.drawString(center_x, cur_y, label_data.get('embarque_title', "Detalles del Embarque:"))
    cur_y -= 12

    hoy = date.today().strftime("%d/%m/%Y")
    c.setFont("Helvetica", 8)
    cur_y -= 2
    c.drawString(center_x, cur_y, f"Fecha: {hoy}")
    cur_y -= 12

    cur_y = draw_wrapped_text(c, f"Lote: {date.today().strftime('%y%m%d')}", center_x, cur_y, center_w, font_name="Helvetica", font_size=8, leading=10)
    cur_y = draw_wrapped_text(c, f"Cantidad: {label_data.get('cantidad','')}", center_x, cur_y, center_w, font_name="Helvetica", font_size=8, leading=10)
    cur_y = draw_wrapped_text(c, f"Peso bruto: {label_data.get('peso_bruto','')}", center_x, cur_y, center_w, font_name="Helvetica", font_size=8, leading=10)
    cur_y = draw_wrapped_text(c, f"Peso neto: {label_data.get('peso_neto','')}", center_x, cur_y, center_w, font_name="Helvetica", font_size=8, leading=10)
    cur_y = draw_wrapped_text(c, f"Peso unitario: {label_data.get('peso_unitario','')}", center_x, cur_y, center_w, font_name="Helvetica", font_size=8, leading=10)

    # ========== Columna derecha ========== 
    right_x = col_x[2] + pad
    right_w = col_w[2] - 2*pad
    right_y = col_top - 20

    c.setFont("Helvetica-Bold", 12)
    right_y = draw_wrapped_text(c, label_data['producto'].get('display_name',''), right_x, right_y, right_w, font_name="Helvetica-Bold", font_size=12, leading=14)
    right_y -= 6

    img_b64 = label_data['producto'].get('image_1920')
    if img_b64:
        try:
            image_data = base64.b64decode(img_b64)
            img = Image.open(BytesIO(image_data)).convert("RGBA")
            iw, ih = img.size
            max_img_h = available_h * 0.7
            max_img_w = right_w
            scale = min(max_img_w / iw, max_img_h / ih, 1.0)
            draw_w = iw * scale
            draw_h = ih * scale
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            c.drawImage(ImageReader(buf), right_x, right_y - draw_h, width=draw_w, height=draw_h, preserveAspectRatio=True)
            right_y -= draw_h + 5
        except Exception:
            logger.exception("Error procesando imagen del producto")
            c.setFont("Helvetica", 7)
            c.drawString(right_x, right_y - 10, "[Imagen producto no disponible]")
    else:
        c.setFont("Helvetica", 7)
        c.drawString(right_x, right_y - 10, "[Sin imagen]")

    # Footer
    footer_text = label_data.get('footer_text', "Generado por Plásticos Plasa - Etiqueta personalizada")
    c.setFont("Helvetica-Oblique", 6)
    c.drawCentredString(ANCHO_PT/2, pad/2, footer_text)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ---------------------------
# Rutas
# ---------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    clientes = fetch_clientes()
    productos = fetch_productos()

    if request.method == "POST":
        try:
            cliente_id = int(request.form.get("cliente", 0))
            producto_id = int(request.form.get("producto", 0))
        except ValueError:
            abort(400, "Cliente o producto inválido")

        cliente = next((c for c in clientes if c.get('id') == cliente_id), None)
        producto = next((p for p in productos if p.get('id') == producto_id), None)
        if cliente is None or producto is None:
            abort(404, "Cliente o producto no encontrado")

        # Construir el diccionario de datos para la etiqueta, usando valores opcionales si se proporcionan
        cliente_mod = cliente.copy() if cliente else {}
        if request.form.get("cliente_name"): cliente_mod['name'] = request.form.get("cliente_name")
        if request.form.get("cliente_phone"): cliente_mod['phone'] = request.form.get("cliente_phone")
        if request.form.get("cliente_address"): 
            # Sobrescribe toda la dirección en un solo campo
            cliente_mod['street'] = request.form.get("cliente_address")
            cliente_mod['street2'] = ""
            cliente_mod['city'] = ""
            cliente_mod['zip'] = ""
        if request.form.get("cliente_email"): cliente_mod['email'] = request.form.get("cliente_email")

        producto_mod = producto.copy() if producto else {}
        if request.form.get("producto_name"): producto_mod['display_name'] = request.form.get("producto_name")

        # Procesar imagen subida para el producto
        producto_image_b64 = None
        if 'producto_image' in request.files:
            file = request.files['producto_image']
            if file and file.filename:
                img_bytes = file.read()
                producto_image_b64 = base64.b64encode(img_bytes).decode('utf-8')
                producto_mod['image_1920'] = producto_image_b64

        # Si el usuario marcó el checkbox para editar el header, usar los valores del formulario; si no, usar los valores por defecto
        label_data = {
            'cliente': cliente_mod,
            'producto': producto_mod,
            'cantidad': request.form.get("cantidad", ""),
            'peso_bruto': request.form.get("peso_bruto", ""),
            'peso_neto': request.form.get("peso_neto", ""),
            'peso_unitario': request.form.get("peso_unitario", ""),
            'header_text': request.form.get("header_text", "Plasticos Plasa de Guadalajara S.A. de C.V."),
            'empresa_direccion': request.form.get("empresa_direccion", "Calle Florentino Acosta #1090"),
            'empresa_ciudad': request.form.get("empresa_ciudad", "Guadalajara, Jalisco   C.P.44329"),
            'empresa_contacto': request.form.get("empresa_contacto", "Telefono: 33-3651-5424    www.plasticosplasa.com"),
            'cliente_info_title': request.form.get("cliente_info_title", "Para cliente:"),
            'fragil_text': "FRÁGIL",
            'fragil_subtext': "Manejese con Cuidado",
            'estiba_text': "ESTIBA MÁXIMA 3 CAJAS",
            'footer_text': request.form.get("footer_text", "Generado por Plásticos Plasa - Etiqueta personalizada"),
        }

        try:
            pdf_io = create_pdf(label_data)
            return send_file(pdf_io, as_attachment=True, download_name="etiqueta_layout_personal.pdf", mimetype='application/pdf')
        except Exception:
            logger.exception("Error generando PDF")
            abort(500, "Error generando PDF")

    return render_template("index.html", clientes=clientes, productos=productos)

# ---------------------------
# Entrypoint
# ---------------------------
if __name__ == "__main__":
    # En producción deberías usar gunicorn/uwsgi y no app.run
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
