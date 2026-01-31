# scboy_signin_scheduler.py
import os
import hashlib
import requests
import json
import configparser
import time
from datetime import datetime
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler

from dark_log import DarkLog
from push_ddmail import Dingdingmail

logger = DarkLog('scboy_sign_in')
notifier = Dingdingmail('scboy_sign_in')


class ScboyAutoCheckin:
    def __init__(self, phone, password):
        self.phone = phone
        self.password = password
        self.results = []
        self.max_retries = 3
        self.session = requests.Session()

        self.BASE_URL = "https://www.scboy.cc"
        self.LOGIN_URL = f"{self.BASE_URL}/?user-login.htm"
        self.CHECKIN_URL = f"{self.BASE_URL}/?mod-checkin.htm"

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.BASE_URL + "/",
            "Origin": self.BASE_URL
        })

    def md5(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def login(self):
        logger.info(f"[{self.phone}] 正在登录...")
        pwd_md5 = self.md5(self.password)
        data = {
            'mobile': self.phone,
            'password': pwd_md5
        }
        try:
            resp = self.session.post(self.LOGIN_URL, data=data, timeout=15)
            resp.raise_for_status()

            try:
                result = resp.json()
                code = result.get("code")
                message = result.get("message", "")
                if code == "0":
                    logger.info(f"[{self.phone}] 登录成功: {message}")
                    self.results.append("✅ 登录成功")
                    return True
                else:
                    logger.error(f"[{self.phone}] 登录失败: {message}")
                    self.results.append(f"❌ 登录失败: {message}")
                    return False
            except json.JSONDecodeError:
                text = resp.text.strip()
                if text == "1":
                    logger.info(f"[{self.phone}] 登录成功（旧版响应）")
                    self.results.append("✅ 登录成功（旧版）")
                    return True
                else:
                    logger.error(f"[{self.phone}] 未知登录响应: {text}")
                    self.results.append(f"❌ 未知响应: {text}")
                    return False

        except Exception as e:
            logger.exception(f"[{self.phone}] 登录请求异常: {e}")
            self.results.append(f"💥 登录异常: {str(e)}")
            return False

    def checkin(self):
        logger.info(f"[{self.phone}] 正在签到...")
        try:
            resp = self.session.post(self.CHECKIN_URL, data="", timeout=15)
            resp.raise_for_status()

            try:
                result = resp.json()
                code = result.get("code")
                message = result.get("message", "")
                if code == "0":
                    logger.info(f"[{self.phone}] 签到成功: {message}")
                    self.results.append(f"🎉 签到成功: {message}")
                elif "已经签过" in message or "重复" in message:
                    logger.info(f"[{self.phone}] 今日已签到: {message}")
                    self.results.append(f"ℹ️ 今日已签到: {message}")
                else:
                    logger.error(f"[{self.phone}] 签到失败: {message}")
                    self.results.append(f"❌ 签到失败: {message}")
            except json.JSONDecodeError:
                text = resp.text.strip()
                if "成功" in text or "签到" in text:
                    self.results.append(f"🎉 签到成功（文本）: {text}")
                elif "已经签过" in text or "重复" in text:
                    self.results.append(f"ℹ️ 今日已签到（文本）: {text}")
                else:
                    self.results.append(f"⚠️ 未知签到响应: {text}")

        except Exception as e:
            logger.exception(f"[{self.phone}] 签到请求异常: {e}")
            self.results.append(f"💥 签到异常: {str(e)}")

    def run(self):
        retry_count = 0
        success = False

        while retry_count < self.max_retries and not success:
            retry_count += 1
            logger.info(f"[{self.phone}] 开始第 {retry_count} 次尝试...")

            if self.login():
                self.checkin()
                success = True
                break
            else:
                wait_time = min(2 ** retry_count, 30)
                logger.warning(f"[{self.phone}] 第 {retry_count} 次失败，{wait_time} 秒后重试...")
                time.sleep(wait_time)

        if not success:
            logger.error(f"[{self.phone}] 经过 {self.max_retries} 次尝试后仍失败")
            self.results.append("❌ 所有重试均失败")

        title = f"SCBOY 签到 - {self.phone}"
        content = "\n\n".join(self.results)
        notifier.get_dingding(title, content)
        notifier.get_mail(title, content.replace("\n\n", "<br>"))


def job():
    config = configparser.ConfigParser()
    # ✅ 关键修复：强制 UTF-8 读取
    with open('config/config.ini', 'r', encoding='utf-8') as f:
        config.read_file(f)

    scboy_sections = [sec for sec in config.sections() if sec.startswith('SCBOY_')]
    if not scboy_sections:
        error_msg = "未找到任何以 'SCBOY_' 开头的账号配置（例如 [SCBOY_1]）"
        logger.error(error_msg)
        notifier.get_dingding("配置错误", error_msg)
        return

    logger.info(f"检测到 {len(scboy_sections)} 个 SCBOY 账号，开始依次签到...")

    for section in scboy_sections:
        try:
            phone = config.get(section, 'phone')
            password = config.get(section, 'password')
            logger.info(f"开始处理账号: {phone} (配置节: {section})")

            task = ScboyAutoCheckin(phone, password)
            task.run()

            time.sleep(3)

        except Exception as e:
            error_msg = f"处理账号 {section} 时异常: {str(e)}"
            logger.exception(error_msg)
            notifier.get_dingding("SCBOY 签到异常", error_msg)
            notifier.get_mail("SCBOY 签到异常", error_msg.replace("\n", "<br>"))


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone='Asia/Shanghai')


    @scheduler.scheduled_job('cron', hour=9, minute=0, timezone='Asia/Shanghai')
    def scheduled_job():
        try:
            job()
        except Exception as e:
            logger.error(f"定时任务执行失败: {e}")
            notifier.get_dingding("SCBOY 定时任务失败", str(e))
            notifier.get_mail("SCBOY 定时任务失败", str(e))


    beijing_now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
    init_msg = f"SCBOY 多账号签到脚本初始化成功<br/>将在每天 09:00 执行<br/>当前时间: {beijing_now}"

    logger.info(f"SCBOY 签到脚本启动。当前时间: {beijing_now}")
    notifier.get_dingding("SCBOY 脚本启动", init_msg)
    notifier.get_mail("SCBOY 脚本启动", init_msg)

    logger.info("首次启动，立即执行签到...")
    try:
        job()
    except Exception as e:
        logger.error(f"首次执行失败: {e}")
        notifier.get_dingding("SCBOY 首次执行失败", str(e))
        notifier.get_mail("SCBOY 首次执行失败", str(e))
    logger.info("首次签到完成，进入定时等待...")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("SCBOY 定时任务已停止")
        notifier.get_dingding("SCBOY 任务停止", "脚本已停止运行")