import pandas as pd
import numpy as np
import io
from typing import Tuple, Optional

class MotorVolcadoTramos:
    """
    Motor centralizado para procesar los volcados de Tramos telefónicos.
    Unifica las funcionalidades de unificar_reportes.py y generar_volcado.py.
    """

    @staticmethod
    def _leer_archivo(contenido_bytes: bytes, extension: str) -> pd.DataFrame:
        if not contenido_bytes:
            return pd.DataFrame()
        
        buffer = io.BytesIO(contenido_bytes)
        extension = extension.lower()
        
        try:
            if extension == 'csv':
                return pd.read_csv(buffer, encoding="utf-8-sig")
            else:
                return pd.read_excel(buffer)
        except Exception as e:
            # Fallback en caso de que la extensión mienta
            buffer.seek(0)
            try:
                if extension == 'csv':
                    return pd.read_excel(buffer)
                else:
                    return pd.read_csv(buffer, encoding="utf-8-sig")
            except:
                raise ValueError(f"No se pudo leer el archivo. Asegúrese de que sea un Excel o CSV válido. Detalle: {str(e)}")

    @staticmethod
    def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
        def limpiar(col):
            if not isinstance(col, str):
                return col
            try:
                return col.encode('latin1').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                return col
        df.columns = [limpiar(c) for c in df.columns]
        return df

    @staticmethod
    def limpiar_codigo(serie: pd.Series) -> pd.Series:
        return (
            serie.astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.strip()
            .replace(["nan", "NaN", "None", "nat", "NaT"], "")
            .fillna("")
        )

    # =========================================================================
    # FASE 1: UNIFICACIÓN
    # =========================================================================
    
    def limpiar_datos(self, df_discador: pd.DataFrame, df_crm: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        if not df_discador.empty:
            if "paraCRM" in df_discador.columns:
                partes = df_discador["paraCRM"].astype(str).str.split("###", n=1, expand=True)
                df_discador["Data"] = self.limpiar_codigo(partes[0])
                if partes.shape[1] > 1:
                    df_discador["Entidad"] = partes[1].str.strip()
                else:
                    df_discador["Entidad"] = ""
            elif "Data" in df_discador.columns:
                df_discador["Data"] = self.limpiar_codigo(df_discador["Data"])
            df_discador = df_discador.drop_duplicates()

        if not df_crm.empty:
            if "Data" in df_crm.columns:
                df_crm["Data"] = self.limpiar_codigo(df_crm["Data"])
            df_crm = df_crm.drop_duplicates()

        return df_discador, df_crm

    def cruzar_datos(self, df_discador: pd.DataFrame, df_crm: pd.DataFrame) -> pd.DataFrame:
        if df_discador.empty:
            if "Fecha / Hora" in df_crm.columns:
                df_crm["_fecha_calculo"] = pd.to_datetime(df_crm["Fecha / Hora"], errors="coerce", format="mixed")
            if "Data" in df_crm.columns:
                df_crm["Data"] = df_crm["Data"].astype(object)
            return df_crm.rename(columns={"Fecha / Hora": "Fecha / Hora_CRM_TEMP", "Data": "Data_CRM_TEMP"})

        if df_crm.empty:
            if "Fecha / Hora" in df_discador.columns:
                df_discador["_fecha_calculo"] = pd.to_datetime(df_discador["Fecha / Hora"], errors="coerce", format="mixed")
            if "Data" in df_discador.columns:
                df_discador["Data"] = df_discador["Data"].astype(object)
            return df_discador.copy()

        df_discador["_fecha_calculo"] = pd.to_datetime(df_discador["Fecha / Hora"], errors="coerce", format="mixed")
        df_crm["_fecha_calculo"] = pd.to_datetime(df_crm["Fecha / Hora"], errors="coerce", format="mixed")

        df_discador["Data"] = df_discador["Data"].astype(object)
        df_crm["Data"] = df_crm["Data"].astype(object)

        df_discador_valid = df_discador.dropna(subset=["_fecha_calculo"]).copy()
        df_discador_invalid = df_discador[df_discador["_fecha_calculo"].isna()].copy()

        df_crm_valid = df_crm.dropna(subset=["_fecha_calculo"]).copy()
        df_crm_invalid = df_crm[df_crm["_fecha_calculo"].isna()].copy()

        df_crm_valid["_id_crm_temp"] = range(len(df_crm_valid))

        df_discador_valid = df_discador_valid.sort_values("_fecha_calculo")
        df_crm_valid = df_crm_valid.sort_values("_fecha_calculo")

        if not df_discador_valid.empty and not df_crm_valid.empty:
            df_unido = pd.merge_asof(
                df_discador_valid,
                df_crm_valid,
                on="_fecha_calculo",
                by="Data",
                direction="nearest",
                tolerance=pd.Timedelta("30 minutes"),
                suffixes=("", "_CRM_TEMP"),
            )
            ids_crm_usados = df_unido["_id_crm_temp"].dropna().unique()
            df_crm_sobrantes = df_crm_valid[~df_crm_valid["_id_crm_temp"].isin(ids_crm_usados)].copy()
        else:
            df_unido = df_discador_valid
            df_crm_sobrantes = df_crm_valid

        df_crm_sobrantes = df_crm_sobrantes.rename(columns={"Fecha / Hora": "Fecha / Hora_CRM_TEMP", "Data": "Data_CRM_TEMP"})
        df_crm_invalid = df_crm_invalid.rename(columns={"Fecha / Hora": "Fecha / Hora_CRM_TEMP", "Data": "Data_CRM_TEMP"})

        return pd.concat([df_unido, df_crm_sobrantes, df_discador_invalid, df_crm_invalid], ignore_index=True)

    def desconcatenar_niveles(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Nivel 1"] = ""
        df["Nivel 2"] = ""
        df["Nivel 3"] = ""
        df["Nivel 4"] = ""

        if "Tipificación 1" in df.columns:
            t1_series = df["Tipificación 1"].astype(str).str.strip()
            partes_t1 = t1_series.str.split("-", n=1)
            df["Nivel 1"] = partes_t1.str[0].fillna("").str.strip()
            df["Nivel 2"] = partes_t1.str[1].fillna("").str.strip()

        if "Tipificación 2" in df.columns:
            df["Tipificación 2"] = df["Tipificación 2"].astype(str).str.strip()

            excepcion_1 = "No contesta - Mensaje en grabadora - No Contesta BOT-Buzon"
            excepcion_2 = "No contesta - Mensaje en grabadora - No Contesta BOT-No contesta"
            excepcion_3 = "No contesta - Mensaje en grabadora - No contesta - Mensaje en grabadora"

            for i in df.index:
                valor_original = df.at[i, "Tipificación 2"]
                if valor_original in [excepcion_1, excepcion_2, excepcion_3]:
                    df.at[i, "Nivel 3"] = "No contesta - Mensaje en grabadora"
                    if valor_original == excepcion_1:
                        df.at[i, "Nivel 4"] = "No Contesta BOT-Buzon"
                    elif valor_original == excepcion_2:
                        df.at[i, "Nivel 4"] = "No Contesta BOT-No contesta"
                    elif valor_original == excepcion_3:
                        df.at[i, "Nivel 4"] = "No contesta - Mensaje en grabadora"
                else:
                    if "-" in valor_original:
                        partes = valor_original.split("-", 1)
                        df.at[i, "Nivel 3"] = partes[0].strip()
                        df.at[i, "Nivel 4"] = partes[1].strip()
                    else:
                        df.at[i, "Nivel 3"] = valor_original
                        df.at[i, "Nivel 4"] = ""

        if "Nivel 4" in df.columns:
            df["Nivel 4"] = df["Nivel 4"].str.replace(
                "Contesta BOT-Corta llamada-No se entrega i",
                "Contesta BOT-Corta llamada-No se entrega informacion de deuda",
                regex=False,
            )

        return df

    def aplicar_logica_negocio(self, df_resultado: pd.DataFrame, df_base: Optional[pd.DataFrame]) -> pd.DataFrame:
        columnas_esperadas = [
            "Data", "Data_CRM_TEMP", "Número", "Teléfono 1", "Fecha / Hora",
            "Fecha / Hora_CRM_TEMP", "Fecha Agenda", "Tipificación 1",
            "Tipificación 2", "Atendió", "Entidad", "campania", "Comentario"
        ]
        for col in columnas_esperadas:
            if col not in df_resultado.columns:
                df_resultado[col] = np.nan
                df_resultado[col] = df_resultado[col].astype(object)

        df_resultado["Data"] = df_resultado["Data"].fillna(df_resultado["Data_CRM_TEMP"])
        df_resultado["Data"] = self.limpiar_codigo(df_resultado["Data"])
        df_resultado["Teléfono"] = df_resultado["Número"].fillna(df_resultado["Teléfono 1"])

        if "Fecha / Hora_CRM_TEMP" in df_resultado.columns:
            df_resultado["_fecha_final_dt"] = pd.to_datetime(
                df_resultado["Fecha / Hora"], errors="coerce", format="mixed"
            ).fillna(pd.to_datetime(df_resultado["Fecha / Hora_CRM_TEMP"], errors="coerce", format="mixed"))
        else:
            df_resultado["_fecha_final_dt"] = pd.to_datetime(df_resultado["Fecha / Hora"], errors="coerce", format="mixed")

        df_resultado["_fecha_agenda_dt"] = pd.to_datetime(df_resultado["Fecha Agenda"], errors="coerce", format="mixed")

        if "Tipificación 2" in df_resultado.columns and "Tipificación 1" in df_resultado.columns:
            df_resultado["Tipificación 2_limpia"] = df_resultado["Tipificación 2"].astype(str).str.strip().str.lower()
            mismo_dia = df_resultado["_fecha_final_dt"].dt.date == df_resultado["_fecha_agenda_dt"].dt.date
            es_rellamar = df_resultado["Tipificación 2_limpia"] == "rellamar"

            df_resultado.loc[es_rellamar & mismo_dia, "Tipificación 1"] = "Contacto efectivo - Promesa de pago"
            df_resultado.loc[es_rellamar & mismo_dia, "Tipificación 2"] = "Promesa parcial - Promesa parcial"
            df_resultado.loc[es_rellamar & ~mismo_dia, "Tipificación 1"] = "Contacto efectivo - Recordar promesa"
            df_resultado.loc[es_rellamar & ~mismo_dia, "Tipificación 2"] = "Recordar promesa parcial - Recordar promesa parcial"
            df_resultado = df_resultado.drop(columns=["Tipificación 2_limpia"])

        df_resultado["_atendio_limpio"] = df_resultado["Atendió"].astype(str).str.strip().str.upper()
        es_vacio_t1 = df_resultado["Tipificación 1"].isna()
        es_vacio_t2 = df_resultado["Tipificación 2"].isna()
        es_corto = df_resultado["_atendio_limpio"] == "CORTO"

        df_resultado.loc[es_vacio_t1 & es_corto, "Tipificación 1"] = "Contacto efectivo - Renuente"
        df_resultado.loc[es_vacio_t2 & es_corto, "Tipificación 2"] = "Consultora renuente - Contesta BOT-Si-Corta la llamada"

        df_resultado["Tipificación 1"] = df_resultado["Tipificación 1"].fillna("No contacto - No contacto manana - tarde")
        df_resultado["Tipificación 2"] = df_resultado["Tipificación 2"].fillna("No contesta - Mensaje en grabadora - No contesta - Mensaje en grabadora")
        df_resultado = df_resultado.drop(columns=["_atendio_limpio"])

        if "Entidad" in df_resultado.columns:
            valor_entidad = df_resultado["Entidad"].dropna().first_valid_index()
            if valor_entidad is not None:
                nombre_entidad = df_resultado.loc[valor_entidad, "Entidad"]
                df_resultado["Entidad"] = df_resultado["Entidad"].fillna(nombre_entidad)

        if df_base is not None and not df_base.empty and "Codigo Cliente" in df_base.columns and "Campana" in df_base.columns:
            df_base_limpio = df_base.drop_duplicates(subset=["Codigo Cliente"]).dropna(subset=["Codigo Cliente"])
            base_codigos = self.limpiar_codigo(df_base_limpio["Codigo Cliente"])
            mapeo_campanas = dict(zip(base_codigos, df_base_limpio["Campana"]))

            df_resultado["campania_limpia"] = df_resultado["campania"].astype(str).str.strip()
            es_vacio_campania = df_resultado["campania"].isna() | (df_resultado["campania_limpia"] == "") | (df_resultado["campania_limpia"] == "nan")
            codigos_buscar = self.limpiar_codigo(df_resultado.loc[es_vacio_campania, "Data"])
            campanas_encontradas = codigos_buscar.map(mapeo_campanas)

            df_resultado.loc[es_vacio_campania, "campania"] = campanas_encontradas
            df_resultado = df_resultado.drop(columns=["campania_limpia"])

        df_resultado = self.desconcatenar_niveles(df_resultado)

        df_resultado["Fecha / Hora_Formateada"] = df_resultado["_fecha_final_dt"].dt.strftime("%d/%m/%Y %H:%M:%S").fillna("")
        df_resultado["Fecha Agenda_Formateada"] = df_resultado["_fecha_agenda_dt"].dt.strftime("%d/%m/%Y %H:%M:%S").fillna("")
        df_resultado["Fecha Agenda"] = df_resultado["Fecha Agenda_Formateada"]
        df_resultado["Atendió"] = df_resultado["Atendió"].fillna("")

        columnas_a_guardar = [
            "Data", "Teléfono", "Fecha / Hora_Formateada", "Entidad", "campania",
            "Comentario", "Atendió", "Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4", "Fecha Agenda",
        ]
        df_final = df_resultado[columnas_a_guardar].copy()
        df_final = df_final.rename(columns={"Fecha / Hora_Formateada": "Fecha / Hora"})

        return df_final

    # =========================================================================
    # FASE 2: GENERACIÓN FINAL (ESTRUCTURA CORPORATIVA)
    # =========================================================================

    def construir_volcado(self, df_limpio: pd.DataFrame) -> pd.DataFrame:
        df_volcado = pd.DataFrame()

        df_volcado["Etapa deuda"] = df_limpio["Entidad"] if "Entidad" in df_limpio.columns else ""
        df_volcado["Codigo Cobrador"] = "BOZYRA"
        df_volcado["Campana"] = df_limpio["campania"] if "campania" in df_limpio.columns else ""

        if "Data" in df_limpio.columns:
            codigos = df_limpio["Data"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
            df_volcado["Codigo"] = codigos.apply(lambda x: x.zfill(7) if x and x.lower() not in ["nan", "none"] else "")
        else:
            df_volcado["Codigo"] = ""

        if "Fecha / Hora" in df_limpio.columns:
            fecha_hora = df_limpio["Fecha / Hora"].astype(str).str.strip()
            partes = fecha_hora.str.split(" ", n=1, expand=True)
            df_volcado["Fecha gestion"] = partes[0].replace(["nan", "NaN", "None"], "").fillna("")
            if partes.shape[1] > 1:
                df_volcado["Hora gestion"] = partes[1].replace(["nan", "NaN", "None"], "").fillna("")
            else:
                df_volcado["Hora gestion"] = ""
        else:
            df_volcado["Fecha gestion"] = ""
            df_volcado["Hora gestion"] = ""

        df_volcado["Nivel 1"] = df_limpio["Nivel 1"] if "Nivel 1" in df_limpio.columns else ""
        df_volcado["Nivel 2"] = df_limpio["Nivel 2"] if "Nivel 2" in df_limpio.columns else ""
        df_volcado["Nivel 3"] = df_limpio["Nivel 3"] if "Nivel 3" in df_limpio.columns else ""
        df_volcado["Nivel 4"] = df_limpio["Nivel 4"] if "Nivel 4" in df_limpio.columns else ""

        df_volcado["Fecha Promesa Pago"] = df_limpio["Fecha Agenda"] if "Fecha Agenda" in df_limpio.columns else ""
        df_volcado["Monto Promesa Pago"] = ""
        df_volcado["Telefono"] = df_limpio["Teléfono"] if "Teléfono" in df_limpio.columns else ""
        df_volcado["Canalidad"] = "Telefonica"
        df_volcado["Observacion"] = df_limpio["Comentario"] if "Comentario" in df_limpio.columns else ""

        df_volcado["Fecha Promesa Pago"] = pd.to_datetime(
            df_volcado["Fecha Promesa Pago"], dayfirst=True, errors="coerce"
        ).dt.strftime("%d/%m/%Y")

        df_volcado = df_volcado.replace(["nan", "NaT", "NaN"], "").fillna("")

        return df_volcado

    # =========================================================================
    # MÉTODO ORQUESTADOR
    # =========================================================================

    def ejecutar(
        self,
        base_bytes: bytes, base_ext: str,
        discador_bytes: Optional[bytes] = None, discador_ext: str = "",
        crm_bytes: Optional[bytes] = None, crm_ext: str = ""
    ) -> io.BytesIO:
        """
        Ejecuta todo el proceso en memoria y devuelve un buffer con el Excel final.
        """
        if not discador_bytes and not crm_bytes:
            raise ValueError("Se requiere al menos el archivo Discador o el CRM.")
        if not base_bytes:
            raise ValueError("El archivo Base Completa es obligatorio.")

        # 1. Cargar DataFrames
        df_base = self._leer_archivo(base_bytes, base_ext)
        if not df_base.empty:
            df_base = self.normalizar_columnas(df_base)

        df_discador = self._leer_archivo(discador_bytes, discador_ext) if discador_bytes else pd.DataFrame()
        if not df_discador.empty:
            df_discador = self.normalizar_columnas(df_discador)

        df_crm = self._leer_archivo(crm_bytes, crm_ext) if crm_bytes else pd.DataFrame()
        if not df_crm.empty:
            df_crm = self.normalizar_columnas(df_crm)

        # 2. Unificación
        discador_clean, crm_clean = self.limpiar_datos(df_discador, df_crm)
        reporte_sucio = self.cruzar_datos(discador_clean, crm_clean)
        reporte_unificado = self.aplicar_logica_negocio(reporte_sucio, df_base)

        # 3. Generación corporativa
        volcado_final = self.construir_volcado(reporte_unificado)

        # 4. Exportar a BytesIO
        output = io.BytesIO()
        # Usar engine openpyxl explícitamente para asegurar compatibilidad en memoria
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            volcado_final.to_excel(writer, index=False)
        
        output.seek(0)
        return output
