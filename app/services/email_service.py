import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    # CONFIGURACIÓN SMTP DE GMAIL
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_EMISOR = os.getenv("EMAIL_EMISOR")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") 
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200")

    @staticmethod
    def enviar_correo_recuperacion(email_destino: str, token: str):
        # Enlace real que apunta a tu pantalla de Angular
        enlace_url = f"{EmailService.FRONTEND_URL}/recuperar-password?token={token}"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Restablecer Contraseña - Portal Zyra BPO"
        msg['From'] = f"Zyra BPO Seguridad <{EmailService.EMAIL_EMISOR}>"
        msg['To'] = email_destino

        # Plantilla ejecutiva y limpia en HTML para el correo que verá el operador
        html = f"""
        <html>
          <body style="font-family: sans-serif; color: #0f172a; background-color: #f8fafc; padding: 40px 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; padding: 32px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);">
              <div style="text-align: center; margin-bottom: 24px;">
                <span style="background: #0f172a; color: #ffffff; padding: 10px 20px; font-weight: 900; border-radius: 8px; font-size: 20px;">Z</span>
                <h2 style="margin-top: 16px; font-size: 22px; font-weight: 800;">Portal de Seguridad Zyra BPO</h2>
              </div>
              <p style="font-size: 15px; color: #334155;">Hola,</p>
              <p style="font-size: 15px; color: #334155;">Hemos recibido una solicitud para restablecer la contraseña de tu cuenta institucional.</p>
              <p style="font-size: 15px; color: #334155;">Para continuar con el proceso, haz clic en el siguiente botón seguro. Recuerda que este enlace expira en <b>15 minutos</b>.</p>
              
              <div style="text-align: center; margin: 32px 0;">
                <a href="{enlace_url}" style="background-color: #0f172a; color: #ffffff; padding: 14px 28px; font-weight: bold; text-decoration: none; border-radius: 10px; font-size: 15px; display: inline-block;">Restablecer Contraseña</a>
              </div>
              
              <p style="font-size: 13px; color: #64748b;">Si tú no solicitaste este cambio, puedes ignorar este correo de forma segura. Tu contraseña actual no sufrirá modificaciones.</p>
              <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;">
              <p style="font-size: 11px; text-align: center; color: #94a3b8;">Este es un correo automático, por favor no lo respondas.</p>
            </div>
          </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        try:
            # Conexión segura e inicio de sesión en los servidores de Google
            server = smtplib.SMTP(EmailService.SMTP_SERVER, EmailService.SMTP_PORT)
            server.starttls() # Cifrado TLS obligado por Google
            server.login(EmailService.EMAIL_EMISOR, EmailService.EMAIL_PASSWORD)
            server.sendmail(EmailService.EMAIL_EMISOR, email_destino, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            print(f"ERROR CRÍTICO SMTP EN EMAIL_SERVICE: {e}")
            return False