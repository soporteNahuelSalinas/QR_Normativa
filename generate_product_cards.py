import os
import json
import re
from PIL import Image, ImageDraw, ImageFont
import textwrap
from PyPDF2 import PdfMerger

# Configuración general
dpi = 300
a4_width, a4_height = int(8.27 * dpi), int(11.69 * dpi)
card_width, card_height = 780, 340
output_folder = "output_pdfs"
qr_folder = "qrcodes-manuales"
page_color = "#D4C3C3"
qr_max_height = card_height - int(0.1 * dpi + 2)
background_color = "#FFFF"
font_color = "black"
margin = int(0.01 * dpi)
spacing = int(0.02 * dpi)
columns = 3
max_rows_per_page = 10
padding_left = 10  # Nuevo padding izquierdo

# Configuración de fuentes
font_path = os.path.join("assets", "fonts", "Poppins-Regular.ttf")
if not os.path.exists(font_path):
    raise FileNotFoundError(f"Fuente no encontrada: {font_path}")

font_size = 36
font = ImageFont.truetype(font_path, font_size)
font_large = ImageFont.truetype(font_path, font_size * 2)
font_iva = ImageFont.truetype(font_path, 30)  # Fuente para el IVA

def clean_product_name(filename, currency):
    try:
        parts = os.path.splitext(filename)[0].split("__PRECIO__")
        name_part = parts[0]
        price_part = parts[1] if len(parts) > 1 else ""
    except (ValueError, IndexError):
        return ("", "", "", "")
    
    # Extraer IVA
    iva_amount = ""
    if "__IVA_" in name_part:
        iva_split = name_part.split("__IVA_", 1)
        name_part = iva_split[0]
        iva_part = iva_split[1].split("__")[0]
        iva_amount = iva_part.replace("IVA_$", "").strip()
    
    # Extraer nombre y referencia
    product_info = re.sub(r"[_-]", " ", name_part)
    ref_match = re.search(r"(\d+)$", product_info)
    reference = ref_match.group(1) if ref_match else ""
    clean_name = re.sub(r"\s*\d+$", "", product_info).strip()

    # Procesar precio
    price = ""
    price_match = re.match(r"(USD|ARS)_\$([\d.,]+)", price_part)
    if price_match and price_match.group(1) == currency:
        raw_price = price_match.group(2)
        try:
            if currency == "USD":
                price_value = float(raw_price.replace(",", ""))
                price = f"{price_value:.2f}"
            else:
                price_value = int(raw_price.replace(".", ""))
                price = f"{price_value}"
        except ValueError:
            print(f"Error formateando precio: {raw_price}")

    return clean_name, reference, price, iva_amount

def load_product_ids():
    data_json_path = 'data/products.json'
    if not os.path.exists(data_json_path):
        print("Error: No se encontró products.json")
        return []
    with open(data_json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_cards(currency):
    os.makedirs(output_folder, exist_ok=True)
    if not os.path.exists(qr_folder):
        raise FileNotFoundError(f"Directorio QR faltante: {qr_folder}")

    product_data = []
    for file in sorted(os.listdir(qr_folder)):
        if file.endswith(".png"):
            name, ref, price, iva = clean_product_name(file, currency)
            if name:
                product_data.append({
                    "name": name,
                    "reference": ref,
                    "price": price,
                    "iva": iva,
                    "qr_path": os.path.join(qr_folder, file),
                    "currency": currency
                })

    if not product_data:
        print("No hay productos válidos")
        return None

    merger = PdfMerger()
    page_count = 1
    x, y, row = margin, margin, 0
    current_page = Image.new("RGB", (a4_width, a4_height), page_color)

    for index, product in enumerate(product_data):
        card = Image.new("RGB", (card_width, card_height), background_color)
        draw = ImageDraw.Draw(card)

        # Agregar QR
        qr_img = Image.open(product["qr_path"]).resize(
            (int(qr_max_height * 0.9), qr_max_height))
        qr_x = card_width - qr_img.width - margin
        qr_y = (card_height - qr_img.height) // 2
        card.paste(qr_img, (qr_x, qr_y))

        # Texto CTA
        cta_font = ImageFont.truetype(font_path, 30)
        cta_text = "Ver más info"
        cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
        draw.text(
            (qr_x + (qr_img.width - cta_bbox[2]) // 2, qr_y + qr_img.height - 25),
            cta_text, font=cta_font, fill=font_color
        )

        # Texto principal (izquierda con padding)
        text_content = product["name"]
        if product["reference"]:
            text_content += f" (Ref: {product['reference']})"
        # Truncar a 65 caracteres
        wrapped_text = textwrap.fill(
            textwrap.shorten(text_content, width=65),
            width=25
        )

        # Posición texto principal
        text_x = margin + padding_left + 15
        text_y = margin + 40  # Alineado con el QR verticalmente
        draw.multiline_text(
            (text_x, text_y), 
            wrapped_text, 
            font=font, 
            fill=font_color, 
            align="left"
        )

        # Precio e IVA
        if product["price"]:
            try:
                if product["currency"] == "USD":
                    formatted_price = f"USD ${float(product['price']):,.2f}"
                else:
                    formatted_price = f"ARS ${int(product['price']):,}".replace(",", ".")
                
                # Posición precio (misma línea vertical que texto principal)
                price_x = text_x
                price_y = text_y + font_size + 80  # Debajo del nombre
                # Dibujar precio
                draw.text(
                    (price_x, price_y),
                    formatted_price, 
                    font=font_large, 
                    fill=font_color
                )
                
                # Dibujar IVA si existe
                if product["iva"]:
                    # Texto completo del IVA
                    iva_text = f"Precio sin impuestos nacionales (IVA): {product['currency']} {product['iva']}"
                    
                    # Dividir el texto en múltiples líneas usando textwrap
                    wrapped_iva_text = textwrap.fill(iva_text, width=35)  # Ancho ajustado para fuente menor
                    
                    # Posición inicial del IVA
                    iva_y = price_y + font_large.getbbox(formatted_price)[3] + 5
                    
                    # Dibujar el texto envuelto línea por línea
                    for line in wrapped_iva_text.split('\n'):
                        draw.text(
                            (price_x, iva_y),
                            line,
                            font=font_iva,  # Usar la nueva fuente de 20 puntos
                            fill=font_color
                        )
                        # Incrementar la posición vertical para la siguiente línea
                        iva_y += font_iva.getbbox(line)[3] + 5  # Espaciado entre líneas

            except ValueError as e:
                print(f"Error en precio: {product['price']} - {str(e)}")

        # Agregar a página
        current_page.paste(card, (x, y))
        x += card_width + spacing

        if (index + 1) % columns == 0:
            x = margin
            y += card_height + spacing
            row += 1
            
            if row >= max_rows_per_page:
                page_path = os.path.join(output_folder, f"pagina_{page_count}.pdf")
                current_page.save(page_path, resolution=dpi)
                merger.append(page_path)
                page_count += 1
                current_page = Image.new("RGB", (a4_width, a4_height), page_color)
                x, y, row = margin, margin, 0

    # Guardar última página
    if x != margin or y != margin:
        page_path = os.path.join(output_folder, f"pagina_{page_count}.pdf")
        current_page.save(page_path, resolution=dpi)
        merger.append(page_path)

    merged_path = os.path.join(output_folder, "tarjetas_finales.pdf")
    merger.write(merged_path)
    merger.close()

    print(f"PDF generado: {merged_path}")
    return merged_path

if __name__ == "__main__":
    generate_cards("USD")