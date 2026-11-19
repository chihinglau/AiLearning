from contextlib import asynccontextmanager

import html as html_lib

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app import models  # noqa: F401  确保模型在 create_all / Alembic 前完成注册
from app.api.routes import (
    admin,
    admin_rbac,
    admin_users,
    ai,
    app_info,
    assignments,
    auth,
    content,
    data,
    exams,
    family,
    health,
    learn,
    legal,
    monitor,
    org,
    practice,
    public,
    textbooks,
    users,
)
from app.core.config import settings, validate_settings
from app.core.middleware import ErrorMaskingMiddleware, RateLimitMiddleware
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """本地开发可开启自动建表；生产环境请使用 Alembic 迁移。"""
    validate_settings()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="深爱学（AiLearning）—— 深圳中小学跨平台学习辅助应用后端服务",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # 评审 R2-06：分页总数走响应头，必须显式暴露，否则浏览器端读不到 X-Total-Count。
    expose_headers=["X-Total-Count"],
)

# 中间件顺序：后添加的在外层。ErrorMasking 最外层兜底，其次限流，最后 CORS。
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ErrorMaskingMiddleware)

app.include_router(health.router)
# 法务文档需公网免登录访问：同时挂在根路径（商店审核用）与 /api 前缀（App 内使用）。
app.include_router(legal.router)
app.include_router(legal.router, prefix=settings.api_prefix)
# R-06：备案信息同样公网免登录，供商店审核与 App「关于」页使用。
app.include_router(app_info.router)
app.include_router(app_info.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(monitor.router, prefix=settings.api_prefix)
app.include_router(public.router, prefix=settings.api_prefix)
app.include_router(practice.router, prefix=settings.api_prefix)
app.include_router(learn.router, prefix=settings.api_prefix)
app.include_router(exams.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(family.router, prefix=settings.api_prefix)
app.include_router(admin_users.router, prefix=settings.api_prefix)
app.include_router(admin_rbac.router, prefix=settings.api_prefix)
app.include_router(assignments.router, prefix=settings.api_prefix)
app.include_router(ai.router, prefix=settings.api_prefix)
app.include_router(data.router, prefix=settings.api_prefix)
app.include_router(content.router, prefix=settings.api_prefix)
app.include_router(org.router, prefix=settings.api_prefix)
app.include_router(textbooks.router, prefix=settings.api_prefix)


_LANDING_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{app_name} · 中小学学习辅助</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin: 0; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
         background: #f7f8fa; color: #1f2937; }}
  .wrap {{ max-width: 720px; margin: 0 auto; padding: 56px 24px 40px; }}
  h1 {{ font-size: 30px; margin: 0 0 12px; letter-spacing: 1px; }}
  .lead {{ color: #4b5563; line-height: 1.9; font-size: 15px; margin-bottom: 28px; }}
  .card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px 22px; margin-bottom: 16px; }}
  .card h2 {{ font-size: 16px; margin: 0 0 10px; color: #111827; }}
  .links a {{ display: inline-block; margin: 0 16px 8px 0; color: #1d4ed8; text-decoration: none; font-size: 15px; }}
  .links a:hover {{ text-decoration: underline; }}
  .meta {{ color: #6b7280; font-size: 13px; line-height: 2; }}
  footer {{ margin-top: 28px; color: #9ca3af; font-size: 12px; line-height: 2; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{app_name}</h1>
  <p class="lead">{app_desc}</p>

  <div class="card">
    <h2>法律文件</h2>
    <div class="links">{legal_links}</div>
  </div>

  <div class="card">
    <h2>联系与备案信息</h2>
    <div class="meta">{meta_lines}</div>
  </div>

  <footer>本页面为 {app_name} 官方网站首页，仅提供应用介绍、法律文件与备案信息展示。</footer>
</div>
</body>
</html>
"""


def _landing_html() -> str:
    """备案落地页：纯内联样式，不依赖任何外部资源（备案审核时可直接打开）。"""
    esc = html_lib.escape
    links = "".join(
        f'<a href="{esc(href)}">{esc(label)}</a>'
        for label, href in (
            ("隐私政策", "/legal/privacy"),
            ("用户协议", "/legal/terms"),
        )
    )
    lines = [f"客服邮箱：{esc(settings.support_email)}"]
    if settings.legal_public_base_url:
        lines.append(f"官网地址：{esc(settings.legal_public_base_url)}")
    if settings.icp_record_no:
        lines.append(
            f'ICP 备案号：<a href="https://beian.miit.gov.cn/" target="_blank" '
            f'rel="noreferrer">{esc(settings.icp_record_no)}</a>'
        )
    if settings.app_record_no:
        lines.append(f"APP 备案号：{esc(settings.app_record_no)}")
    if settings.software_copyright_no:
        lines.append(f"软件著作权登记号：{esc(settings.software_copyright_no)}")
    return _LANDING_TEMPLATE.format(
        app_name=esc(settings.app_display_name),
        app_desc=esc(
            f"{settings.app_display_name}是面向中小学的学习辅助应用，"
            "提供教材同步练习、单元 / 期中 / 期末试卷与学情反馈。"
            "当前版本 " + settings.app_version_label + "。"
        ),
        legal_links=links,
        meta_lines="<br />".join(lines),
    )


@app.get("/", response_model=None)
def root(request: Request) -> Response:
    accept = request.headers.get("accept", "")
    if "text/html" in accept.lower():
        return HTMLResponse(_landing_html())
    return JSONResponse(
        {"name": settings.app_name, "docs": "/docs", "health": "/health"}
    )
