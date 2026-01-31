# push_ddmail.py
import smtplib
import requests
import configparser
from email.mime.text import MIMEText
from email.header import Header

class Dingdingmail:
    def __init__(self, task_name):
        self.task_name = task_name
        self.config = configparser.ConfigParser()
        # ✅ 关键修复：强制 UTF-8 读取
        with open('config/config.ini', 'r', encoding='utf-8') as f:
            self.config.read_file(f)

    def _get_dingding_webhook(self):
        try:
            return self.config.get('dingding', 'webhook', fallback=None)
        except:
            return None

    def _get_email_config(self):
        try:
            return {
                'smtp_server': self.config.get('EMAIL', 'smtp_server'),
                'smtp_port': self.config.getint('EMAIL', 'smtp_port'),
                'sender': self.config.get('EMAIL', 'sender'),
                'password': self.config.get('EMAIL', 'password'),
                'receivers': [r.strip() for r in self.config.get('EMAIL', 'receivers').split(',')]
            }
        except Exception as e:
            print(f"邮箱配置读取失败: {e}")
            return None

    def get_dingding(self, title, message):
        webhook = self._get_dingding_webhook()
        if not webhook:
            print("⚠️ 未配置钉钉 webhook，跳过通知")
            return

        full_msg = f"【{self.task_name}】\n\n{title}\n\n{message}"
        payload = {
            "msgtype": "text",
            "text": {
                "content": full_msg
            }
        }

        try:
            resp = requests.post(webhook, json=payload, timeout=10)
            if resp.status_code == 200 and resp.json().get("errcode") == 0:
                print("✅ 钉钉通知发送成功")
            else:
                print(f"❌ 钉钉通知失败: {resp.text}")
        except Exception as e:
            print(f"💥 钉钉通知异常: {e}")

    def get_mail(self, subject, html_content):
        email_cfg = self._get_email_config()
        if not email_cfg:
            print("⚠️ 邮箱配置缺失，跳过邮件通知")
            return

        try:
            msg = MIMEText(html_content, 'html', 'utf-8')
            msg['From'] = Header(email_cfg['sender'])
            msg['To'] = Header(", ".join(email_cfg['receivers']))
            msg['Subject'] = Header(f"[{self.task_name}] {subject}", 'utf-8')

            server = smtplib.SMTP(email_cfg['smtp_server'], email_cfg['smtp_port'])
            server.starttls()
            server.login(email_cfg['sender'], email_cfg['password'])
            server.sendmail(
                email_cfg['sender'],
                email_cfg['receivers'],
                msg.as_string()
            )
            server.quit()
            print("✅ 邮件通知发送成功")
        except Exception as e:
            print(f"💥 邮件通知异常: {e}")