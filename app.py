"""
极简版 - 只用 pymysql + minio
"""
import pymysql
from minio import Minio
import uuid
import json
from datetime import datetime
from io import BytesIO

# ============== 配置 ==============
MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root123",
    "database": "video_processing",
    "charset": "utf8mb4"
}

MINIO_CONFIG = {
    "endpoint": "localhost:9000",
    "access_key": "admin",
    "secret_key": "admin123",
    "secure": False
}

BUCKET_NAME = "videos"


# ============== MySQL 操作 ==============
def get_conn():
    """获取数据库连接"""
    return pymysql.connect(**MYSQL_CONFIG)


def init_db():
    """初始化数据库表"""
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS video_tasks (
                    id VARCHAR(36) PRIMARY KEY,
                    status VARCHAR(20) DEFAULT 'pending',
                    input_bucket VARCHAR(255),
                    input_key VARCHAR(500),
                    output_url VARCHAR(1000),
                    progress INT DEFAULT 0,
                    current_step VARCHAR(100),
                    result_json JSON,
                    error_message TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
        conn.commit()
    finally:
        conn.close()


def save_task(task_id: str, input_bucket: str, input_key: str):
    """保存任务"""
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO video_tasks (id, status, input_bucket, input_key, current_step, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (task_id, "pending", input_bucket, input_key, "等待处理", datetime.now(), datetime.now())
            )
        conn.commit()
    finally:
        conn.close()


def get_task(task_id: str):
    """查询任务"""
    conn = get_conn()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM video_tasks WHERE id = %s", (task_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def list_tasks():
    """列出所有任务"""
    conn = get_conn()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT id, status, progress, current_step, created_at FROM video_tasks ORDER BY created_at DESC")
            return cursor.fetchall()
    finally:
        conn.close()


def update_task(task_id: str, **kwargs):
    """更新任务"""
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            fields = ", ".join([f"{k} = %s" for k in kwargs])
            values = list(kwargs.values()) + [task_id]
            cursor.execute(f"UPDATE video_tasks SET {fields}, updated_at = %s WHERE id = %s", values + [datetime.now()])
        conn.commit()
    finally:
        conn.close()


# ============== MinIO 操作 ==============
minio_client = Minio(**MINIO_CONFIG)


def ensure_bucket():
    """确保 bucket 存在"""
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)


def upload_video(task_id: str, filename: str, file_data: bytes, content_type: str = "video/mp4"):
    """上传视频到 MinIO"""
    ensure_bucket()
    object_name = f"raw/{task_id}/{filename}"
    minio_client.put_object(BUCKET_NAME, object_name, BytesIO(file_data), len(file_data), content_type=content_type)
    return BUCKET_NAME, object_name


def get_video_url(bucket: str, key: str) -> str:
    """获取视频访问URL"""
    return f"http://localhost:9000/{bucket}/{key}"


import subprocess
import tempfile
import os

# ============== 主程序 ==============
if __name__ == "__main__":
    # 初始化
    init_db()
    ensure_bucket()

    print("=" * 50)
    print("1. 上传视频")
    # print("2. 查询任务")
    # print("3. 列出所有任务")
    # print("4. 更新任务状态")
    print("q. 退出")
    print("=" * 50)

    while True:
        cmd = input("\n请选择: ").strip()

        if cmd == "1":
            # 上传视频
            filepath = input("视频文件路径: ").strip('"')
            if not filepath:
                continue

            with open(filepath, "rb") as f:
                data = f.read()

            task_id = str(uuid.uuid4())
            filename = filepath.split("\\")[-1]

            # 存 MinIO
            bucket, key = upload_video(task_id, filename, data)

            # 存 MySQL
            save_task(task_id, bucket, key)

            print(f"\n任务已创建!")
            print(f"  任务ID: {task_id}")
            print(f"  视频URL: {get_video_url(bucket, key)}")

            # 从 MinIO 下载到临时文件
            print("\n正在下载视频...")
            tmp_path = f"temp_{task_id}.mp4"
            with open(tmp_path, "wb") as f:
                f.write(data)

            print(f"临时文件: {tmp_path}")

            # 自动执行根目录的 main.py
            print("\n开始执行处理脚本...")
            try:
                # 获取 .venv 的 Python 路径
                project_root = os.path.dirname(os.path.abspath(__file__))
                venv_python = os.path.join(project_root, "..", ".venv", "Scripts", "python.exe")
                if not os.path.exists(venv_python):
                    venv_python = os.path.join(project_root, "..", ".venv", "bin", "python")

                # 调用根目录 main.py，传入临时视频路径，实时显示输出
                result = subprocess.run(
                    [venv_python, "main.py", tmp_path],
                    cwd=os.path.join(project_root, ".."),
                    encoding="utf-8",
                    errors="ignore"
                )

                if result.returncode == 0:
                    print("\n处理完成!")
                    update_task(task_id, status="completed", current_step="处理完成")
                else:
                    print(f"\n处理失败!")
                    update_task(task_id, status="failed", current_step="处理失败")
            except Exception as e:
                print(f"执行失败: {e}")
                update_task(task_id, status="failed", current_step=str(e)[:100])
            finally:
                # 清理临时文件
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        elif cmd == "2":
            # 查询任务
            task_id = input("任务ID: ").strip()
            task = get_task(task_id)
            if task:
                print(f"\n任务信息:")
                for k, v in task.items():
                    print(f"  {k}: {v}")
            else:
                print("任务不存在")

        elif cmd == "3":
            # 列出任务
            tasks = list_tasks()
            print(f"\n共有 {len(tasks)} 个任务:")
            for t in tasks:
                print(f"  {t['id'][:8]}... | {t['status']} | {t['current_step']}")

        elif cmd == "4":
            # 更新任务
            task_id = input("任务ID: ").strip()
            status = input("新状态 (pending/processing/completed/failed): ").strip()
            step = input("当前步骤: ").strip()
            update_task(task_id, status=status, current_step=step)
            print("已更新")

        elif cmd == "q":
            break
