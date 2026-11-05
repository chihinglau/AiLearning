"""开发环境初始化：创建管理员账号 + 小学一年级示例内容。

用法：python -m scripts.seed
"""

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.content import Chapter, Question, Textbook
from app.models.user import User

ADMIN_PHONE = "13800000000"
ADMIN_PASSWORD = "admin123"
DEMO_STUDENT_PHONE = "13900000000"
DEMO_STUDENT_PASSWORD = "student123"


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.phone == ADMIN_PHONE))
        if admin is None:
            admin = User(
                phone=ADMIN_PHONE,
                password_hash=hash_password(ADMIN_PASSWORD),
                nickname="内容管理员",
                role="admin",
            )
            db.add(admin)
            print(f"已创建管理员：{ADMIN_PHONE} / {ADMIN_PASSWORD}")

        if db.scalar(select(User).where(User.phone == DEMO_STUDENT_PHONE)) is None:
            db.add(
                User(
                    phone=DEMO_STUDENT_PHONE,
                    password_hash=hash_password(DEMO_STUDENT_PASSWORD),
                    nickname="小深",
                    role="student",
                    stage="primary",
                    grade=1,
                )
            )
            print(f"已创建体验学生：{DEMO_STUDENT_PHONE} / {DEMO_STUDENT_PASSWORD}")

        samples = [
            ("math", 1, "人教版", "first", "10以内加减法", "3 + 4 = ?", "B"),
            ("chinese", 1, "人教版", "first", "汉语拼音", "下列哪个是声母？", "A"),
            ("english", 1, "牛津深圳版", "first", "Unit 1 Hello", "How do you say 你好?", "A"),
        ]
        for subject, grade, version, semester, chapter_name, stem, answer in samples:
            textbook = db.scalar(
                select(Textbook).where(
                    Textbook.subject == subject,
                    Textbook.grade == grade,
                    Textbook.version == version,
                    Textbook.semester == semester,
                )
            )
            if textbook is None:
                textbook = Textbook(
                    subject=subject, grade=grade, version=version, semester=semester
                )
                db.add(textbook)
                db.flush()

            chapter = db.scalar(
                select(Chapter).where(
                    Chapter.textbook_id == textbook.id, Chapter.name == chapter_name
                )
            )
            if chapter is None:
                chapter = Chapter(
                    textbook_id=textbook.id, grade=grade, name=chapter_name, order_index=1
                )
                db.add(chapter)
                db.flush()

            exists = db.scalar(select(Question).where(Question.chapter_id == chapter.id))
            if exists is None:
                db.add(
                    Question(
                        chapter_id=chapter.id,
                        subject=subject,
                        q_type="choice",
                        content={"stem": stem},
                        options=[
                            {"key": "A", "text": "选项 A"},
                            {"key": "B", "text": "选项 B"},
                            {"key": "C", "text": "选项 C"},
                        ],
                        answer={"value": answer},
                        analysis="示例题目，仅用于本地联调。",
                        difficulty=2,
                        tags=[chapter_name],
                    )
                )
        db.commit()
        print("示例教材/章节/题目已就绪")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
