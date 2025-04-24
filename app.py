from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import csv
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from qr_generator import generate_qr_codes
from generate_product_cards import generate_cards

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATA_JSON_PATH = 'data/products.json'

# Ruta para la página principal
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            # Leer el archivo CSV y extraer los IDs de productos
            ids_productos = []
            csv_file = csv.DictReader(file.stream.read().decode('utf-8').splitlines(), delimiter=';')
            for row in csv_file:
                ids_productos.append(row['Product ID'])
            
            # Reescribir el archivo JSON con los nuevos IDs
            with open(DATA_JSON_PATH, 'w', encoding='utf-8') as json_file:
                json.dump(ids_productos, json_file)

            flash('Archivo CSV cargado y IDs actualizados exitosamente.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Por favor, carga un archivo CSV válido.', 'error')

    return render_template('index.html')

# Ruta para generar códigos QR
@app.route('/generate', methods=['POST'])
def generate():
    currency = request.form.get('currency', 'ARS')

    if not os.path.exists(DATA_JSON_PATH):
        flash('No se encontró la lista de IDs de productos. Carga un CSV primero.', 'error')
        return redirect(url_for('index'))

    with open(DATA_JSON_PATH, 'r', encoding='utf-8') as json_file:
        product_ids = json.load(json_file)

    if not product_ids:
        flash('No hay IDs de productos para generar los códigos QR.', 'error')
        return redirect(url_for('index'))

    # Llamar a la función para generar códigos QR
    generate_qr_codes(product_ids, currency)

    flash('Códigos QR generados exitosamente.', 'success')
    return redirect(url_for('index'))

# Ruta para generar tarjetas y descargar el PDF
@app.route("/generate_cards", methods=["POST"])
def generate_cards_route():
    currency = request.form.get('currency', 'ARS')

    if not os.path.exists(DATA_JSON_PATH):
        flash("No se encontró la lista de IDs de productos. Carga un CSV primero.", "error")
        return redirect(url_for("index"))

    with open(DATA_JSON_PATH, 'r', encoding='utf-8') as json_file:
        product_ids = json.load(json_file)

    if not product_ids:
        flash("No hay IDs de productos para generar tarjetas.", "error")
        return redirect(url_for("index"))

    try:
        # Llama a la función que genera las tarjetas con los IDs actuales
        merged_pdf_path = generate_cards(currency)

        if os.path.exists(merged_pdf_path):
            return send_file(merged_pdf_path, as_attachment=True, download_name="tarjetas_productos.pdf")
        else:
            flash("No se encontró el archivo PDF generado.", "error")
            return redirect(url_for("index"))
    except Exception as e:
        flash(f"Error al generar las tarjetas: {str(e)}", "error")
        return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)