from email.message import EmailMessage

import aiosmtplib

from app.config import settings


async def send_email(
    to_email: str,
    subject: str,
    plain_text: str,
    html_content: str | None = None,
) -> None:

    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to_email
    message["Subject"] = subject

    message.set_content(plain_text)

    if html_content:
        message.add_alternative(html_content, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.mail_server,
        port=settings.mail_port,
        username=settings.mail_username
        if settings.mail_username
        else None,
        password=settings.mail_password.get_secret_value() or None,
        start_tls=settings.mail_use_tls,
    )


async def send_password_reset_otp_email(
    to_email: str, username: str, otp: str
) -> None:
    plain_text = f"""Hi {username},

You requested to reset your SharafAI password.

Your reset code is:

{otp}

This code expires in 10 minutes. If you did not request this, ignore this email.

Best regards,
The SharafAI Team
"""

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your SharafAI Password</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #334155;">
  <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8fafc; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 500px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); border: 1px solid #e2e8f0; overflow: hidden;">
          <tr>
            <td style="background-color: #4f46e5; height: 6px; line-height: 6px; font-size: 1px;">&nbsp;</td>
          </tr>
          <tr>
            <td style="padding: 40px 32px;">
              <h1 style="margin: 0 0 16px 0; font-size: 22px; font-weight: 700; color: #1e293b; line-height: 28px;">Password Reset Request</h1>
              <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 24px; color: #475569;">Hi {username},</p>
              <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 24px; color: #475569;">You requested to reset your <strong>SharafAI</strong> password. Use the verification code below to complete the process:</p>
              
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="margin: 28px 0;">
                <tr>
                  <td align="center" style="background-color: #f1f5f9; border-radius: 8px; padding: 18px; border: 1px dashed #cbd5e1;">
                    <span style="font-family: 'Courier New', Courier, monospace; font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #1e293b; display: inline-block; padding-left: 6px;">{otp}</span>
                  </td>
                </tr>
              </table>

              <p style="margin: 0 0 24px 0; font-size: 14px; line-height: 20px; color: #64748b;">This code expires in <strong style="color: #0f172a;">10 minutes</strong>. If you did not request this, you can safely ignore this email; your account remains secure.</p>
              
              <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 32px 0 24px 0;">
              
              <p style="margin: 0 0 4px 0; font-size: 15px; line-height: 22px; color: #475569;">Best regards,</p>
              <p style="margin: 0; font-size: 15px; line-height: 22px; font-weight: 600; color: #1e293b;">The SharafAI Team</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    await send_email(
        to_email=to_email,
        subject="Reset Your SharafAI Password",
        plain_text=plain_text,
        html_content=html_content,
    )
