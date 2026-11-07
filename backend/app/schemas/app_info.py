"""R-06 应用信息与备案号公开展示 Schema。"""

from pydantic import BaseModel


class AppInfoOut(BaseModel):
    """关于页/商店审核所需的公开应用信息。"""

    name: str
    version: str
    icp_record_no: str
    app_record_no: str
    software_copyright_no: str
    privacy_url: str
    terms_url: str
    support_email: str
