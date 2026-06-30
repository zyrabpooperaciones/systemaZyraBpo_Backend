import pandas as pd
import numpy as np
import io

class MotorVolcadoIVR:
    """
    Motor centralizado para procesar los volcados de IVR.
    Unifica las funcionalidades de unificar_reporteIVR.py y generar_volcadoIVR.py.
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

    # =========================================================================
    # FASE 1: UNIFICACIÓN IVR
    # =========================================================================

    def normalizar_columnas(self, df_discador: pd.DataFrame) -> pd.DataFrame:
        column_mapping = {
            "NÃºmero": "Numero",
            "Número": "Numero",
            "RelaciÃ³n": "Relacion",
            "Relación": "Relacion",
            "AtendiÃ³": "Atendio",
            "Atendió": "Atendio",
        }
        df_discador = df_discador.rename(columns=column_mapping)

        if "paraCRM" in df_discador.columns:
            df_discador = df_discador[
                df_discador["paraCRM"].notna() &
                (df_discador["paraCRM"].astype(str).str.strip() != "") &
                (df_discador["paraCRM"].astype(str).str.strip().str.lower() != "nan")
            ]
        return df_discador

    def extraer_datos_base(self, df_discador: pd.DataFrame) -> pd.DataFrame:
        df_limpio = pd.DataFrame()
        df_limpio["Fecha / Hora"] = df_discador["Fecha / Hora"] if "Fecha / Hora" in df_discador.columns else np.nan
        df_limpio["Numero"] = df_discador["Numero"] if "Numero" in df_discador.columns else np.nan
        df_limpio["Atendio"] = df_discador["Atendio"] if "Atendio" in df_discador.columns else np.nan

        if "paraCRM" in df_discador.columns:
            df_limpio["Data"] = df_discador["paraCRM"].astype(str).str.split("###").str[0].str.strip()
            df_limpio["Relacion"] = df_discador["paraCRM"].astype(str).str.split("###").str[1].str.strip()
        else:
            df_limpio["Data"] = np.nan
            df_limpio["Relacion"] = np.nan
            
        return df_limpio

    def clasificar_niveles(self, df_limpio: pd.DataFrame, df_discador: pd.DataFrame) -> pd.DataFrame:
        atendio = df_discador["Atendio"].astype(str).str.strip().str.upper() if "Atendio" in df_discador.columns else pd.Series([""] * len(df_limpio))

        condiciones = [
            (atendio.isna()) | (atendio == "NAN") | (atendio == ""),
            atendio.isin(["CONTESTADOR", "DESCONOCIDO"]),
            atendio.isin(["HUMANO", "CORTO"]),
        ]

        n1_opciones = ["No contacto", "No contacto", "Contacto efectivo"]
        n2_opciones = [
            "No contacto manana / tarde",
            "No contacto manana / tarde",
            "Renuente",
        ]
        n3_opciones = [
            "No contesta / Mensaje en grabadora",
            "No contesta / Mensaje en grabadora",
            "Consultora renuente",
        ]
        n4_opciones = [
            "No contesta / Mensaje en grabadora",
            "No contesta / Mensaje en grabadora",
            "Cuelga la llamada",
        ]

        df_limpio["nivel1"] = np.select(condiciones, n1_opciones, default="No contacto")
        df_limpio["nivel2"] = np.select(condiciones, n2_opciones, default="No contacto manana / tarde")
        df_limpio["nivel3"] = np.select(condiciones, n3_opciones, default="No contesta / Mensaje en grabadora")
        df_limpio["nivel4"] = np.select(condiciones, n4_opciones, default="No contesta / Mensaje en grabadora")

        return df_limpio

    def cruzar_con_base(self, df_limpio: pd.DataFrame, df_base: pd.DataFrame) -> pd.DataFrame:
        if df_base.empty or "Codigo Cliente" not in df_base.columns or "Campana" not in df_base.columns:
            df_limpio["campana"] = np.nan
            return df_limpio

        df_limpio["Data_aux"] = df_limpio["Data"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        df_base["Data_aux"] = df_base["Codigo Cliente"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

        df_base_campana = df_base[["Data_aux", "Campana"]].drop_duplicates(subset=["Data_aux"])

        df_limpio = pd.merge(df_limpio, df_base_campana, on="Data_aux", how="left")
        df_limpio = df_limpio.rename(columns={"Campana": "campana"})
        df_limpio = df_limpio.drop(columns=["Data_aux"])

        return df_limpio

    # =========================================================================
    # FASE 2: GENERACIÓN FINAL (ESTRUCTURA CORPORATIVA)
    # =========================================================================

    def construir_volcado(self, df_limpio: pd.DataFrame) -> pd.DataFrame:
        df_volcado = pd.DataFrame()

        df_volcado["Etapa deuda"] = df_limpio.get("Relacion", df_limpio.get("RelaciÃ³n", np.nan))
        df_volcado["Codigo Cobrador"] = "BOZYRA"
        df_volcado["Campana"] = df_limpio.get("campana", np.nan)

        if "Data" in df_limpio.columns:
            codigos = df_limpio["Data"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
            df_volcado["Codigo"] = codigos.apply(lambda x: x.zfill(7) if x not in ["nan", "None", ""] else np.nan)
        else:
            df_volcado["Codigo"] = np.nan

        fechas_dt = pd.to_datetime(df_limpio.get("Fecha / Hora", pd.Series()), format='mixed', dayfirst=True, errors="coerce")

        if "Fecha / Hora" in df_limpio.columns:
            df_volcado["Fecha gestion"] = fechas_dt.dt.strftime("%d/%m/%Y").fillna(
                df_limpio["Fecha / Hora"].astype(str).str.split().str[0]
            ).replace("nan", np.nan)
            
            df_volcado["Hora gestion"] = fechas_dt.dt.strftime("%H:%M:%S").fillna(
                df_limpio["Fecha / Hora"].astype(str).str.split().str[1] if df_limpio["Fecha / Hora"].astype(str).str.split().apply(len).max() > 1 else np.nan
            ).replace("nan", np.nan)
        else:
            df_volcado["Fecha gestion"] = np.nan
            df_volcado["Hora gestion"] = np.nan

        df_volcado["Nivel 1"] = df_limpio.get("nivel1", np.nan)
        df_volcado["Nivel 2"] = df_limpio.get("nivel2", np.nan)
        df_volcado["Nivel 3"] = df_limpio.get("nivel3", np.nan)
        df_volcado["Nivel 4"] = df_limpio.get("nivel4", np.nan)
        
        df_volcado["Fecha Promesa Pago"] = np.nan
        df_volcado["Monto Promesa Pago"] = np.nan

        df_volcado["Telefono"] = df_limpio.get("Numero", df_limpio.get("NÃºmero", np.nan))
        df_volcado["Canalidad"] = "IVR"
        
        if "Atendio" in df_limpio.columns:
            atendio_limpio = df_limpio["Atendio"].astype(str).str.strip().str.upper()
            df_volcado["Observacion"] = np.where(
                atendio_limpio == "HUMANO",
                "Notificado por BOT",
                None
            )
        else:
            df_volcado["Observacion"] = np.nan

        # Reemplazar NaN visualmente
        df_volcado = df_volcado.replace(["nan", "NaT", "NaN"], "").fillna("")

        return df_volcado

    # =========================================================================
    # MÉTODO ORQUESTADOR
    # =========================================================================

    def ejecutar(self, base_bytes: bytes, base_ext: str, discador_bytes: bytes, discador_ext: str) -> io.BytesIO:
        """
        Ejecuta todo el proceso en memoria y devuelve un buffer con el Excel final.
        """
        if not discador_bytes:
            raise ValueError("El archivo Discador IVR es obligatorio.")
        if not base_bytes:
            raise ValueError("El archivo Base Completa es obligatorio.")

        # 1. Cargar DataFrames
        df_discador = self._leer_archivo(discador_bytes, discador_ext)
        if df_discador.empty:
            raise ValueError("El archivo Discador IVR parece estar vacío.")
            
        df_base = self._leer_archivo(base_bytes, base_ext)
        
        # 2. Unificación
        df_discador = self.normalizar_columnas(df_discador)
        df_limpio = self.extraer_datos_base(df_discador)
        df_limpio = self.clasificar_niveles(df_limpio, df_discador)
        df_limpio = self.cruzar_con_base(df_limpio, df_base)

        # 3. Generación corporativa
        volcado_final = self.construir_volcado(df_limpio)

        # 4. Exportar a BytesIO
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            volcado_final.to_excel(writer, index=False)
        
        output.seek(0)
        return output
