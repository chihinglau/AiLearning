"""生产账号 bootstrap（管理员 + 可选质检学生）。

问题背景：生产用 `RUN_SEED=false` 启动、内容由数据包导入，此时库里**一个账号都没有**，
既进不了后台，也没法做任何登录态验收。

用法（在 backend 目录，或 docker compose exec api）：
    ADMIN_PASSWORD='<强口令>' python -m scripts.bootstrap_admin
    ADMIN_PASSWORD='<强口令>' ADMIN_PHONE=13800000000 ADMIN_NICKNAME=内容管理员 \
        python -m scripts.bootstrap_admin
    # 顺带建一个质检学生（仅用于冒烟验收，可加 --no-student 跳过）
    ADMIN_PASSWORD='<强口令>' QUALITY_STUDENT_PHONE=13900000001 QUALITY_STUDENT_PASSWORD='<口令>' \
        python -m scripts.bootstrap_admin

安全约束：
- 密码只从环境变量读，不接受命令行明文参数（避免进 shell 历史）。
- production 环境拒绝弱口令（长度 <10、等于 admin123/student123、纯数字）。
- 幂等：账号已存在时默认跳过；`--reset-password` 才改口令。
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User
from app.services.rbac import backfill_user_roles, sync_catalog

WEAK_PASSWORDS = {"admin123", "student123", "123456", "password", "12345678"}


def _check_password(phone: str, password: str | None, label: str) -> str:
    if not password:
        print(f"❌ 缺少 {label} 口令：请通过环境变量传入")
        raise SystemExit(2)
    if settings.app_env == "production" and (
        len(password) < 10 or password in WEAK_PASSWORDS or password.isdigit()
    ):
        print(f"❌ {label} 口令太弱（生产要求 ≥10 位、非纯数字、非常见弱口令）")
        raise SystemExit(2)
    return password


def _ensure_user(db, phone: str, password: str, nickname: str, role: str, **extra) -> bool:
    existing = db.scalar(select(User).where(User.phone == phone))
    if existing is not None:
        if existing.role != role:
            print(f"❌ {phone} 已存在但角色是 {existing.role}（期望 {role}），不做覆盖，请人工处理")
            raise SystemExit(3)
        print(f"· {role} {phone} 已存在，跳过")
        return False
    db.add(
        User(
            phone=phone,
            password_hash=hash_password(password),
            nickname=nickname,
            role=role,
            **extra,
        )
    )
    db.commit()
    print(f"✅ 已创建 {role}：{phone}（{nickname}）")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="生产账号 bootstrap")
    parser.add_argument("--reset-password", action="store_true", help="已存在时重置口令")
    parser.add_argument("--no-student", action="store_true", help="不创建质检学生")
    args = parser.parse_args()

    admin_phone = os.getenv("ADMIN_PHONE", "13800000000").strip()
    admin_nickname = os.getenv("ADMIN_NICKNAME", "内容管理员").strip()
    admin_password = _check_password(admin_phone, os.getenv("ADMIN_PASSWORD"), "管理员")

    student_phone = os.getenv("QUALITY_STUDENT_PHONE", "13900000001").strip()
    student_password_env = os.getenv("QUALITY_STUDENT_PASSWORD")
    if not args.no_student and student_phone:
        student_password = _check_password(student_phone, student_password_env, "质检学生")
    else:
        student_password = None

    db = SessionLocal()
    try:
        # 1. RBAC 目录（角色/权限/授权关系）——空库时第一次跑必须补
        stats = sync_catalog(db)
        print(f"RBAC catalog 同步：{stats}")

        # 2. 管理员
        created = _ensure_user(db, admin_phone, admin_password, admin_nickname, "admin")
        if not created and args.reset_password:
            user = db.scalar(select(User).where(User.phone == admin_phone))
            user.password_hash = hash_password(admin_password)
            db.commit()
            print(f"🔁 已重置管理员口令：{admin_phone}")

        # 3. 质检学生（用于登录态冒烟，不对学生开放）
        if student_password:
            _ensure_user(
                db,
                student_phone,
                student_password,
                "质检学生",
                "student",
                stage="primary",
                grade=1,
            )

        # 4. 补齐 user_roles 关联
        filled = backfill_user_roles(db)
        db.commit()
        print(f"user_roles 补齐：{filled} 条")

        total = db.scalar(select(User.id).order_by(User.id.desc()).limit(1))
        print(f"完成。当前用户表最大 id = {total}")
    finally:
        db.close()
    if settings.app_env == "production":
        print("提示：生产环境请确认 Nginx/Caddy 未对公开放 /docs 与 /openapi.json（见部署文档 §7）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
