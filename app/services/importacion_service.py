import io
import re
import hashlib
import time
from datetime import datetime, date, timedelta
from typing import List, Tuple, Dict, Any
import pandas as pd
from sqlalchemy.orm import Session
from app.models.cobranzas import (
    Cliente, Cargo, TelefonoCliente, MovimientoCargo, HistorialImportacion,
    Tramo, PlantillaMapeo, MapeoColumnasTramo, ConfiguracionPrioridadTelefonos,
    Campana, Departamento, Seccion, PerfilRiesgo, SegmentoRolling
)
from app.schemas.importacion import ValidationErrorDetail, ImportSummaryResponse

class ImportacionService:

    @staticmethod
    def calcular_hash_archivo(file_content: bytes) -> str:
        """Calcula el Hash SHA-256 de un archivo para evitar duplicados."""
        return hashlib.sha256(file_content).hexdigest()

    @staticmethod
    def verificar_duplicado(db: Session, file_hash: str) -> bool:
        """Comprueba si el hash de un archivo ya fue importado."""
        exists = db.query(HistorialImportacion).filter(
            HistorialImportacion.hash_archivo == file_hash
        ).first()
        return exists is not None

    @staticmethod
    def parse_date(value: Any) -> date:
        """Parsea de forma robusta cualquier valor de celda a una fecha de Python."""
        if pd.isna(value) or str(value).strip() == "":
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        
        # OADate de Excel (float serial)
        if isinstance(value, (int, float)):
            try:
                return (datetime(1899, 12, 30) + timedelta(days=int(value))).date()
            except Exception:
                raise ValueError("Número serial de fecha inválido en Excel")
                
        # Parseo de Strings
        text = str(value).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Formato de fecha '{text}' no reconocido (esperado DD/MM/AAAA)")

    @staticmethod
    def parse_number(value: Any) -> float:
        """Limpia caracteres monetarios y convierte valores a números flotantes."""
        if pd.isna(value) or str(value).strip() == "":
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
            
        text = str(value).strip()
        text = text.replace("$", "").replace("Bs", "").replace(" ", "")
        
        if "," in text and "." not in text:
            text = text.replace(",", ".")
        elif "," in text and "." in text:
            text = text.replace(",", "")  # Quitar separador de miles
            
        try:
            return float(text)
        except ValueError:
            raise ValueError(f"Monto '{value}' no es un número válido")

    @classmethod
    def validar_y_mapear_columnas(
        cls, file_df: pd.DataFrame, plantilla: PlantillaMapeo
    ) -> Tuple[Dict[str, str], List[ConfiguracionPrioridadTelefonos], List[ValidationErrorDetail]]:
        """
        Valida que las columnas obligatorias mapeadas en la plantilla existan en el DataFrame.
        Devuelve un diccionario de mapeo sistema->columna_excel, teléfonos mapeados y lista de errores de cabeceras.
        """
        errores = []
        mapeo_sistema_excel = {}
        headers_excel = [str(h).strip().lower() for h in file_df.columns]

        # 1. Validar catálogo de columnas mapeadas
        for col_tramo in plantilla.columnas:
            col_excel = col_tramo.nombre_columna_excel.strip()
            es_obligatoria = col_tramo.es_obligatorio

            # Buscar coincidencia (sin distinguir mayúsculas ni espacios)
            idx = -1
            for i, h in enumerate(headers_excel):
                if h == col_excel.lower():
                    idx = i
                    break

            # Si es BASE_SALDOS o BASE_ACTUALIZACION, el nombre y el monto inicial NO son obligatorios en las columnas del Excel
            if str(plantilla.tipo_proceso).strip().upper() in ("BASE_SALDOS", "BASE_ACTUALIZACION"):
                if col_tramo.campo_sistema in ("nombre_completo", "INICIAL"):
                    es_obligatoria = False

            if idx == -1:
                if es_obligatoria:
                    errores.append(ValidationErrorDetail(
                        fila=1,
                        columna=col_excel,
                        mensaje=f"La columna obligatoria '{col_excel}' no se encuentra en el archivo Excel."
                    ))
            else:
                mapeo_sistema_excel[col_tramo.campo_sistema] = file_df.columns[idx]

        # En base a las reglas de negocio, la columna 'campana' es obligatoria
        if "campana" not in mapeo_sistema_excel:
            errores.append(ValidationErrorDetail(
                fila=1,
                columna="Campaña",
                mensaje="La plantilla seleccionada debe incluir obligatoriamente el mapeo para el campo 'campana'."
            ))

        # 2. Filtrar teléfonos configurados en esta plantilla
        telefonos_plantilla = [t for t in plantilla.telefonos if t.activo]

        return mapeo_sistema_excel, telefonos_plantilla, errores

    @classmethod
    def simular_dry_run(
        cls, file_df: pd.DataFrame, mapeo_columnas: Dict[str, str], tipo_proceso: str = "BASE_ORIGINAL"
    ) -> List[ValidationErrorDetail]:
        """
        Realiza la validación fila por fila del Excel sin tocar la base de datos (Opción A).
        Verifica tipos de datos, fechas y campos requeridos para Código Cliente y Número de Cargo.
        """
        errores = []
        
        # Mapeos de nombres de Excel para validar rápido
        col_cliente = mapeo_columnas.get("codigo_cliente")
        col_cargo = mapeo_columnas.get("numero_cargo")
        col_nombre = mapeo_columnas.get("nombre_completo")
        col_campana = mapeo_columnas.get("campana")
        col_monto_inicial = mapeo_columnas.get("INICIAL")
        col_interes = mapeo_columnas.get("INTERES")
        col_gasto_adm = mapeo_columnas.get("GASTO_ADM")
        col_fecha_cierre = mapeo_columnas.get("fecha_cierre")
        col_fecha_pago = mapeo_columnas.get("fecha_pago")
        col_dias_atraso = mapeo_columnas.get("dias_atraso")

        proceso_tipo = str(tipo_proceso).strip().upper()

        for index, row in file_df.iterrows():
            fila_num = index + 2  # Pandas es 0-indexed y la fila 1 son cabeceras

            # 1. Identificadores obligatorios y no vacíos
            val_cliente = row.get(col_cliente) if col_cliente else None
            val_cargo = row.get(col_cargo) if col_cargo else None
            val_nombre = row.get(col_nombre) if col_nombre else None
            val_campana = row.get(col_campana) if col_campana else None

            if pd.isna(val_cliente) or str(val_cliente).strip() == "":
                errores.append(ValidationErrorDetail(
                    fila=fila_num,
                    columna=col_cliente or "Código Cliente",
                    mensaje="El Código de Cliente es obligatorio y no puede estar vacío."
                ))
            if pd.isna(val_cargo) or str(val_cargo).strip() == "":
                errores.append(ValidationErrorDetail(
                    fila=fila_num,
                    columna=col_cargo or "Número de Cargo",
                    mensaje="El Número de Cargo es obligatorio y no puede estar vacío."
                ))
            
            # Sólo exigimos Nombre Completo si es un proceso de Base Original
            if proceso_tipo == "BASE_ORIGINAL":
                if pd.isna(val_nombre) or str(val_nombre).strip() == "":
                    errores.append(ValidationErrorDetail(
                        fila=fila_num,
                        columna=col_nombre or "Nombre completo",
                        mensaje="El Nombre completo es obligatorio para la subida de Base Original y no puede estar vacío."
                    ))

            if not col_campana:
                errores.append(ValidationErrorDetail(
                    fila=fila_num,
                    columna="Campaña",
                    mensaje="La Campaña no está mapeada en la plantilla seleccionada."
                ))
            elif pd.isna(val_campana) or str(val_campana).strip() == "":
                errores.append(ValidationErrorDetail(
                    fila=fila_num,
                    columna=col_campana,
                    mensaje="La Campaña es obligatoria y no puede estar vacía."
                ))

            # 2. Validación de Montos Financieros
            if col_monto_inicial:
                try:
                    cls.parse_number(row.get(col_monto_inicial))
                except ValueError as e:
                    errores.append(ValidationErrorDetail(
                        fila=fila_num,
                        columna=col_monto_inicial,
                        mensaje=str(e)
                    ))
            elif proceso_tipo == "BASE_ORIGINAL":
                errores.append(ValidationErrorDetail(
                    fila=fila_num,
                    columna="Monto Inicial",
                    mensaje="El Monto Inicial (INICIAL) no está mapeado y es obligatorio para la subida de Base Original."
                ))
            if col_interes and not pd.isna(row.get(col_interes)):
                try:
                    cls.parse_number(row.get(col_interes))
                except ValueError as e:
                    errores.append(ValidationErrorDetail(
                        fila=fila_num,
                        columna=col_interes,
                        mensaje=str(e)
                    ))
            if col_gasto_adm and not pd.isna(row.get(col_gasto_adm)):
                try:
                    cls.parse_number(row.get(col_gasto_adm))
                except ValueError as e:
                    errores.append(ValidationErrorDetail(
                        fila=fila_num,
                        columna=col_gasto_adm,
                        mensaje=str(e)
                    ))

            # 3. Validación de Fechas
            if col_fecha_cierre and not pd.isna(row.get(col_fecha_cierre)):
                try:
                    cls.parse_date(row.get(col_fecha_cierre))
                except ValueError as e:
                    errores.append(ValidationErrorDetail(
                        fila=fila_num,
                        columna=col_fecha_cierre,
                        mensaje=str(e)
                    ))
            if col_fecha_pago and not pd.isna(row.get(col_fecha_pago)):
                try:
                    cls.parse_date(row.get(col_fecha_pago))
                except ValueError as e:
                    errores.append(ValidationErrorDetail(
                        fila=fila_num,
                        columna=col_fecha_pago,
                        mensaje=str(e)
                    ))

            # 4. Días de Atraso
            if col_dias_atraso and not pd.isna(row.get(col_dias_atraso)):
                val_atraso = row.get(col_dias_atraso)
                if str(val_atraso).strip() != "":
                    try:
                        int(float(str(val_atraso).replace(" ", "")))
                    except ValueError:
                        errores.append(ValidationErrorDetail(
                            fila=fila_num,
                            columna=col_dias_atraso,
                            mensaje=f"Días de atraso '{val_atraso}' debe ser un número entero válido."
                        ))

        return errores

    @classmethod
    def procesar_carga_base_original(
        cls,
        db: Session,
        file_df: pd.DataFrame,
        tramo_id: int,
        plantilla: PlantillaMapeo,
        mapeo_columnas: Dict[str, str],
        telefonos_prioridad: List[ConfiguracionPrioridadTelefonos],
        usuario_id: int,
        nombre_archivo: str,
        hash_archivo: str
    ) -> ImportSummaryResponse:
        """
        Ejecuta la importación real en lotes de 1,000 en 1,000 bajo una sola transacción.
        Actualiza perfiles, determina prioridad telefónica, gestiona importes/intereses por diferencia
        y calcula el estado dinámico de las deudas (ACTIVO, VENCIDO, PAGADO) de la nueva campaña.
        """
        inicio_tiempo = time.time()

        # Contadores para el resumen ejecutivo
        clientes_nuevos = 0
        clientes_actualizados = 0
        cargos_nuevos = 0
        cargos_actualizados = 0
        telefonos_nuevos = 0
        telefono_uso_actualizados = 0
        movimientos_financieros_creados = 0
        monto_deuda_inicial_total = 0.0
        monto_interes_total = 0.0
        monto_gasto_adm_total = 0.0
        monto_pagos_total = 0.0

        # Mapeos de columnas del Excel
        col_cliente = mapeo_columnas.get("codigo_cliente")
        col_cargo = mapeo_columnas.get("numero_cargo")
        col_nombre = mapeo_columnas.get("nombre_completo")
        col_departamento = mapeo_columnas.get("departamento")
        col_seccion = mapeo_columnas.get("seccion")
        col_perfil_riesgo = mapeo_columnas.get("perfil_riesgo")
        col_segmento_rolling = mapeo_columnas.get("segmento_rolling")
        col_fecha_cierre = mapeo_columnas.get("fecha_cierre")
        col_fecha_pago = mapeo_columnas.get("fecha_pago")
        col_numero_documento = mapeo_columnas.get("numero_documento")
        col_dias_atraso = mapeo_columnas.get("dias_atraso")
        col_correo = mapeo_columnas.get("correo_electronico")
        col_campana = mapeo_columnas.get("campana")
        col_observacion = mapeo_columnas.get("observacion")

        col_monto_inicial = mapeo_columnas.get("INICIAL")
        col_interes = mapeo_columnas.get("INTERES")
        col_gasto_adm = mapeo_columnas.get("GASTO_ADM")
        col_pago = mapeo_columnas.get("PAGO")

        # Cachés locales para optimizar consultas de semillas en lote
        campanas_cache: Dict[str, int] = {c.nombre: c.id for c in db.query(Campana).all()}
        departamentos_cache: Dict[str, int] = {d.nombre.upper().strip(): d.id for d in db.query(Departamento).all()}
        secciones_cache: Dict[Tuple[int, str], int] = {
            (s.departamento_id, s.nombre.upper().strip()): s.id for s in db.query(Seccion).all()
        }
        perfiles_cache: Dict[str, int] = {p.nombre.upper().strip(): p.id for p in db.query(PerfilRiesgo).all()}
        segmentos_cache: Dict[str, int] = {s.nombre.upper().strip(): s.id for s in db.query(SegmentoRolling).all()}

        # Caché de teléfonos existentes y sus prioridades/tipos del deudor para consulta y secuencia rápida
        # key: (cliente_id, numero_limpio)
        telefonos_existentes_cache = set()
        telefonos_por_cliente_tipo = {}  # key: (cliente_id, tipo_base) -> lista de prioridades
        telefonos_db_prioridades = {}    # key: (cliente_id, numero_limpio) -> prioridad float
        telefonos_db_tipos = {}          # key: (cliente_id, numero_limpio) -> tipo string
        
        # Cargar todos los teléfonos de la base de datos
        all_db_telefonos = db.query(
            TelefonoCliente.cliente_id,
            TelefonoCliente.numero,
            TelefonoCliente.tipo,
            TelefonoCliente.prioridad
        ).all()
        for c_id, num, tipo, prio in all_db_telefonos:
            num_clean = str(num).strip()
            cache_key = (c_id, num_clean)
            telefonos_existentes_cache.add(cache_key)
            telefonos_db_prioridades[cache_key] = float(prio)
            telefonos_db_tipos[cache_key] = str(tipo)
            
            # Limpiar sufijo numérico para obtener la columna padre/base
            tipo_base = re.sub(r"\s*\d+$", "", str(tipo)).strip()
            key_base = (c_id, tipo_base)
            if key_base not in telefonos_por_cliente_tipo:
                telefonos_por_cliente_tipo[key_base] = []
            telefonos_por_cliente_tipo[key_base].append(float(prio))

        hoy = date.today()

        # Iniciar transacción única
        db.begin_nested()  # Usar nested para soporte de transacciones complejas en tests y sub-transacciones
        try:
            lote_actual = []
            
            for index, row in file_df.iterrows():
                # --- 1. DATOS DE IDENTIFICACIÓN ---
                cod_belcor = str(row.get(col_cliente)).strip()
                num_cargo_val = str(row.get(col_cargo)).strip()

                # --- 2. SIEMBRAS DINÁMICAS (CAMPOS RELACIONADOS) ---
                # A. Campaña
                campana_val = str(row.get(col_campana)).strip()
                if campana_val not in campanas_cache:
                    new_camp = Campana(nombre=campana_val)
                    db.add(new_camp)
                    db.flush()
                    campanas_cache[campana_val] = new_camp.id
                campana_id = campanas_cache[campana_val]

                # B. Departamento
                depto_id = None
                if col_departamento and not pd.isna(row.get(col_departamento)):
                    depto_val = str(row.get(col_departamento)).upper().strip()
                    if depto_val != "":
                        if depto_val not in departamentos_cache:
                            new_depto = Departamento(nombre=depto_val)
                            db.add(new_depto)
                            db.flush()
                            departamentos_cache[depto_val] = new_depto.id
                        depto_id = departamentos_cache[depto_val]

                # C. Sección (depende del Departamento)
                seccion_id = None
                if col_seccion and depto_id and not pd.isna(row.get(col_seccion)):
                    seccion_val = str(row.get(col_seccion)).upper().strip()
                    if seccion_val != "":
                        cache_key = (depto_id, seccion_val)
                        if cache_key not in secciones_cache:
                            new_sec = Seccion(nombre=seccion_val, departamento_id=depto_id)
                            db.add(new_sec)
                            db.flush()
                            secciones_cache[cache_key] = new_sec.id
                        seccion_id = secciones_cache[cache_key]

                # D. Perfil de Riesgo
                perfil_id = None
                if col_perfil_riesgo and not pd.isna(row.get(col_perfil_riesgo)):
                    perfil_val = str(row.get(col_perfil_riesgo)).upper().strip()
                    if perfil_val != "":
                        if perfil_val not in perfiles_cache:
                            new_perfil = PerfilRiesgo(nombre=perfil_val)
                            db.add(new_perfil)
                            db.flush()
                            perfiles_cache[perfil_val] = new_perfil.id
                        perfil_id = perfiles_cache[perfil_val]

                # E. Segmento Rolling
                segmento_id = None
                if col_segmento_rolling and not pd.isna(row.get(col_segmento_rolling)):
                    segmento_val = str(row.get(col_segmento_rolling)).upper().strip()
                    if segmento_val != "":
                        if segmento_val not in segmentos_cache:
                            new_seg = SegmentoRolling(nombre=segmento_val)
                            db.add(new_seg)
                            db.flush()
                            segmentos_cache[segmento_val] = new_seg.id
                        segmento_id = segmentos_cache[segmento_val]

                # --- 3. GUARDAR / ACTUALIZAR CLIENTE ---
                cliente_nombre = str(row.get(col_nombre)).strip() if col_nombre and not pd.isna(row.get(col_nombre)) else ""
                doc_val = str(row.get(col_numero_documento)).strip() if col_numero_documento and not pd.isna(row.get(col_numero_documento)) else None
                correo_val = str(row.get(col_correo)).strip() if col_correo and not pd.isna(row.get(col_correo)) else None

                cliente = db.query(Cliente).filter(Cliente.codigo_cliente_belcor == cod_belcor).first()
                if not cliente:
                    if not cliente_nombre or cliente_nombre == "":
                        raise ValueError(f"Fila {index + 2}: El deudor con código '{cod_belcor}' no existe en el sistema y no se puede crear porque falta el Nombre completo en el archivo.")
                    cliente = Cliente(
                        codigo_cliente_belcor=cod_belcor,
                        nombre_completo=cliente_nombre,
                        numero_documento=doc_val,
                        correo_electronico=correo_val,
                        departamento_id=depto_id,
                        seccion_id=seccion_id,
                        perfil_riesgo_id=perfil_id,
                        segmento_rolling_id=segmento_id
                    )
                    db.add(cliente)
                    db.flush()  # Para obtener el cliente.id
                    clientes_nuevos += 1
                else:
                    # Actualización de datos personales con información fresca (sólo si viene en el Excel)
                    if cliente_nombre:
                        cliente.nombre_completo = cliente_nombre
                    if doc_val:
                        cliente.numero_documento = doc_val
                    if correo_val:
                        cliente.correo_electronico = correo_val
                    if depto_id:
                        cliente.departamento_id = depto_id
                    if seccion_id:
                        cliente.seccion_id = seccion_id
                    if perfil_id:
                        cliente.perfil_riesgo_id = perfil_id
                    if segmento_id:
                        cliente.segmento_rolling_id = segmento_id
                    clientes_actualizados += 1

                # --- 4. CARGA DE TELÉFONOS (INVENTARIO Y SELECCIÓN DE PRIORIDAD Y SUFIJOS NUMÉRICOS) ---
                candidatos_telefono: List[Tuple[str, str, float]] = []  # (numero, columna_excel, prioridad)

                for tel_cfg in telefonos_prioridad:
                    col_base = tel_cfg.nombre_columna_excel.strip()
                    col_base_esc = re.escape(col_base)
                    # Patrón: nombre base opcionalmente seguido de espacio y dígitos (ej. "Telefono Móvil 1" o "Telefono Móvil1")
                    pattern = re.compile(rf"^{col_base_esc}(?:\s*(\d+))?$", re.IGNORECASE)

                    # 1. Agrupar candidatos del Excel en esta fila para la columna base
                    candidatos_columna_fila = []
                    for col_excel in row.index:
                        col_excel_str = str(col_excel).strip()
                        match = pattern.match(col_excel_str)
                        if match:
                            val_tel = row.get(col_excel)
                            if not pd.isna(val_tel):
                                tel_limpio = str(val_tel).strip()
                                if tel_limpio != "":
                                    sufijo = match.group(1)
                                    sufijo_idx = int(sufijo) if sufijo else 0
                                    candidatos_columna_fila.append((tel_limpio, col_excel_str, sufijo_idx))

                    # 2. Ordenar candidatos del Excel de izquierda a derecha (por el número de columna)
                    candidatos_columna_fila.sort(key=lambda x: x[2])

                    # 3. Procesar cada teléfono en orden secuencial
                    for tel_limpio, col_excel_str, _ in candidatos_columna_fila:
                        cache_tel_key = (cliente.id, tel_limpio)
                        key_base = (cliente.id, col_base)
                        existing_prios = telefonos_por_cliente_tipo.get(key_base, [])

                        if cache_tel_key not in telefonos_existentes_cache:
                            # Teléfono nuevo: Calcular sufijo y prioridad de forma correlativa
                            sufijo_nuevo = len(existing_prios)
                            if sufijo_nuevo == 0:
                                tipo_registrado = col_base
                                prioridad_registrada = float(tel_cfg.prioridad)
                            else:
                                tipo_registrado = f"{col_base} {sufijo_nuevo}"
                                prioridad_registrada = float(tel_cfg.prioridad) + (sufijo_nuevo * 0.1)

                            # Añadir a la caché local
                            if key_base not in telefonos_por_cliente_tipo:
                                telefonos_por_cliente_tipo[key_base] = []
                            telefonos_por_cliente_tipo[key_base].append(prioridad_registrada)
                            telefonos_existentes_cache.add(cache_tel_key)
                            telefonos_db_prioridades[cache_tel_key] = prioridad_registrada
                            telefonos_db_tipos[cache_tel_key] = tipo_registrado

                            # Insertar nuevo teléfono
                            db_tel = TelefonoCliente(
                                cliente_id=cliente.id,
                                numero=tel_limpio,
                                tipo=tipo_registrado,
                                prioridad=prioridad_registrada,
                                estado="ACTIVO"
                            )
                            db.add(db_tel)
                            telefonos_nuevos += 1

                            candidatos_telefono.append((tel_limpio, tipo_registrado, prioridad_registrada))
                        else:
                            # Teléfono existente: Buscar su prioridad y tipo real en la base de datos
                            prio_db = telefonos_db_prioridades.get(cache_tel_key, float(tel_cfg.prioridad))
                            tipo_db = telefonos_db_tipos.get(cache_tel_key, col_base)
                            candidatos_telefono.append((tel_limpio, tipo_db, prio_db))

                # Clasificar teléfonos por prioridad y elegir el mejor para telefono_uso (marcado rápido)
                if candidatos_telefono:
                    # Ordenar por prioridad (menor número es mayor prioridad)
                    candidatos_telefono.sort(key=lambda x: x[2])
                    best_tel, best_col, _ = candidatos_telefono[0]
                    if cliente.telefono_uso != best_tel:
                        cliente.telefono_uso = best_tel
                        cliente.observacion_telefono = best_col
                        telefono_uso_actualizados += 1

                # --- 5. GESTIÓN DE CARGOS (DEUDAS) ---
                fecha_cierre_val = cls.parse_date(row.get(col_fecha_cierre)) if col_fecha_cierre else None
                fecha_pago_val = cls.parse_date(row.get(col_fecha_pago)) if col_fecha_pago else None
                dias_atraso_val = int(float(str(row.get(col_dias_atraso)).replace(" ", ""))) if col_dias_atraso and not pd.isna(row.get(col_dias_atraso)) and str(row.get(col_dias_atraso)).strip() != "" else 0
                observacion_val = str(row.get(col_observacion)).strip() if col_observacion and not pd.isna(row.get(col_observacion)) else None

                val_inicial_raw = cls.parse_number(row.get(col_monto_inicial)) if col_monto_inicial else 0.0
                val_interes_raw = cls.parse_number(row.get(col_interes)) if col_interes else 0.0
                val_gasto_raw = cls.parse_number(row.get(col_gasto_adm)) if col_gasto_adm else 0.0
                val_pago_raw = cls.parse_number(row.get(col_pago)) if col_pago else 0.0

                # Tipo de proceso actual de la plantilla
                proceso_tipo = str(plantilla.tipo_proceso).strip().upper()

                # Sumatorias estadísticas globales basadas en lo que procesamos
                if proceso_tipo != "BASE_SALDOS":
                    monto_deuda_inicial_total += val_inicial_raw
                    monto_interes_total += val_interes_raw
                    monto_gasto_adm_total += val_gasto_raw
                else:
                    monto_pagos_total += val_pago_raw

                # Buscar si el cargo ya existe para este deudor, tramo y campaña
                cargo = db.query(Cargo).filter(
                    Cargo.cliente_id == cliente.id,
                    Cargo.numero_cargo == num_cargo_val,
                    Cargo.tramo_id == tramo_id,
                    Cargo.campana_id == campana_id
                ).first()

                es_cargo_nuevo = False
                if not cargo:
                    es_cargo_nuevo = True
                    # Si el proceso no es de tipo Saldos, requerimos que venga el Monto Inicial para crear el cargo
                    if proceso_tipo != "BASE_SALDOS":
                        if not col_monto_inicial or pd.isna(row.get(col_monto_inicial)):
                            raise ValueError(f"Fila {index + 2}: El cargo '{num_cargo_val}' no existe en el sistema y no se puede crear porque falta el Monto Inicial en el archivo.")
                    
                    # Crear nuevo cargo base (los montos se calcularán vía triggers tras añadir movimientos)
                    cargo = Cargo(
                        cliente_id=cliente.id,
                        numero_cargo=num_cargo_val,
                        tramo_id=tramo_id,
                        campana_id=campana_id,
                        dias_atraso=dias_atraso_val,
                        fecha_cierre=fecha_cierre_val,
                        observacion=observacion_val,
                        estado="ACTIVO"
                    )
                    db.add(cargo)
                    db.flush()  # Para obtener cargo.id

                    # Registro de movimientos financieros según el tipo de proceso
                    if proceso_tipo != "BASE_SALDOS":
                        # Registrar movimientos financieros iniciales de arranque
                        mov_inicial = MovimientoCargo(
                            cargo_id=cargo.id,
                            tipo_movimiento="INICIAL",
                            monto=val_inicial_raw
                        )
                        db.add(mov_inicial)
                        movimientos_financieros_creados += 1

                        if val_interes_raw > 0:
                            mov_int = MovimientoCargo(
                                cargo_id=cargo.id,
                                tipo_movimiento="INTERES",
                                monto=val_interes_raw
                            )
                            db.add(mov_int)
                            movimientos_financieros_creados += 1

                        if val_gasto_raw > 0:
                            mov_g = MovimientoCargo(
                                cargo_id=cargo.id,
                                tipo_movimiento="GASTO_ADM",
                                monto=val_gasto_raw
                            )
                            db.add(mov_g)
                            movimientos_financieros_creados += 1
                    else:
                        # Si es de tipo Saldos, se crea la cuenta directamente con el pago recibido
                        if val_pago_raw > 0:
                            fecha_mov_dt = datetime.combine(fecha_pago_val, datetime.min.time()) if fecha_pago_val else func.now()
                            mov_p = MovimientoCargo(
                                cargo_id=cargo.id,
                                tipo_movimiento="PAGO",
                                monto=val_pago_raw,
                                fecha_movimiento=fecha_mov_dt
                            )
                            db.add(mov_p)
                            movimientos_financieros_creados += 1

                    cargos_nuevos += 1
                else:
                    # El cargo ya existe en esta campaña (actualización incremental o reasignación histórica)
                    cargo.dias_atraso = dias_atraso_val
                    cargo.fecha_cierre = fecha_cierre_val
                    if observacion_val:
                        cargo.observacion = observacion_val

                    # LÓGICA DE ACTUALIZACIÓN SEGÚN TIPO DE PROCESO
                    if proceso_tipo != "BASE_SALDOS":
                        # --- PROCESAMIENTO DE BASES INICIALES / ACTUALIZACIONES ---
                        is_activo = (cargo.estado == "ACTIVO")

                        # 1. Deuda Inicial (INICIAL)
                        # Regla: si NO está activo (retomando deudor histórico), ajustamos la deuda (puede ser positivo o negativo)
                        if not is_activo:
                            if val_inicial_raw != float(cargo.monto_inicial):
                                diff_inicial = val_inicial_raw - float(cargo.monto_inicial)
                                mov_inicial_diff = MovimientoCargo(
                                    cargo_id=cargo.id,
                                    tipo_movimiento="INICIAL",
                                    monto=diff_inicial
                                )
                                db.add(mov_inicial_diff)
                                movimientos_financieros_creados += 1

                        # 2. Intereses (INTERES)
                        if is_activo:
                            # Sólo aumentos permitidos en cuentas activas
                            if val_interes_raw > float(cargo.monto_interes):
                                diff_int = val_interes_raw - float(cargo.monto_interes)
                                mov_int_diff = MovimientoCargo(
                                    cargo_id=cargo.id,
                                    tipo_movimiento="INTERES",
                                    monto=diff_int
                                )
                                db.add(mov_int_diff)
                                movimientos_financieros_creados += 1
                        else:
                            # Aumentos o reducciones permitidas en deudores históricos
                            if val_interes_raw != float(cargo.monto_interes):
                                diff_int = val_interes_raw - float(cargo.monto_interes)
                                mov_int_diff = MovimientoCargo(
                                    cargo_id=cargo.id,
                                    tipo_movimiento="INTERES",
                                    monto=diff_int
                                )
                                db.add(mov_int_diff)
                                movimientos_financieros_creados += 1

                        # 3. Gastos Administrativos (GASTO_ADM)
                        if is_activo:
                            # Sólo aumentos permitidos en cuentas activas
                            if val_gasto_raw > float(cargo.monto_gasto_adm):
                                diff_g = val_gasto_raw - float(cargo.monto_gasto_adm)
                                mov_g_diff = MovimientoCargo(
                                    cargo_id=cargo.id,
                                    tipo_movimiento="GASTO_ADM",
                                    monto=diff_g
                                )
                                db.add(mov_g_diff)
                                movimientos_financieros_creados += 1
                        else:
                            # Aumentos o reducciones permitidas en deudores históricos
                            if val_gasto_raw != float(cargo.monto_gasto_adm):
                                diff_g = val_gasto_raw - float(cargo.monto_gasto_adm)
                                mov_g_diff = MovimientoCargo(
                                    cargo_id=cargo.id,
                                    tipo_movimiento="GASTO_ADM",
                                    monto=diff_g
                                )
                                db.add(mov_g_diff)
                                movimientos_financieros_creados += 1
                    else:
                        # --- PROCESAMIENTO DE SALDOS ---
                        # Solo procesamos pagos por diferencia. Ignoramos deudas, intereses y gastos por completo.
                        if val_pago_raw > float(cargo.monto_pagado):
                            diff_p = val_pago_raw - float(cargo.monto_pagado)
                            fecha_mov_dt = datetime.combine(fecha_pago_val, datetime.min.time()) if fecha_pago_val else func.now()
                            mov_p_diff = MovimientoCargo(
                                cargo_id=cargo.id,
                                tipo_movimiento="PAGO",
                                monto=diff_p,
                                fecha_movimiento=fecha_mov_dt
                            )
                            db.add(mov_p_diff)
                            movimientos_financieros_creados += 1
                            monto_pagos_total += diff_p

                    cargos_actualizados += 1

                # --- 6. DETERMINACIÓN DINÁMICA DEL ESTADO ---
                # Hacemos una pre-suma matemática en Python para actualizar el estado antes del commit
                # (PostgreSQL re-calculará todo físicamente en el commit real mediante triggers)
                
                # Montos preliminares según el tipo de proceso para el cálculo del estado
                if es_cargo_nuevo:
                    if proceso_tipo != "BASE_SALDOS":
                        pre_inicial = float(val_inicial_raw)
                        pre_interes = float(val_interes_raw)
                        pre_gasto = float(val_gasto_raw)
                        pre_monto_pagado = 0.0
                    else:
                        pre_inicial = 0.0
                        pre_interes = 0.0
                        pre_gasto = 0.0
                        pre_monto_pagado = float(val_pago_raw)
                else:
                    if proceso_tipo != "BASE_SALDOS":
                        # Si no es Saldos y no estaba activo, la deuda inicial se ajusta al valor del Excel
                        if cargo.estado != "ACTIVO":
                            pre_inicial = float(val_inicial_raw)
                            pre_interes = float(val_interes_raw)
                            pre_gasto = float(val_gasto_raw)
                        else:
                            pre_inicial = float(cargo.monto_inicial)
                            pre_interes = max(float(val_interes_raw), float(cargo.monto_interes))
                            pre_gasto = max(float(val_gasto_raw), float(cargo.monto_gasto_adm))
                        pre_monto_pagado = float(cargo.monto_pagado)
                    else:
                        pre_inicial = float(cargo.monto_inicial)
                        pre_interes = float(cargo.monto_interes)
                        pre_gasto = float(cargo.monto_gasto_adm)
                        pre_monto_pagado = max(float(val_pago_raw), float(cargo.monto_pagado))

                pre_total_deuda = pre_inicial + pre_interes + pre_gasto
                pre_saldo_cobrar = pre_total_deuda - pre_monto_pagado - float(cargo.monto_descontar if cargo.id else 0.0)

                if pre_saldo_cobrar <= 0:
                    cargo.estado = "PAGADO"
                elif fecha_cierre_val and hoy > fecha_cierre_val:
                    cargo.estado = "VENCIDO"
                else:
                    cargo.estado = "ACTIVO"  # Reactivación automática si la fecha es futura y tiene saldo

                # --- 7. BATCH FLUSH CADA 1000 REGISTROS ---
                if len(lote_actual) >= 1000:
                    db.flush()
                    lote_actual = []

            # Guardar el registro de auditoría de importación
            tiempo_total = time.time() - inicio_tiempo
            db_historial = HistorialImportacion(
                tramo_id=tramo_id,
                nombre_archivo=nombre_archivo,
                hash_archivo=hash_archivo,
                tipo_subida=plantilla.tipo_proceso,
                usuario_id=usuario_id,
                registros_procesados=len(file_df),
                clientes_nuevos=clientes_nuevos,
                clientes_actualizados=clientes_actualizados,
                cargos_nuevos=cargos_nuevos,
                cargos_actualizados=cargos_actualizados,
                telefonos_nuevos=telefonos_nuevos,
                telefono_uso_actualizados=telefono_uso_actualizados,
                movimientos_financieros_creados=movimientos_financieros_creados,
                monto_deuda_inicial_total=round(monto_deuda_inicial_total, 2),
                monto_interes_total=round(monto_interes_total, 2),
                monto_gasto_adm_total=round(monto_gasto_adm_total, 2),
                monto_pagos_total=round(monto_pagos_total, 2),
                duracion_segundos=round(tiempo_total, 2)
            )
            db.add(db_historial)
            db.flush()

            # Confirmar la transacción
            db.commit()

        except Exception as e:
            db.rollback()
            raise e

        tiempo_total = time.time() - inicio_tiempo
        return ImportSummaryResponse(
            clientes_nuevos=clientes_nuevos,
            clientes_actualizados=clientes_actualizados,
            cargos_nuevos=cargos_nuevos,
            cargos_actualizados=cargos_actualizados,
            telefonos_nuevos=telefonos_nuevos,
            telefono_uso_actualizados=telefono_uso_actualizados,
            movimientos_financieros_creados=movimientos_financieros_creados,
            monto_deuda_inicial_total=round(monto_deuda_inicial_total, 2),
            monto_interes_total=round(monto_interes_total, 2),
            monto_gasto_adm_total=round(monto_gasto_adm_total, 2),
            monto_pagos_total=round(monto_pagos_total, 2),
            total_filas_procesadas=len(file_df),
            duracion_segundos=round(tiempo_total, 2)
        )
