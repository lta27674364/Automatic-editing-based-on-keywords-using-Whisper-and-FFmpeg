import re
import os
import subprocess
import shutil
import sys

# FFmpeg 路径配置
FFMPEG_PATH = r"F:\ffmpeg\ffmpeg-2026-02-09-git-9bfa1635ae-essentials_build\ffmpeg-2026-02-09-git-9bfa1635ae-essentials_build\bin\ffmpeg.exe" # 配置ffmpeg路径

# 视频路径 - 支持命令行参数
if len(sys.argv) > 1:
    VIDEO_PATH = sys.argv[1]
else:
    VIDEO_PATH = r"C:\Users\admin\Desktop\剪辑\输入.mp4" # 配置视频路径

# --- GPU 编码配置 ---
# 只使用 GPU 编码，不使用 GPU 解码，以换取最大的稳定性
VIDEO_CODEC = 'h264_nvenc'
PRESET = 'p4'
RC_MODE = 'vbr'
CQ_VALUE = '23'


def parse_timestamps_keep(txt_path):
    """解析时间戳"""
    segments = []
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('='):
            continue
        match = re.match(r'\[([\d.]+)s - ([\d.]+)s\]', line)
        if match:
            segments.append({
                'start': float(match.group(1)),
                'end': float(match.group(2))
            })
    return segments


def merge_adjacent_segments(segments):
    """合并相邻区间"""
    if not segments:
        return []
    sorted_segments = sorted(segments, key=lambda x: x['start'])
    merged = [sorted_segments[0]]
    for seg in sorted_segments[1:]:
        if seg['start'] <= merged[-1]['end']:
            merged[-1]['end'] = max(merged[-1]['end'], seg['end'])
        else:
            merged.append(seg)
    return merged


def concat_video_ffmpeg_safe(video_path, segments, temp_dir):
    """
    分步处理：
    1. 分别截取每个片段保存为临时文件 (使用 GPU 编码)
    2. 使用 concat 协议无损合并
    """
    segments = merge_adjacent_segments(segments)
    total = len(segments)
    print(f"\n采用稳定模式处理，共有 {total} 个片段...")
    print("正在排队处理中，请耐心等待...")

    clips_dir = os.path.join(temp_dir, "clips")
    if os.path.exists(clips_dir):
        shutil.rmtree(clips_dir)
    os.makedirs(clips_dir)

    # 2. 循环截取每个片段
    for i, seg in enumerate(segments):
        clip_path = os.path.join(clips_dir, f"clip_{i:04d}.mp4")
        duration = seg['end'] - seg['start']

        # 命令解释：
        # -ss 放在 -i 前面：快速定位（输入级跳转，速度极快）
        # 去掉了 -hwaccel cuda：避免定位导致的解码报错，由CPU软解，稳定性最高
        # -c:v h264_nvenc：核心加速点，使用显卡编码，速度极快
        cmd = [
            FFMPEG_PATH, '-y',
            '-ss', str(seg['start']),
            '-i', video_path,
            '-t', str(duration),
            '-c:v', VIDEO_CODEC,  # GPU 编码
            '-preset', PRESET,
            '-rc', RC_MODE,
            '-cq', CQ_VALUE,
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '0:a:0?',
            clip_path
        ]

        # 打印进度，不隐藏输出，让你看到它在动
        print(f"\n[{i + 1}/{total}] 正在处理片段: {seg['start']:.2f}s - {seg['end']:.2f}s")

        try:
            # 这里的 check=True 如果报错会直接抛出异常，方便排查
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"\n错误：处理第 {i + 1} 个片段时失败。")
            print(f"错误命令: {e.cmd}")
            # 可以选择继续或停止
            break

    print("\n\n正在合并片段...")

    # 3. 创建合并列表文件
    list_file_path = os.path.join(temp_dir, "filelist.txt")
    with open(list_file_path, 'w', encoding='utf-8') as f:
        for i in range(total):
            abs_path = os.path.abspath(os.path.join(clips_dir, f"clip_{i:04d}.mp4"))
            safe_path = abs_path.replace('\\', '/')
            f.write(f"file '{safe_path}'\n")

    output_path = os.path.join(temp_dir, "cut_video.mp4")

    # 4. 合并视频 (无需重编码，速度极快)
    cmd_concat = [
        FFMPEG_PATH, '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file_path,
        '-c', 'copy',
        output_path
    ]
    subprocess.run(cmd_concat, check=True)

    print(f"剪辑完成: {output_path}")
    return output_path


def speed_up_video(input_path, output_path, speed=1.5):
    """加速视频 (GPU加速)"""
    print(f"\n正在加速视频 ({speed}x, GPU模式)...")

    cmd = [
        FFMPEG_PATH, '-y',
        # 这一步也可以去掉 -hwaccel cuda，更稳妥
        '-i', input_path,
        '-filter_complex',
        f'[0:v]setpts=1/{speed}*PTS[v];[0:a]atempo={speed}[a]',
        '-map', '[v]',
        '-map', '[a]',
        '-c:v', VIDEO_CODEC,
        '-preset', PRESET,
        '-rc', RC_MODE,
        '-cq', CQ_VALUE,
        '-c:a', 'aac',
        output_path
    ]

    subprocess.run(cmd, check=True)
    print(f"加速完成: {output_path}")


def main():
    VIDEO_PATH = r"C:\Users\admin\Desktop\剪辑\输入.mp4"
    TIMESTAMPS_KEEP = "timestamps_1.txt"
    OUTPUT_VIDEO = r"C:\Users\admin\Desktop\剪辑\输出.mp4"
    TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")

    os.makedirs(TEMP_DIR, exist_ok=True)

    print("=" * 50)
    print("视频剪辑工具（GPU编码 - 极速稳定版）")
    print("=" * 50)

    print("\n正在读取 timestamps_1.txt...")
    segments = parse_timestamps_keep(TIMESTAMPS_KEEP)
    print(f"共读取到 {len(segments)} 个保留片段")

    # 剪辑
    cut_video = concat_video_ffmpeg_safe(VIDEO_PATH, segments, TEMP_DIR)

    # 加速
    final_output = OUTPUT_VIDEO.replace(".mp4", "_加速.mp4")
    speed_up_video(cut_video, final_output, speed=1.5)

    # 删除临时文件
    if os.path.exists(OUTPUT_VIDEO):
        os.remove(OUTPUT_VIDEO)

    print("\n" + "=" * 50)
    print(f"完成！输出视频: {final_output}")
    print("=" * 50)


if __name__ == "__main__":
    main()
