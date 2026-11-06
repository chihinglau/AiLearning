"""家庭绑定相关查询（D-03 §7.2、D-05 §3.1）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import ParentChildBinding, User


def has_active_guardian(db: Session, child: User) -> bool:
    """儿童账号是否已有生效的监护人绑定且完成同意留痕。"""
    binding = db.scalar(
        select(ParentChildBinding.id).where(
            ParentChildBinding.child_id == child.id,
            ParentChildBinding.status == "active",
            ParentChildBinding.consent_at.is_not(None),
        )
    )
    return binding is not None
