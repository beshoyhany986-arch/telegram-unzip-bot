import os
import shutil
import subprocess
import asyncio
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]

WORK_DIR = Path.home() / "unzip-bot" / "work"

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".m4v",
    ".ts",
    ".mts",
    ".m2ts",
    ".3gp",
}


def extract_archive(archive, output):
    output.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "7z",
            "x",
            "-y",
            f"-o{output}",
            str(archive),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if result.returncode not in (0, 1):
        raise RuntimeError(result.stdout[-2000:])


def find_videos(folder):
    return [
        p
        for p in folder.rglob("*")
        if p.is_file()
        and p.suffix.lower() in VIDEO_EXTENSIONS
    ]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك\n\n"
        "أرسل ملف ZIP أو RAR أو 7Z "
        "وسأقوم بفك الضغط وإرسال الفيديوهات."
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    filename = document.file_name or "file"
    extension = Path(filename).suffix.lower()

    allowed_archives = {
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
        ".xz"
    }

    if extension not in allowed_archives:
        await update.message.reply_text(
            "❌ الملف ده مش ملف مضغوط.\n\n"
            "📦 ابعت ZIP أو RAR أو 7Z."
        )
        return
    if not document:
        return

    job = WORK_DIR / str(update.effective_user.id)
    archive = job / (document.file_name or "archive")
    extracted = job / "extracted"

    try:
        job.mkdir(parents=True, exist_ok=True)

        msg = await update.message.reply_text(
            "📥 استلمت الملف...\n"
            "جاري تنزيله ومعالجته."
        )

        telegram_file = await document.get_file()

        await telegram_file.download_to_drive(
            custom_path=str(archive)
        )

        await msg.edit_text(
            "📦 تم تنزيل الملف.\n"
            "🔧 جاري فك الضغط..."
        )

        await asyncio.to_thread(
            extract_archive,
            archive,
            extracted
        )

        videos = find_videos(extracted)

        if not videos:
            await msg.edit_text(
                "❌ تم فك الضغط، "
                "لكن لم أجد فيديوهات."
            )
            return

        await msg.edit_text(
            f"✅ تم فك الضغط.\n"
            f"🎬 عدد الفيديوهات: {len(videos)}\n"
            f"📤 جاري الإرسال..."
        )

        for number, video in enumerate(videos, 1):

            with open(video, "rb") as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=(
                        f"🎬 {number}/{len(videos)}"
                        f" — {video.name}"
                    ),
                    supports_streaming=True,
                )

            await msg.edit_text(
                f"📤 تم إرسال "
                f"{number}/{len(videos)}"
            )

        await msg.edit_text(
            f"✅ انتهى.\n"
            f"تم إرسال {len(videos)} فيديو."
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ حصل خطأ:\n"
            f"{str(e)[:1000]}"
        )

    finally:
        shutil.rmtree(
            job,
            ignore_errors=True
        )


def main():
    WORK_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .base_url("http://127.0.0.1:8081/bot")
        .base_file_url("http://127.0.0.1:8081/file/bot")
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            handle_file
        )
    )

    print("BOT IS RUNNING...")

    app.run_polling()


if __name__ == "__main__":
    main()

