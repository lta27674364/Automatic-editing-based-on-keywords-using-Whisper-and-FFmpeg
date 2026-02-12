"""
从视频中提取音频并获取说话内容的时间戳
"""
from openai import OpenAI
from moviepy import VideoFileClip
import os
import sys

# 配置 - 支持命令行参数
if len(sys.argv) > 1:
    VIDEO_PATH = sys.argv[1]
else:
    VIDEO_PATH = r"C:\Users\admin\Desktop\剪辑\输入.mp4"  # 默认路径
OUTPUT_TXT = os.path.join(os.path.dirname(__file__), "timestamps.txt")  # 时间戳输出路径
AUDIO_TEMP = "temp_audio.mp3"  # 临时音频文件

# OpenAI 客户端
os.environ["OPENAI_API_KEY"] = "sk-**********************************" # 配置api key
client = OpenAI(
    base_url="https://********************"
)


def extract_audio_from_video(video_path, audio_output_path):
    """
    从视频中提取音频
    """
    print(f"正在提取视频音频: {video_path}")
    video = VideoFileClip(video_path)
    audio = video.audio
    audio.write_audiofile(audio_output_path)
    video.close()
    print(f"音频已保存到: {audio_output_path}")
    return audio_output_path


def get_audio_timestamps(audio_path):
    """
    调用 OpenAI Whisper API 获取音频的时间戳
    """
    # 获取文件大小
    file_size = os.path.getsize(audio_path)
    print(f"正在上传音频并获取时间戳...")
    print(f"音频文件大小: {file_size / (1024 * 1024):.2f} MB")
    print(f"正在上传...")

    with open(audio_path, "rb") as audio_file:
        try:
            print(f"上传中，请稍候...")
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )
            print(f"上传成功!")
            print(f"正在处理音频...")
            print(f"时间戳获取成功!")
            print(f"共识别到 {len(transcription.words)} 个词")
            return transcription.words
        except Exception as e:
            print(f"上传失败: {e}")
            raise


def save_timestamps_to_txt(words, output_path):
    """
    将时间戳保存到 txt 文件
    """
    print(f"正在保存时间戳到: {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 50 + "\n")
        f.write("说话内容时间戳\n")
        f.write("=" * 50 + "\n\n")

        for word_info in words:
            start_time = word_info.start
            end_time = word_info.end
            word = word_info.word

            f.write(f"[{start_time:.2f}s - {end_time:.2f}s] {word}\n")

    print(f"时间戳已保存!")


def cleanup_temp_file(file_path):
    """
    删除临时文件
    """
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"临时文件已删除: {file_path}")


def main():
    # 1. 提取音频
    extract_audio_from_video(VIDEO_PATH, AUDIO_TEMP)

    # 2. 获取时间戳
    words = get_audio_timestamps(AUDIO_TEMP)

    # 3. 保存到 txt
    save_timestamps_to_txt(words, OUTPUT_TXT)

    # 4. 清理临时文件
    cleanup_temp_file(AUDIO_TEMP)

    print("\n完成!")


if __name__ == "__main__":
    main()
