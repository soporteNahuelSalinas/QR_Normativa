import json
import requests
from requests.auth import HTTPBasicAuth
import qrcode
import os
import xml.etree.ElementTree as ET
import re

# Configuraciones de la API
api_url = 'https://tienda.anywayinsumos.com.ar/api/products/'
api_key = '7FBXGUHYR2PXIGBS7GC3AAQ7BHEQX57E'
tinyurl_api_url = 'http://tinyurl.com/api-create.php?url='
output_dir = 'qrcodes-manuales'

# Función para obtener el valor del dólar
def obtener_valor_venta():
    url = "https://dolarapi.com/v1/dolares/oficial"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        venta = data.get("venta")

        if venta is not None:
            print(f"Valor de venta: {venta}")
            return venta
        else:
            print("El campo 'venta' no está presente en la respuesta.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error al realizar la solicitud: {e}")
        return None

DOLAR_VENTA = obtener_valor_venta()

# Limpieza de nombres
def clean_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name.strip()[:100]

# Normalizar precios con impuestos
def normalize_price(price, tax_type):
    try:
        price = float(price)
        if tax_type == "1":
            price *= 1.21  # Aplicar IVA 21%
        elif tax_type == "2":
            price *= 1.105  # Aplicar IVA 10.5%
        return str(int(price))
    except ValueError:
        return "0"

# Obtener datos del producto
def fetch_product_data(product_id):
    url = f"{api_url}{product_id}"
    try:
        response = requests.get(url, auth=HTTPBasicAuth(api_key, ''), timeout=10)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        product_name = root.find('.//name/language').text
        link_rewrite = root.find('.//link_rewrite/language').text
        reference = root.find('.//reference').text
        price = root.find('.//price').text
        tax_type = root.find('.//id_tax_rules_group').text
        
        # Obtener precio en pesos con impuestos
        final_price_pesos_str = normalize_price(price, tax_type)
        final_price_pesos = float(final_price_pesos_str)
        
        # Calcular precio en dólares
        final_price_usd = round(final_price_pesos / DOLAR_VENTA, 2)
        final_price_usd_str = f"{final_price_usd:.2f}"

        return {
            "id": product_id,
            "name": product_name,
            "link_rewrite": link_rewrite,
            "reference": reference,
            "price_pesos": final_price_pesos_str,
            "price_usd": final_price_usd_str,
            "tax_type": tax_type
        }
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud para el producto {product_id}: {e}")
    except ET.ParseError:
        print(f"Error al parsear XML para el producto {product_id}.")
    return None

# Generar código QR
def generate_qr(product_data, currency):
    os.makedirs(output_dir, exist_ok=True)
    product_url = f"https://tienda.anywayinsumos.com.ar/{product_data['link_rewrite']}/{product_data['id']}-{product_data['link_rewrite']}.html"
    
    try:
        response = requests.get(tinyurl_api_url + product_url, timeout=10)
        response.raise_for_status()
        short_url = response.text

        qr_img = qrcode.make(short_url)
        cleaned_name = clean_filename(product_data["name"])

        # Calcular IVA
        tax_type = product_data['tax_type']
        final_price_pesos = float(product_data['price_pesos'])
        if tax_type == "1":
            tax_rate = 0.21
        elif tax_type == "2":
            tax_rate = 0.105
        else:
            tax_rate = 0.0
        
        original_price = final_price_pesos / (1 + tax_rate)
        iva_ars = original_price

        # Convertir IVA a USD si es necesario
        if currency == "USD":
            iva_usd = round(iva_ars / DOLAR_VENTA, 2)
            iva_str = f"{iva_usd:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            iva_part = f"IVA_USD${iva_str}"
        else:
            iva_str = f"{iva_ars:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            iva_part = f"IVA_${iva_str}"

        if currency == "USD":
            # Formatear USD con decimales y comas
            price_value = float(product_data['price_usd'])
            price_str = f"USD_${price_value:,.2f}"
        else:
            # Formatear ARS sin decimales con puntos
            price_value = int(product_data['price_pesos'])
            price_str = f"ARS_${price_value:,}".replace(",", ".")

        qr_filename = os.path.join(output_dir, f"{cleaned_name}_{product_data['reference']}__{iva_part}__PRECIO__{price_str}.png")

        if os.path.exists(qr_filename):
            print(f"El archivo {qr_filename} ya existe. Saltando...")
            return

        qr_img.save(qr_filename)
        print(f"Código QR generado: {qr_filename}")
    except requests.exceptions.RequestException as e:
        print(f"Error al acortar URL para el producto {product_data['id']}: {e}")
    except Exception as e:
        print(f"Error al generar el código QR: {e}")

# Generar códigos QR para una lista de IDs
def generate_qr_codes(product_ids, currency):
    # Eliminar QR existentes al cambiar de divisa
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith(".png"):
                file_path = os.path.join(output_dir, filename)
                try:
                    os.remove(file_path)
                    print(f"Archivo existente eliminado: {file_path}")
                except Exception as e:
                    print(f"Error eliminando {file_path}: {e}")

    # Generar nuevos QR
    for product_id in product_ids:
        product_data = fetch_product_data(product_id)
        if product_data:
            generate_qr(product_data, currency)

# Ejecución principal
if __name__ == "__main__":
    DOLAR_VENTA = obtener_valor_venta()