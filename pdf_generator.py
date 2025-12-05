from reportlab.lib.pagesizes import letter, mm
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from datetime import datetime
import os
import re
from typing import List, Dict, Any, Literal

# Basic sanitization for strings used in PDFs
CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")

def sanitize_str(value: Any, max_len: int = 250) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    s = CONTROL_CHARS_RE.sub('', value).strip()
    if len(s) > max_len:
        s = s[:max_len]
    return s

def generar_planilla(datos: List[Dict[str, Any]], nombre_pdf: str) -> None:
    # Sort data by 'id' numerically before processing
    try:
        datos.sort(key=lambda x: int(x.get("id", 0)) if x.get("id") is not None else float('inf'))
    except (ValueError, TypeError) as sort_error:
        print(f"Warning: Could not numerically sort data by ID in generar_planilla: {sort_error}")
        # Fallback to string sort if numeric fails
        datos.sort(key=lambda x: str(x.get("id", '')) if x.get("id") is not None else '')

    doc = SimpleDocTemplate(nombre_pdf, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []    # Título principal con estilo personalizado

    # --- Calcular totales y balance (suma de netos por tipo) ---
    compras_total = 0.0
    ventas_total = 0.0
    for item in datos:
        try:
            tipo_item = item.get("tipo")
            neto_val = item.get("neto")
            if neto_val is None or str(neto_val).strip() == "":
                neto_val = 0
            neto_f = float(neto_val)
            if tipo_item == "Compra":
                compras_total += neto_f
            elif tipo_item == "Venta":
                ventas_total += neto_f
        except (ValueError, TypeError):
            print(f"Warning: Could not parse neto value '{item.get('neto')}' for item id {item.get('id')}")

    balance_val = compras_total - ventas_total

    # Helper local formatter (same behavior as formatear_numero used later)
    def _fmt_int_dots(valor):
        try:
            if valor is None or str(valor).strip() == "":
                return "0"
            num = int(float(valor))
            return "{:,}".format(num).replace(",", ".")
        except (ValueError, TypeError):
            return "0"

    balance_fmt = _fmt_int_dots(balance_val)

    # Add Balance Neto at top
    balance_style = styles['Heading2'].clone('BalanceStyle')
    balance_style.fontSize = 14
    balance_style.spaceAfter = 6
    balance_style.textColor = colors.HexColor("#293741")
    balance_style.alignment = 1  # Center
    elements.append(Paragraph(f"Balance Neto: {balance_fmt} Kgs", balance_style))

    titulo_style = styles['Title'].clone('CustomTitle')
    titulo_style.fontSize = 16
    titulo_style.spaceAfter = 20
    titulo_style.textColor = colors.HexColor('#2c3e50')  # Azul oscuro elegante
    titulo_style.underline = True # Add underline
    fecha_hora_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
    elements.append(Paragraph(f"<u>Planilla General - {fecha_hora_actual}</u>", titulo_style))
    elements.append(Spacer(1, 15))

    # Función auxiliar para formatear números
    def formatear_numero(valor):
        try:
            if valor is None or str(valor).strip() == "":
                return "0"
            num = float(valor)
            return "{:,}".format(int(num)).replace(",", ".")
        except (ValueError, TypeError):
            return "0"
            
    # Encabezados comunes (sin Kg)
    common_headers = ["ID", "Fecha", "Proveedor/Cliente", "Material", "Bruto", "Tara", "Merma", "Neto", "Hora Ing.", "Hora Sal."]
    
    # Encabezados específicos para compras (incluyen Chofer y Patente)
    compras_headers = common_headers.copy()
    compras_headers.insert(3, "Chofer")
    
    # Encabezados específicos para ventas (incluyen Transporte y Patente)
    ventas_headers = common_headers.copy()
    ventas_headers.insert(3, "Transporte")

    # Separar datos en compras y ventas
    compras = [item for item in datos if item.get("tipo") == "Compra"]
    ventas = [item for item in datos if item.get("tipo") == "Venta"]

    def crear_seccion_tabla(items, titulo):
        # Estilo personalizado para títulos de sección
        seccion_style = styles['Heading1'].clone('SeccionTitle')
        seccion_style.fontSize = 12
        seccion_style.spaceAfter = 8
        seccion_style.textColor = colors.HexColor('#34495e')  # Gris azulado
        seccion_style.alignment = 1  # Centrado

        # Agregar título de sección con el nuevo estilo
        elements.append(Paragraph(titulo, seccion_style))
        elements.append(Spacer(1, 6))

        if not items:
            elements.append(Paragraph("No hay registros para mostrar", styles['Normal']))
            elements.append(Spacer(1, 12))
            return        # Preparar datos para la tabla usando los headers correspondientes
        headers = compras_headers if titulo == "COMPRAS" else (ventas_headers if titulo == "VENTAS" else common_headers)
        data = [headers]
        styleN = styles['Normal'] # Get the normal style for paragraphs

        for item in items:
            fila = [
                Paragraph(sanitize_str(str(item.get("id", "") or ""), max_len=20), styleN), # Wrap ID in Paragraph
                Paragraph(item.get("fecha", "") or "", styleN), # Wrap Fecha in Paragraph
                Paragraph((item.get("proveedor", "") if "proveedor" in item else item.get("cliente", "")) or "", styleN), # Wrap Proveedor/Cliente in Paragraph
            ]
            
            # Agregar Chofer o Transporte según el tipo
            if titulo == "COMPRAS":
                fila.extend([
                    Paragraph(item.get("chofer", "") or "", styleN), # Wrap Chofer in Paragraph
                ])
            elif titulo == "VENTAS":
                fila.extend([
                    Paragraph(item.get("transporte", "") or "", styleN),  # Wrap Transporte in Paragraph
                ])
                
            fila.extend([
                Paragraph(sanitize_str(item.get("mercaderia", "") or "", max_len=80), styleN), # Wrap Mercaderia in Paragraph
                Paragraph(formatear_numero(item.get("bruto", 0)), styleN), # Wrap numeric in Paragraph
                Paragraph(formatear_numero(item.get("tara", 0)), styleN), # Wrap numeric in Paragraph
                Paragraph(formatear_numero(item.get("merma", 0)), styleN), # Wrap numeric in Paragraph
                Paragraph(formatear_numero(item.get("neto", 0)), styleN), # Wrap numeric in Paragraph
                Paragraph(item.get("hora_ingreso", "--:--") or "", styleN), # Wrap Hora Ing. in Paragraph
                Paragraph(item.get("hora_salida", "--:--") or "", styleN) # Wrap Hora Sal. in Paragraph
            ])
            data.append(fila)

        # Calculate total neto, safely handling non-numeric values
        total_neto = 0
        for item in items:
            neto_value = item.get("neto")
            if neto_value is not None and str(neto_value).strip() != "":
                try:
                    total_neto += float(neto_value)
                except (ValueError, TypeError):
                    # Ignore values that cannot be converted to float
                    print(f"Warning: Could not convert neto value '{neto_value}' to float for total calculation.")
                    pass # Skip this value

        total_neto_fmt = formatear_numero(total_neto)

        # Add total row
        total_row = [""] * len(headers)
        total_row[0] = "Total Kgs Netos:" # Label in first column
        # Find the index of the "Neto" column
        try:
            neto_col_index = headers.index("Neto")
            total_row[neto_col_index] = f"{total_neto_fmt}" # Total in Neto column
        except ValueError:
            print("Warning: 'Neto' column not found in headers.")
            # Fallback: add total at the end if 'Neto' column is not found
            total_row[-1] = f"<b>{total_neto_fmt}</b>"

        data.append(total_row)

        # Calcular anchos de columna según el tipo de tabla
        if titulo == "COMPRAS":
            colWidths = [25, 55, 95, 75, 95, 45, 45, 40, 45, 40, 40, 40]  # Ajustado para incluir Chofer y Patente
        elif titulo == "VENTAS":
            colWidths = [25, 55, 95, 75, 95, 45, 45, 40, 45, 40, 40, 40]  # Ajustado para incluir Transporte y Patente
        else:
            colWidths = [30, 50, 100, 100, 55, 55, 55, 55, 45, 45]  # Original sin campos adicionales

        # Crear tabla
        table = Table(data, colWidths=colWidths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),  # Azul oscuro elegante para encabezados
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'), # Center header
            ('ALIGN', (0, 1), (-1, -2), 'CENTER'), # Center data rows (excluding total)
            ('ALIGN', (0, -1), (-1, -1), 'CENTER'), # Center total row
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),  # Set font size to 9 for header row
            ('FONTSIZE', (0, 1), (-1, -2), 6),  # Set font size to 6 for data rows
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), # Bold for total row
            ('FONTSIZE', (0, -1), (-1, -1), 12), # Font size for total row
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8), # Add top padding to header
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6), # Add padding to data rows
            ('TOPPADDING', (0, 1), (-1, -1), 6), # Add padding to data rows
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f5f6fa')),  # Gris muy claro para el content (excluding total)
            ('BACKGROUND', (0, 2), (-1, -3), colors.HexColor('#e9ecef')),  # Slightly darker grey for alternate rows (excluding total)
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#bdc3c7')), # Light grey background for total row
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),  # Gris claro para las líneas
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')), # Add outer box
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')), # Add inner grid lines
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black), # Add a line above the total row
            ('SPAN', (0, -1), (neto_col_index - 1, -1)), # Merge cells for the total label
            # Removed specific right alignment for numeric columns to ensure all data is centered
        ]))

        elements.append(table)
        elements.append(Spacer(1, 12))


    # Ordenar compras y ventas por ID de manera numérica por separado (fallback a string si falla)
    def _sort_by_id(items):
        try:
            return sorted(items, key=lambda x: int(x.get("id", 0)) if x.get("id") is not None else float('inf'))
        except (ValueError, TypeError):
            return sorted(items, key=lambda x: str(x.get("id", '')) if x.get("id") is not None else '')

    compras = _sort_by_id(compras)
    ventas = _sort_by_id(ventas)

    # Crear sección de Compras primero y luego Ventas
    crear_seccion_tabla(compras, "COMPRAS")
    crear_seccion_tabla(ventas, "VENTAS")

    # Generar PDF
    try:
        doc.build(elements)
        print(f"Planilla general generada: {nombre_pdf}")
    except Exception as e:
        print(f"Error al generar la planilla: {e}")
        raise

def crear_pdf_recibo(datos: List[Dict[str, Any]], nombre_pdf="ticket.pdf", tipo: Literal["ticket", "planilla"] = "ticket", tipo_recibo: str = "", copies: int = 1):
    if tipo == "planilla":
        return generar_planilla(datos, nombre_pdf)

    # Si es ticket individual, continuamos con la lógica original
    width, height = letter
    c = canvas.Canvas(nombre_pdf, pagesize=letter)
    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleN.alignment = 0 # Left aligned

    # --- Constants ---
    margin = 20 * mm
    col1_x = margin
    col2_x = margin + 90 * mm
    label_offset = 2 * mm # Space between label and value start
    value_offset = 30 * mm # Start of value relative to column start
    right_align_offset = 45 * mm # Reduced: Position for right-aligned numbers (closer to label)
    kgs_offset = 50 * mm # Reduced: Position for "Kgs" (closer to number)
    line_height = 5 * mm # Reduced line height
    section_space = 3 * mm # Reduced section space

    # --- Fonts ---
    font_regular = "Helvetica"
    font_name = "Helvetica"  # usar regular para etiquetas
    font_bold = "Helvetica-Bold"
    font_size_normal = 10
    font_size_large = 12
    font_size_header = 14
    # Tamaños específicos del header del recibo
    font_size_company_title = 12  # antes: 16 (más pequeño a pedido)
    font_size_subtitle = 10       # se mantiene igual

    # --- Data Extraction ---
    if not isinstance(datos, list) or not datos:
        print("Error: No se proporcionaron datos válidos para generar el PDF.")
        raise ValueError("No se proporcionaron datos válidos para generar el PDF.")
    data = datos[0] # Assuming only one entry per PDF

    # Asegurar que los campos de texto NUNCA sean None para evitar errores en ReportLab
    fecha = sanitize_str(data.get("fecha", "") or "")
    mercaderia = sanitize_str(data.get("mercaderia", "") or "")
    bruto = data.get("bruto", 0)
    tara = data.get("tara", 0)
    merma = data.get("merma", 0)
    neto = data.get("neto", 0)
    precio_kg = data.get("precio_kg", 0)  # Add precio_kg
    importe = data.get("importe", 0)      # Add importe
    hora_ingreso_str = data.get("hora_ingreso", "")
    hora_salida_str = data.get("hora_salida", "")

    # Detectar tipo efectivo del recibo a partir del parámetro o de los datos
    tipo_item = (tipo_recibo or data.get("tipo", "")).strip().capitalize()
    proveedor = ""
    chofer = ""
    transporte = ""
    patente = sanitize_str(data.get("patente", "") or "")
    incoterm = ""
    if tipo_item == "Compra":
        proveedor = sanitize_str(data.get("proveedor", "") or "")
        chofer = sanitize_str(data.get("chofer", "") or "")
    elif tipo_item == "Venta":
        proveedor = sanitize_str(data.get("cliente", "") or "")
        transporte = sanitize_str(data.get("transporte", "") or "")  # usar transporte en ventas
        # Optional incoterm para ventas (CIF/FOB)
        try:
            incoterm = data.get("incoterm", "")
            if isinstance(incoterm, str):
                incoterm = incoterm.strip().upper()
                if incoterm not in ("CIF", "FOB"):
                    incoterm = ""
            else:
                incoterm = ""
        except Exception:
            incoterm = ""
    # Asegurar que incoterm sea texto seguro
    incoterm = sanitize_str(incoterm or "", max_len=10)

    def format_time_ampm(time_str):
        if not time_str or time_str == '--:--':
            return '--:--'
        try:
            # Attempt parsing with seconds first, then without
            try:
                time_obj = datetime.strptime(time_str, '%H:%M:%S').time()
            except ValueError:
                time_obj = datetime.strptime(time_str, '%H:%M').time()
            return time_obj.strftime('%I:%M %p') # Simplified AM/PM format
        except ValueError:
            return time_str # Return original if format is unexpected

    hora_ingreso = format_time_ampm(hora_ingreso_str)
    hora_salida = format_time_ampm(hora_salida_str)

    def formatear_numero(valor):
        try:
            # Handle potential None or empty strings before conversion
            if valor is None or str(valor).strip() == "":
                return "0"
            # Convert to float first for safety, then int for formatting
            num = int(float(valor))
            return "{:,}".format(num).replace(",", ".")
        except (ValueError, TypeError):
            return "0" # Return "0" if conversion fails

    bruto_fmt = formatear_numero(bruto)
    tara_fmt = formatear_numero(tara)
    merma_fmt = formatear_numero(merma)
    neto_fmt = formatear_numero(neto)

    # --- PDF Drawing ---
    def draw_page():
        # Encabezado empresarial con banda, logo y títulos
        header_top = height - margin
        header_h = 22 * mm
        header_bottom = header_top - header_h
        c.setFillColor(colors.HexColor('#f2f5f7'))
        c.setStrokeColor(colors.HexColor('#d9e1e6'))
        c.setLineWidth(0.5)
        c.rect(margin, header_bottom, width - 2*margin, header_h, fill=1, stroke=1)

        # Logo
        logo_drawn = False
        logo_w = 18 * mm
        logo_h = 18 * mm
        logo_x = margin + 3 * mm
        logo_y = header_bottom + (header_h - logo_h) / 2
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            candidatos_logo = [
                os.path.join(base_dir, "static", "logo.png"),
                os.path.join(base_dir, "logo.png"),
            ]
            logo_path = next((p for p in candidatos_logo if os.path.exists(p)), None)
            if logo_path:
                c.drawImage(logo_path, logo_x, logo_y, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
                logo_drawn = True
            else:
                print("Aviso: logo.png no encontrado en static/ ni en la raíz del proyecto.")
        except Exception as e:
            print(f"Aviso: No se pudo dibujar el logo: {e}")

        # Títulos en encabezado
        empresa = "Industrias Metalurgicas Ronanfer S.A."
        subtitulo = "Ticket de Pesada" + (f" - {tipo_item}" if tipo_item else "")
        text_left_x = logo_x + (logo_w + 4 * mm if logo_drawn else 4 * mm)
        c.setFillColor(colors.black)
        c.setFont(font_bold, font_size_company_title)
        c.drawString(text_left_x, header_bottom + header_h - 8 * mm, empresa)
        if subtitulo.strip():
            c.setFont(font_regular, font_size_subtitle)
            c.setFillColor(colors.black)
            c.drawString(text_left_x, header_bottom + 5 * mm, subtitulo)

        # Ticket y fecha en el extremo derecho del header
        c.setFont(font_regular, 9)
        c.setFillColor(colors.black)
        ticket_id = str(data.get("id", "-"))
        fecha_hdr = fecha
        right_block_x = width - margin - 60 * mm
        c.drawRightString(width - margin - 2 * mm, header_bottom + header_h - 7 * mm, f"Ticket N° {ticket_id}")
        c.setFillColor(colors.black)

        # Posición inicial de contenido y color negro por defecto
        y_pos = header_bottom - section_space * 2
        c.setFillColor(colors.black)

        # --- Details Section (Two Columns) ---
        c.setFont(font_name, font_size_normal)

        # Row 1: Fecha / Proveedor/Cliente (part 1)
        c.drawString(col1_x, y_pos, "Fecha:")
        c.setFont(font_bold, font_size_normal)
        c.drawString(col1_x + value_offset, y_pos, fecha)
        c.setFont(font_name, font_size_normal)
        # Change label based on tipo
        label_proveedor_cliente = "Cliente:" if tipo_item == "Venta" else "Proveedor:"
        c.drawString(col2_x, y_pos, label_proveedor_cliente)
        # Use Paragraph for potentially long provider names, append incoterm if provided (Ventas)
        styleN.fontName = font_bold
        try:
            proveedor_txt = proveedor
            if tipo_item == "Venta" and incoterm:
                proveedor_txt = f"{proveedor} - {incoterm}"
        except Exception:
            proveedor_txt = proveedor
        p = Paragraph(proveedor_txt, styleN)
        p.wrapOn(c, width - col2_x - value_offset - margin, line_height)
        p_height = p.height
        p.drawOn(c, col2_x + value_offset, y_pos - (p_height - line_height)/2 ) # Adjust Y slightly for alignment
        styleN.fontName = font_name

        y_pos -= max(line_height, p_height) + section_space # Move down by the taller element
        
        # Row 2: Material
        c.drawString(col1_x, y_pos, "Material:")
        styleN.fontName = font_bold
        p = Paragraph(mercaderia or "", styleN)
        p.wrapOn(c, width - col1_x - value_offset - margin, line_height)
        p_height = p.height
        p.drawOn(c, col1_x + value_offset, y_pos - (p_height - line_height)/2)
        styleN.fontName = font_name

        y_pos -= max(line_height, p_height) + section_space
        
        # Row 3: Chofer/Transporte / Patente
        c.drawString(col1_x, y_pos, "Chofer/Transp.:")
        c.setFont(font_bold, font_size_normal)
        # Use 'transporte' para Venta, 'chofer' para Compra
        display_chofer_transporte = (transporte if tipo_item == "Venta" else chofer) or ""
        c.drawString(col1_x + value_offset, y_pos, display_chofer_transporte)
        c.setFont(font_name, font_size_normal)
        c.drawString(col2_x, y_pos, "Patente:")
        c.setFont(font_bold, font_size_normal)
        c.drawString(col2_x + value_offset, y_pos, patente or "")
        c.setFont(font_name, font_size_normal)

        y_pos -= line_height + section_space

        # --- Separator Line ---
        c.setStrokeColor(colors.black)
        c.line(margin, y_pos, width - margin, y_pos)
        y_pos -= section_space * 2
        c.setStrokeColor(colors.black)

        # --- Weights and Times Section (Two Columns) ---
        c.setFont(font_name, font_size_normal)

        # (quitado) Recuadro de "Pesos y Tiempos" para un estilo más limpio
        # Mantener colores en negro para el texto
        c.setStrokeColor(colors.black)
        c.setFillColor(colors.black)

        # Bruto / Hora Ingreso
        c.drawString(col1_x, y_pos, "Peso Bruto:")
        c.setFont(font_bold, font_size_normal)
        c.drawRightString(col1_x + right_align_offset, y_pos, bruto_fmt)
        c.drawString(col1_x + kgs_offset, y_pos, "Kgs")
        c.setFont(font_name, font_size_normal)
        c.drawString(col2_x, y_pos, "Hora Ingreso:")
        c.setFont(font_bold, font_size_normal)
        c.drawString(col2_x + value_offset, y_pos, hora_ingreso)
        c.setFont(font_name, font_size_normal)
        y_pos -= line_height

        # Tara / Hora Salida
        c.drawString(col1_x, y_pos, "Peso Tara:")
        c.setFont(font_bold, font_size_normal)
        c.drawRightString(col1_x + right_align_offset, y_pos, tara_fmt)
        c.drawString(col1_x + kgs_offset, y_pos, "Kgs")
        c.setFont(font_name, font_size_normal)
        c.drawString(col2_x, y_pos, "Hora Salida:")
        c.setFont(font_bold, font_size_normal)
        c.drawString(col2_x + value_offset, y_pos, hora_salida)
        c.setFont(font_name, font_size_normal) # Reset font for label
        y_pos -= line_height

        # Merma
        c.drawString(col1_x, y_pos, "Merma:")
        c.setFont(font_bold, font_size_normal)
        c.drawRightString(col1_x + right_align_offset, y_pos, merma_fmt)
        c.drawString(col1_x + kgs_offset, y_pos, "Kgs")
        c.setFont(font_name, font_size_normal) # Reset font for label
        y_pos -= line_height

        # Precio x Kg / Importe
        c.drawString(col1_x, y_pos, "Precio x Kg:")
        c.setFont(font_bold, font_size_normal)
        precio_display = f"$ {formatear_numero(precio_kg)}" if precio_kg else "$"
        c.drawRightString(col1_x + right_align_offset, y_pos, precio_display)
        c.setFont(font_name, font_size_normal)
        c.drawString(col2_x, y_pos, "Importe:")
        c.setFont(font_bold, font_size_normal)
        # Formato moneda más profesional: $ 12.345,67
        def formatear_moneda(valor):
            try:
                if valor is None or str(valor).strip() == "":
                    return "$"
                num = float(valor)
                entero, dec = divmod(round(num * 100), 100)
                entero_fmt = "{:,}".format(int(entero)).replace(",", ".")
                return f"$ {entero_fmt},{int(dec):02d}"
            except (ValueError, TypeError):
                return "$"

        importe_display = formatear_moneda(importe) if importe else "$"
        c.drawString(col2_x + value_offset, y_pos, importe_display)
        c.setFont(font_name, font_size_normal) # Reset font for label
        y_pos -= line_height * 1 # Extra space before Neto

        # --- Separator Line ---
        c.setStrokeColor(colors.HexColor('#d9e1e6'))
        c.line(margin, y_pos, width - margin, y_pos)
        y_pos -= section_space
        c.setStrokeColor(colors.black)

        # --- Neto Section (Highlighted) ---
        font_size_neto = 13
        neto_box_height = font_size_neto * 1.5 # Increased box height
        neto_box_width = width - 2 * margin
        neto_box_y = y_pos - neto_box_height - section_space

        # Draw the box
        c.setLineWidth(1.5)
        c.setStrokeColor(colors.black)
        c.setFillColor(colors.white)
        try:
            c.roundRect(margin, neto_box_y, neto_box_width, neto_box_height, 6, stroke=1, fill=1)
        except Exception:
            c.rect(margin, neto_box_y, neto_box_width, neto_box_height, stroke=1, fill=1)

        # Prepare text
        neto_text = f" Neto:    {neto_fmt} Kgs"

        # Set font for calculating width
        c.setFont(font_bold, font_size_neto)
        c.setFillColor(colors.black)

        # Calculate text width to center it
        text_width = c.stringWidth(neto_text, font_bold, font_size_neto)
        
        # Calculate positions
        text_x = margin + (neto_box_width - text_width) / 2
        text_y = neto_box_y + (neto_box_height - font_size_neto) / 2 + (font_size_neto * 0.1) # Adjust for better vertical centering

        # Draw the centered text
        c.drawString(text_x, text_y, neto_text)

        y_pos = neto_box_y - section_space * 1.5 # Update y_pos below the box
        c.setFont(font_name, font_size_normal) # Reset font to normal for subsequent text

        # --- Footer ---
        c.setLineWidth(0.5)
        c.setStrokeColor(colors.HexColor("#000000"))
        c.line(margin, y_pos, width - margin, y_pos)
        c.setFont(font_regular, 8)
        c.setFillColor(colors.black)
        footer_text = f"I.M.R. Sistema de Pesada • Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        c.drawCentredString(width/2.0, y_pos - 3 * mm, footer_text)

    # Generate pages for copies
    for i in range(copies):
        draw_page()
        if i < copies - 1:
            c.showPage()

    # --- Save PDF ---
    c.save()
    print(f"PDF '{nombre_pdf}' generado con {copies} página(s).")

# Example Usage (for testing if run directly)
if __name__ == '__main__':
    # Datos de ejemplo de compras
    datos_compras = [
        {
            "id": 1,
            "tipo": "Compra",
            "proveedor": "RECICLADOS MANZANA.",
            "chofer": "FRANCISCO",
            "patente": "AB123CD",
            "bruto": 25500,
            "hora_ingreso": "09:15",
            "hora_salida": "14:30",
            "mercaderia": "HIERRO DIMENSIONADO",
            "fecha": "16/04/25",
            "tara": 5250,
            "merma": 150,
            "neto": 20100
        }
    ]

    # Crear ticket de ejemplo
    crear_pdf_recibo(datos_compras, "ticket_ejemplo.pdf")

    # Crear planilla de ejemplo con ambos tipos de registros
    datos_planilla = datos_compras + [
        {
            "id": 124,
            "tipo": "Venta",
            "cliente": "Cliente Ejemplo S.A.",
            "bruto": 15500.50,
            "hora_ingreso": "10:30",
            "hora_salida": "15:45",
            "mercaderia": "Chatarra Mixta",
            "fecha": "16/04/2025",
            "tara": 3250.0,
            "merma": 100,
            "neto": 12150.50
        }
    ]
    crear_pdf_recibo(datos_planilla, "planilla_ejemplo.pdf", "planilla")
