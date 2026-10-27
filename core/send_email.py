import ast
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, List, Optional, Sequence, Type
from core.comdata import CommonData
from core.utils.u_compress import create_zip_archive


class ReportEmailSender:
    """构建测试报告邮件，并通过 SMTP 或 SMTP_SSL 发送。"""

    def __init__(self) -> None:
        email_config = CommonData.get_config_data()["邮件发送配置"]
        self._host = email_config["host"]
        self._port = int(email_config["port"])
        self._sender_name = email_config["sender"]
        self._sender_address = email_config["send_email"]
        self._recipients = self._parse_recipients(email_config["receiver"])
        self._password = email_config["pwd"]
        self._subject = email_config["subject"]

    @staticmethod
    def _parse_recipients(raw_recipients: str) -> List[str]:
        """安全解析配置文件中的收件人列表。"""
        recipients = ast.literal_eval(raw_recipients)
        if not isinstance(recipients, (list, tuple)) or not all(
            isinstance(address, str) for address in recipients
        ):
            raise ValueError("邮件接收方必须配置为字符串列表！")
        return list(recipients)

    @staticmethod
    def _create_plain_text_part(content: str) -> MIMEText:
        """创建纯文本邮件正文。"""
        return MIMEText(content, "plain", "utf-8")

    @staticmethod
    def _create_html_part(html_content: str) -> MIMEText:
        """创建 HTML 邮件正文。"""
        return MIMEText(html_content, "html", "utf-8")

    @staticmethod
    def _create_attachment(file_path: str) -> MIMEApplication:
        """读取文件并创建标准 MIME 附件。"""
        with open(file_path, "rb") as attachment_file:
            attachment = MIMEApplication(
                attachment_file.read(), Name=os.path.basename(file_path)
            )
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(file_path),
        )
        return attachment

    def _build_message(
        self,
        parts: Sequence[Any],
        send_date: Optional[str] = None,
    ) -> MIMEMultipart:
        """设置邮件头并挂载正文和附件。"""
        message = MIMEMultipart("mixed")
        message["Subject"] = self._subject
        message["From"] = f"{self._sender_name} <{self._sender_address}>"
        message["To"] = ";".join(self._recipients)
        message["Date"] = send_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for part in parts:
            message.attach(part)
        return message

    def _send_with_client(
        self,
        smtp_client_class: Type,
        message: MIMEMultipart,
    ) -> None:
        """使用指定 SMTP 客户端发送消息并可靠关闭连接。"""
        smtp_client = smtp_client_class(self._host, port=self._port)
        try:
            smtp_client.login(self._sender_address, self._password)
            smtp_client.sendmail(
                self._sender_address,
                self._recipients,
                message.as_string(),
            )
        finally:
            smtp_client.quit()

    def _send_message(self, message: MIMEMultipart) -> None:
        """优先使用 SMTP，连接或发送失败时回退到 SMTP_SSL。"""
        try:
            self._send_with_client(smtplib.SMTP, message)
        except Exception:
            self._send_with_client(smtplib.SMTP_SSL, message)

        send_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"{self._sender_address}给{self._recipients}发送邮件成功,"
            f"发送时间:{send_time}"
        )

    @staticmethod
    def _get_report_attachment_path(report_type: str) -> str:
        """获取报告附件路径，Allure 报告会先压缩为 ZIP。"""
        if report_type == "allure":
            allure_report_path = CommonData.get_allure_report_path()
            zip_path = os.path.join(os.path.dirname(allure_report_path), "allure.zip")
            return create_zip_archive(allure_report_path, zip_path)
        if report_type == "html":
            return os.path.join(CommonData.get_html_path(), "auto_reports.html")
        raise ValueError(f"暂不支持此邮件报告类型:{report_type}")

    def send_report(
        self,
        send_date: Optional[str] = None,
        content: str = "",
        html_content: str = "",
        report_type: str = "html",
    ) -> None:
        """构建并发送带测试报告附件的邮件。"""
        message_parts: List[Any] = [self._create_plain_text_part(content)]
        if html_content:
            message_parts.append(self._create_html_part(html_content))
        else:
            attachment_path = self._get_report_attachment_path(report_type)
            message_parts.append(self._create_attachment(attachment_path))

        message = self._build_message(message_parts, send_date)
        self._send_message(message)


if __name__ == "__main__":
    email_content = "本邮件由系统自动发出，无需回复！\n各位同事，大家好，以下为本次测试报告!"
    ReportEmailSender().send_report(content=email_content, report_type="html")
