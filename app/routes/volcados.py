from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Optional
from app.core.dependencies import verificar_permiso
from app.services.volcados.motor_tramos import MotorVolcadoTramos
from app.services.volcados.motor_ivr import MotorVolcadoIVR
import os

router = APIRouter(prefix="/volcados", tags=["Motor de Volcados"])

def get_extension(filename: str) -> str:
    if not filename:
        return ""
    return os.path.splitext(filename)[1].replace(".", "").lower()

@router.post("/generar/tramos")
async def generar_volcado_tramos(
    base_file: UploadFile = File(...),
    discador_file: Optional[UploadFile] = File(None),
    crm_file: Optional[UploadFile] = File(None),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="volcados", nivel_requerido=2))
):
    """
    Recibe los archivos necesarios para Tramos, ejecuta el proceso en memoria y devuelve el Excel.
    """
    if not discador_file and not crm_file:
        raise HTTPException(status_code=400, detail="Debe subir al menos el archivo Discador o el CRM.")
        
    try:
        base_bytes = await base_file.read()
        base_ext = get_extension(base_file.filename)
        
        discador_bytes = None
        discador_ext = ""
        if discador_file:
            discador_bytes = await discador_file.read()
            discador_ext = get_extension(discador_file.filename)
            
        crm_bytes = None
        crm_ext = ""
        if crm_file:
            crm_bytes = await crm_file.read()
            crm_ext = get_extension(crm_file.filename)

        motor = MotorVolcadoTramos()
        output_buffer = motor.ejecutar(
            base_bytes=base_bytes, base_ext=base_ext,
            discador_bytes=discador_bytes, discador_ext=discador_ext,
            crm_bytes=crm_bytes, crm_ext=crm_ext
        )
        
        headers = {
            'Content-Disposition': 'attachment; filename="Volcado_Final_Tramos.xlsx"'
        }
        return StreamingResponse(output_buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno procesando el volcado: {str(e)}")

@router.post("/generar/ivr")
async def generar_volcado_ivr(
    base_file: UploadFile = File(...),
    discador_file: UploadFile = File(...),
    _usuario_valido = Depends(verificar_permiso(modulo_interno="volcados", nivel_requerido=2))
):
    """
    Recibe los archivos necesarios para IVR, ejecuta el proceso en memoria y devuelve el Excel.
    """
    try:
        base_bytes = await base_file.read()
        base_ext = get_extension(base_file.filename)
        
        discador_bytes = await discador_file.read()
        discador_ext = get_extension(discador_file.filename)

        motor = MotorVolcadoIVR()
        output_buffer = motor.ejecutar(
            base_bytes=base_bytes, base_ext=base_ext,
            discador_bytes=discador_bytes, discador_ext=discador_ext
        )
        
        headers = {
            'Content-Disposition': 'attachment; filename="Volcado_Final_IVR.xlsx"'
        }
        return StreamingResponse(output_buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno procesando el volcado: {str(e)}")
