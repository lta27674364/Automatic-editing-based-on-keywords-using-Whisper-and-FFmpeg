import os
from openai import OpenAI

os.environ["OPENAI_API_KEY"] = "sk-PPuZAgTDe40Ek9Yy34D010EcDb6f4760A6Bc4bDc3628B09b"
client = OpenAI(
    base_url="https://chat.9000aigc.com/v1"
)

# 你的剪辑规则提示词
system_prompt = """
你现在的任务是对一段未经整理的演讲口语转写稿进行剪辑处理。

这是连续的线性文本。文本中包含多次"讲一段 → 否定 → 重讲"的结构。

严格处理规则：

只允许删除文本，禁止修改、润色、替换或重写任何保留内容。

将文本按时间顺序理解为多个"表达版本块"：
每一次连续讲述的内容，直到出现否定信号为止，视为一个完整版本块。

当出现否定或重录信号时，必须删除：
最近一次完整的表达版本块 + 该否定语句本身。

否定信号包括但不限于：
"重来""再重来""不对""讲错了""这句没讲好""卡住了""算了重来""我要换个讲法""太枯燥""太技术""听不懂""没必要讲这个"等。

如果连续出现多个否定信号，视为对同一版本块的重复否定。

只保留最后一次未被否定的完整表达版本。

不做任何语义优化或逻辑重组。

输出最终清理后的完整文本，不添加解释或说明。
"""

# 文件路径配置
txt_file_path = "演讲稿文本.txt"
timestamps_file_path = "timestamps.txt"
output_txt_path = "演讲稿文本1.txt"
output_timestamps_path = "timestamps_1.txt"


def parse_timestamps(filepath):
    """
    解析时间戳文件，返回：
    - chars: 按顺序排列的所有字符列表
    - char_to_line: 每个字符索引对应的行索引
    - lines: 原始时间戳行列表
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    all_lines = []
    chars = []
    char_to_line = []  # 字符索引 -> 行索引

    for line_idx, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith("="):
            continue

        if line.startswith("[") and "] " in line:
            all_lines.append(line)
            content = line.split("] ", 1)[1]
            for char in content:
                if char.strip():
                    chars.append(char)
                    char_to_line.append(len(all_lines) - 1)  # 记录这行是第几行

    return chars, char_to_line, all_lines


def sliding_window_match(cleaned_chars, timestamps_chars):
    """
    滑动窗口匹配法：
    - cleaned_chars: GPT清理后的字符列表
    - timestamps_chars: 时间戳中的原始字符列表
    返回：要保留的 timestamps 字符索引列表
    """
    if len(cleaned_chars) == 0:
        return []

    result = []  # 保留的 timestamps 索引
    i = 0  # cleaned 指针
    j = 0  # timestamps 指针

    while i < len(cleaned_chars):
        # 尝试在 timestamps[j:] 中找到 cleaned[i:] 能匹配的位置
        best_match_pos = -1
        best_match_len = 0

        # 限制搜索范围
        search_limit = min(j + 500, len(timestamps_chars))

        for pos in range(j, search_limit):
            # 检查 cleaned[i:] 是否能在 timestamps[pos:] 中完全匹配
            match_len = 0
            max_check = min(len(cleaned_chars) - i, len(timestamps_chars) - pos, 100)

            for k in range(max_check):
                if cleaned_chars[i + k] == timestamps_chars[pos + k]:
                    match_len += 1
                else:
                    break

            if match_len > best_match_len:
                best_match_len = match_len
                best_match_pos = pos

            if best_match_len == len(cleaned_chars) - i:
                break

        if best_match_pos > j and best_match_len > 0:
            # 找到更好的匹配位置，跳过中间的 timestamps 字符（删除）
            j = best_match_pos

        # 现在 timestamps[j] 应该匹配 cleaned[i]
        if j < len(timestamps_chars) and timestamps_chars[j] == cleaned_chars[i]:
            result.append(j)
            i += 1
            j += 1
        else:
            print(f"警告: cleaned[{i}]='{cleaned_chars[i]}' 在 timestamps 中找不到匹配")
            i += 1

    return result


def build_cleaned_timestamp_lines(kept_indices, char_to_line, original_lines):
    """
    根据保留的字符索引，构建清理后的时间戳行
    - kept_indices: 保留的字符在 timestamps 中的索引
    - char_to_line: 每个字符索引对应的行索引
    - original_lines: 原始时间戳行列表
    """
    # 找出需要保留的行索引（去重，保持顺序）
    kept_lines_set = set()
    for char_idx in kept_indices:
        if char_idx < len(char_to_line):
            kept_lines_set.add(char_to_line[char_idx])

    kept_lines = sorted(kept_lines_set)
    return [original_lines[line_idx] for line_idx in kept_lines]


def save_output_files(cleaned_text, cleaned_timestamps):
    # 保存演讲稿文本1.txt
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)
    print(f"已保存: {output_txt_path}")

    # 保存时间戳1.txt
    header = "==================================================\n说话内容时间戳\n==================================================\n"
    content = header + "\n".join(cleaned_timestamps) + "\n"

    with open(output_timestamps_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"已保存: {output_timestamps_path}")


def main():
    # 1. 解析时间戳文件
    timestamps_chars, char_to_line, timestamp_lines = parse_timestamps(timestamps_file_path)
    print(f"时间戳字符数: {len(timestamps_chars)}")
    print(f"时间戳行数: {len(timestamp_lines)}")

    # 0. 如果演讲稿文本.txt不存在，从timestamps.txt生成
    if not os.path.exists(txt_file_path):
        print(f"演讲稿文本.txt 不存在，正在从 timestamps.txt 生成...")
        # 从时间戳提取纯文本
        raw_text_from_ts = "".join(timestamps_chars)
        with open(txt_file_path, "w", encoding="utf-8") as f:
            f.write(raw_text_from_ts)
        print(f"已生成: {txt_file_path} ({len(raw_text_from_ts)} 字)")
        raw_text_clean = raw_text_from_ts
    else:
        # 2. 读取演讲稿文本
        with open(txt_file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # 清理演讲稿文本（去除标题栏等）
        raw_text_clean = raw_text.split("==================================================")[-1].strip()

    # 验证
    print(f"\n演讲稿文本长度: {len(raw_text_clean)}")
    print(f"时间戳字符数: {len(timestamps_chars)}")

    # 3. 调用 GPT 处理
    print("\n正在调用 GPT 处理...")
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": raw_text_clean}
        ],
    )

    cleaned_text = response.choices[0].message.content.strip()
    cleaned_chars = list(cleaned_text)
    print(f"\nGPT清理后字符数: {len(cleaned_chars)}")

    if cleaned_text == raw_text_clean:
        print("无需删减，文本相同")
        save_output_files(cleaned_text, timestamp_lines)
        return

    # 4. 滑动窗口匹配
    print("\n正在进行滑动窗口匹配...")
    kept_indices = sliding_window_match(cleaned_chars, timestamps_chars)
    print(f"保留的字符数: {len(kept_indices)}")

    # 5. 重新构建时间戳行
    cleaned_timestamps = build_cleaned_timestamp_lines(kept_indices, char_to_line, timestamp_lines)
    print(f"保留的时间戳行数: {len(cleaned_timestamps)}")

    # 6. 验证
    reconstructed = ""
    for line in cleaned_timestamps:
        content = line.split("] ", 1)[1]
        reconstructed += content

    print(f"\n重建文本长度: {len(reconstructed)}")
    print(f"GPT清理文本长度: {len(cleaned_text)}")

    if reconstructed == cleaned_text:
        print("✓ 匹配成功！")
    else:
        print("✗ 匹配失败，显示差异:")
        for idx, (c1, c2) in enumerate(zip(reconstructed, cleaned_text)):
            if c1 != c2:
                print(f"  位置 {idx}: 重建='{c1}', GPT='{c2}'")
                print(f"  前后各5字: 重建='{reconstructed[max(0,idx-5):idx+5]}', GPT='{cleaned_text[max(0,idx-5):idx+5]}'")
                break

    # 7. 保存输出
    save_output_files(cleaned_text, cleaned_timestamps)

    print("\n处理完成！")


if __name__ == "__main__":
    main()
