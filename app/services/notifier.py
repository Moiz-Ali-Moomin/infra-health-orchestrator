import logging
import smtplib
from email.mime.text import MIMEText
import requests
import json
from app.config import settings

logger = logging.getLogger(__name__)

class Notifier:
    @staticmethod
    def send_slack_alert(message: str):
        if not settings.SLACK_WEBHOOK_URL:
            logger.debug("SLACK_WEBHOOK_URL not configured. Skipping Slack alert.")
            return
            
        try:
            payload = {"text": message}
            response = requests.post(
                settings.SLACK_WEBHOOK_URL,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            response.raise_for_status()
            logger.info("Successfully sent Slack alert")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    @staticmethod
    def send_email_alert(subject: str, message: str):
        if not settings.SMTP_HOST or not settings.ALERT_EMAIL_TO:
            logger.debug("SMTP_HOST or ALERT_EMAIL_TO not configured. Skipping email alert.")
            return
            
        try:
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = settings.ALERT_EMAIL_FROM
            msg['To'] = settings.ALERT_EMAIL_TO
            
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5) as server:
                server.send_message(msg)
            logger.info("Successfully sent email alert")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    @classmethod
    def alert_failure(cls, check_name: str, details: dict):
        message = f"🚨 *System Health Validation Failed*\n*Check:* {check_name}\n*Details:* ```json\n{json.dumps(details, indent=2)}\n```"
        logger.error(f"Triggering alerts for failure in {check_name}")
        cls.send_slack_alert(message)
        cls.send_email_alert(f"Health Check Failed: {check_name}", message)
