from flask import Flask, render_template, request, send_file
import xmlrpc.client
from reportlab.pdfgen import canvas
import io
import base64
from PIL import Image
from io import BytesIO
from datetime import date

app = Flask(__name__)

# Tamaño de la etiqueta en mm (ancho x alto)
ANCHO_MM = 200
ALTO_MM = 102.1

# Conversión mm -> puntos (pt)
MM_TO_PT = 72 / 25.4
ANCHO_PT = ANCHO_MM * MM_TO_PT
ALTO_PT = ALTO_MM * MM_TO_PT

# Configuración Odoo
ODOO_URL = 'http://192.168.1.160:8070/'
DB = 'ppg'
USERNAME = 'admin'
PASSWORD = 'odooppg'

# Conexión a Odoo
common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

def get_clientes():
    return models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search_read', [[]],
                             {'fields': ['id','name','phone','street','street2','city','zip','email']})

def get_productos():
    productos_raw = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'search_read', [[]],
                                      {'fields': ['id', 'image_1920']})
    productos = []
    for p in productos_raw:
        # Obtener display_name vía name_get para asegurar variantes
        try:
            name = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'name_get', [[p['id']]])[0][1]
        except Exception:
            name = p.get('id') and str(p.get('id')) or "Producto"
        productos.append({
            'id': p['id'],
            'display_name': name,
            'image_1920': p.get('image_1920')
        })
    return productos

clientes = get_clientes()
productos = get_productos()

# Helper: dividir texto en líneas que quepan dentro de max_width (pt)
def draw_wrapped_text(c, text, x, y, max_width, font_name="Helvetica", font_size=8, leading=None):
    if leading is None:
        leading = font_size + 2
    c.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current = ""
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
    return y - (len(lines)*leading)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        use_empresa_header = request.form.get("use_empresa_header") == "1"
        # Datos ingresados por el usuario
        cantidad = request.form.get("cantidad", "")
        peso_bruto = request.form.get("peso_bruto", "")
        peso_neto = request.form.get("peso_neto", "")
        peso_unitario = request.form.get("peso_unitario", "")

        # Número de lote basado en la fecha: AAMMDD
        lote = date.today().strftime("%y%m%d")

        cliente_id = int(request.form.get("cliente"))
        producto_id = int(request.form.get("producto"))

        cliente = next(c for c in clientes if c['id']==cliente_id)
        producto = next(p for p in productos if p['id']==producto_id)

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(ANCHO_PT, ALTO_PT))

        pad = 8  # padding general en pts

        # --- HEADER (centrado y más grande) ---
        header_y = ALTO_PT - pad - 5 # baseline inicio

        
        if use_empresa_header:
            # Header de la empresa centrado y grande
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(ANCHO_PT / 2, header_y, "Plásticos Plasa de Guadalajara S.A. de C.V.")
            header_y -= 12
            c.setFont("Helvetica", 8)
            c.drawCentredString(ANCHO_PT / 2, header_y, "Calle Florentino Acosta #1090")
            header_y -= 12
            c.drawCentredString(ANCHO_PT / 2, header_y, "Guadalajara, Jalisco   C.P.44329")
            header_y -= 12
            c.drawCentredString(ANCHO_PT / 2, header_y, "Teléfono: 33-3651-5424    www.plasticosplasa.com")
            header_y -= 12
        else:
            # Título genérico de embarque
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(ANCHO_PT / 2, header_y, "EMBARQUE")
            header_y -= 18

        # Línea separadora debajo del header
        header_h = 0.18 * ALTO_PT
        line_y = ALTO_PT - header_h
        c.setLineWidth(0.5)
        c.line(pad/2, line_y, ANCHO_PT - pad/2, line_y)

        # --- Zona principal: redistribuida en 3 columnas ---
        col_w = [0.30 * ANCHO_PT, 0.30 * ANCHO_PT, 0.40 * ANCHO_PT]  # izquierda | centro | derecha
        col_x = [0, col_w[0], col_w[0] + col_w[1]]
        col0_x = col_x[0]
        col1_x = col_x[1]
        col2_x = col_x[2]

        col_top = line_y - pad
        col_bottom = pad
        available_h = col_top - col_bottom

        # ---------- COLUMNA IZQUIERDA ----------
        left_x = col0_x + pad
        left_w = col_w[0] - 2*pad
        left_y = col_top - 20

        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(left_x + left_w/2, left_y, "FRÁGIL")
        left_y -= 12
        c.setFont("Helvetica", 12)
        c.drawCentredString(left_x + left_w/2, left_y, "Manejese con Cuidado")
        left_y -= 6

        try:
            logo_path = "static/fixed.png"
            max_img_w = left_w
            max_img_h = available_h * 0.50
            c.drawImage(logo_path, left_x, left_y - max_img_h, width=max_img_w, height=max_img_h, preserveAspectRatio=True)
        except Exception:
            c.setFont("Helvetica", 7)
            c.drawString(left_x, left_y - 10, "[Imagen fija no encontrada: coloca static/fixed.png]")
            
        # coordenada Y justo debajo de la imagen
        text_y = left_y - max_img_h - 25  # 5 pts de espacio extra

        c.setFont("Helvetica", 12)
        c.drawCentredString(left_x + left_w/2, text_y, "ESTIBA MÁXIMA 3 CAJAS")

        # ---------- COLUMNA CENTRAL ----------
        center_x = col1_x + pad
        center_w = col_w[1] - 2*pad
        center_y_top = col_top - 20

        # Dejamos la parte superior libre (nombre del producto eliminado)
        cur_y = center_y_top

        # Información del cliente justo debajo de los detalles
        cliente_start_y = cur_y - 8  # empezamos un poco más abajo
        c.setFont("Helvetica-Bold", 9)
        c.drawString(center_x, cliente_start_y, "Información del cliente:")
        y_client = cliente_start_y - 20
        c.setFont("Helvetica-Bold", 12)
        y_client = draw_wrapped_text(c, cliente['name'], center_x, y_client, center_w, font_name="Helvetica-Bold", font_size=12, leading=11)
        y_client -= 4
        c.setFont("Helvetica", 8)
        y_client = draw_wrapped_text(c, f"Tel: {cliente.get('phone','')}", center_x, y_client, center_w, font_name="Helvetica", font_size=8, leading=9)
        y_client -= 2
        direccion = f"{cliente.get('street','')} {cliente.get('street2','')}, {cliente.get('city','')} {cliente.get('zip','')}"
        y_client = draw_wrapped_text(c, f"Dirección: {direccion}", center_x, y_client, center_w, font_name="Helvetica", font_size=8, leading=9)
        y_client -= 2
        y_client = draw_wrapped_text(c, f"Email: {cliente.get('email','')}", center_x, y_client, center_w, font_name="Helvetica", font_size=8, leading=9)

        cur_y = y_client - 20
        c.setFont("Helvetica-Bold", 9)
        c.drawString(center_x, cur_y, "Detalles del Embarque:")

        cur_y -= 12
        # Fecha y detalles justo debajo del header
        hoy = date.today().strftime("%d/%m/%Y")
        c.setFont("Helvetica", 8)
        cur_y -= 2  # un pequeño espacio desde el header
        c.drawString(center_x, cur_y, f"Fecha: {hoy}")
        cur_y -= 12

        # Detalles adicionales
        c.setFont("Helvetica", 8)
        
        # Lote
        cur_y = draw_wrapped_text(c, f"Lote: {lote}", center_x, cur_y, center_w, font_name="Helvetica", font_size=8, leading=10)

        # Cantidad
        cur_y = draw_wrapped_text(c, f"Cantidad: {cantidad}", center_x, cur_y, center_w, font_name="Helvetica", font_size=8, leading=10)

        # Peso bruto
        cur_y = draw_wrapped_text(c, f"Peso bruto: {peso_bruto}", center_x, cur_y, center_w, font_name="Helvetica", font_size=8, leading=10)

        # Peso neto
        cur_y = draw_wrapped_text(c, f"Peso neto: {peso_neto}", center_x, cur_y, center_w, font_name="Helvetica", font_size=8, leading=10)

        # Peso unitario
        cur_y = draw_wrapped_text(c, f"Peso unitario: {peso_unitario}", center_x, cur_y, center_w, font_name="Helvetica", font_size=8, leading=10)



        # ---------- COLUMNA DERECHA ----------
        right_x = col2_x + pad
        right_w = col_w[2] - 2*pad
        right_y_top = col_top - 20

        # Nombre del producto
        c.setFont("Helvetica-Bold", 12)
        right_y = right_y_top
        right_y = draw_wrapped_text(c, producto['display_name'], right_x, right_y, right_w, font_name="Helvetica-Bold", font_size=12, leading=14)
        right_y -= 6

        if producto.get('image_1920'):
            try:
                image_data = base64.b64decode(producto['image_1920'])
                image = Image.open(BytesIO(image_data))
                iw, ih = image.size
                max_img_h = available_h * 0.7
                max_img_w = right_w
                scale = min(max_img_w / iw, max_img_h / ih)
                if scale <= 0:
                    scale = 1
                draw_w = iw * scale
                draw_h = ih * scale
                image.save("temp_prod.png")
                c.drawImage("temp_prod.png", right_x, right_y - draw_h, width=draw_w, height=draw_h, preserveAspectRatio=True)
            except Exception:
                c.setFont("Helvetica", 7)
                c.drawString(right_x, right_y - 10, "[Imagen producto no disponible]")
        else:
            c.setFont("Helvetica", 7)
            c.drawString(right_x, right_y - 10, "[Sin imagen]")

        # Footer
        footer_text = "Generado por Plásticos Plasa - Etiqueta personalizada"
        c.setFont("Helvetica-Oblique", 6)
        c.drawCentredString(ANCHO_PT/2, pad/2, footer_text)

        c.showPage()
        c.save()
        buffer.seek(0)

        return send_file(buffer, as_attachment=True, download_name="etiqueta_layout_personal.pdf", mimetype='application/pdf')

    return render_template("index.html", clientes=clientes, productos=productos)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


