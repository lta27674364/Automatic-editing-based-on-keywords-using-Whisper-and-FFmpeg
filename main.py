"""
主程序：整合视频剪辑流程
执行顺序：
1. extract_audio_timestamps.py - 提取音频并获取时间戳
2. phase1_cut.py - 第一阶段裁剪时间戳文本
3. edit_video1.py - 根据时间戳剪辑视频
"""
import os
import sys

# 添加当前目录到路径，确保能导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入各个阶段的模块
import extract_audio_timestamps
import phase1_cut
import edit_video1


def main():
    # 支持命令行参数接收视频路径
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        print(f"使用命令行视频路径: {video_path}")
    else:
        video_path = None
        print("未提供视频路径，各模块将使用默认路径")

    print("=" * 60)
    print("视频剪辑主程序")
    print("=" * 60)

    # --- 阶段1: 提取音频时间戳 ---
    print("\n" + "=" * 50)
    print("阶段 1: 提取音频并获取时间戳")
    print("=" * 50)
    try:
        # 如果有命令行参数，修改 extract_audio_timestamps 的 VIDEO_PATH
        if video_path:
            extract_audio_timestamps.VIDEO_PATH = video_path
        extract_audio_timestamps.main()
        print("阶段 1 完成!")
    except Exception as e:
        print(f"阶段 1 出错: {e}")
        sys.exit(1)

    # --- 阶段2: 裁剪时间戳文本 ---
    print("\n" + "=" * 50)
    print("阶段 2: 裁剪时间戳文本（识别'重来'指令）")
    print("=" * 50)
    try:
        phase1_cut.main()
        print("阶段 2 完成!")
    except Exception as e:
        print(f"阶段 2 出错: {e}")
        sys.exit(1)

    # --- 阶段3: 剪辑视频 ---
    print("\n" + "=" * 50)
    print("阶段 3: 根据时间戳剪辑视频")
    print("=" * 50)
    try:
        # 如果有命令行参数，修改 edit_video1 的 VIDEO_PATH
        if video_path:
            edit_video1.VIDEO_PATH = video_path
        edit_video1.main()
        print("阶段 3 完成!")
    except Exception as e:
        print(f"阶段 3 出错: {e}")
        sys.exit(1)

    # --- 完成 ---
    print("\n" + "=" * 60)
    print("所有阶段完成！")
    print("=" * 60)
    print("\n生成的文件:")
    print("  - timestamps.txt (原始时间戳)")
    print("  - timestamps_1.txt (裁剪后时间戳)")
    print("  - 演讲稿文本.txt (演讲稿)")
    print("  - 演讲稿文本1.txt (裁剪后演讲稿)")
    print("  - cut_segments.txt (被剪去的时间段)")
    print("  - 输出视频: 输出.mp4")


if __name__ == "__main__":
    main()
