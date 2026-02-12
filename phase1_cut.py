"""
第一阶段：传统方法裁剪时间戳文本
功能：
1. 读取 timestamps.txt 和演讲稿文本.txt
2. 识别所有"重来"指令（连续挨着的取最后一个）
3. 计算每个指令对应的删除区间
4. 从时间戳文本中抹掉这些区间
5. 输出 timestamps_1.txt 和 演讲稿文本1.txt
"""

import os
import re


def parse_timestamps(txt_path):
    """解析时间戳文件"""
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    words = []
    for line_idx, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith('='):
            continue

        match = re.match(r'\[([\d.]+)s - ([\d.]+)s\]\s*(.+)', line)
        if match:
            start = float(match.group(1))
            end = float(match.group(2))
            word = match.group(3)
            words.append({
                'word': word,
                'start': start,
                'end': end,
                'line_index': line_idx
            })

    return lines, words


def parse_script(script_path):
    """读取演讲稿文本"""
    if not os.path.exists(script_path):
        return None
    with open(script_path, 'r', encoding='utf-8') as f:
        return f.read()


def find_chonglai_groups(words):
    """
    找出所有"重来"的位置，并合并连续的"重来"

    例如：如果有"重来重来重来"，算作一组，处理最后一个

    Returns:
        chonglai_groups: 每组"重来"的信息，{'index': n, 'start_idx':, 'end_idx':}
    """
    chonglai_groups = []
    group_index = 0
    i = 0

    while i < len(words) - 1:
        if words[i]['word'] == '重' and words[i + 1]['word'] == '来':
            # 找到一个"重来"，继续往后检查是否还有连续的
            group_start = i
            j = i

            # 跳过连续的"重来"
            while j < len(words) - 1 and words[j]['word'] == '重' and words[j + 1]['word'] == '来':
                j += 2  # 跳过"重来"两个字

            group_end = j - 2  # 最后一个"重来"的"重"字位置
            last_lai_idx = group_end + 1  # 最后一个"重来"的"来"字位置

            group_index += 1
            chonglai_groups.append({
                'index': group_index,
                'start_idx': group_start,     # 第一个"重来"的"重"字索引
                'end_idx': last_lai_idx,      # 最后一个"重来"的"来"字索引
                'start_time': words[group_start]['start'],
                'end_time': words[last_lai_idx]['end']
            })

            i = j
        else:
            i += 1

    return chonglai_groups


def is_instruction(chonglai_group, words, prev_group_end_idx=None):
    """
    判断某个"重来"组是否是剪辑指令

    规则1：取"重来"后面2个字，往前找（精确匹配）
    规则2：取"重来"后面3个字，往前找（滑动窗口，2个以上连续匹配）
    优先匹配3个字，再匹配2个字

    Args:
        chonglai_group: "重来"组信息
        words: 字列表
        prev_group_end_idx: 前一个"重来"组的结束索引（用于限定搜索范围）

    Returns:
        (bool, match_idx, match_info): (是否指令, 匹配位置, 匹配信息)
    """
    last_lai_idx = chonglai_group['end_idx']  # 最后一个"重来"的"来"字索引

    # 确定往前找的范围
    search_start = last_lai_idx - 1
    search_end = (prev_group_end_idx + 1) if prev_group_end_idx is not None else 0

    # 先尝试规则2（3个字，滑动窗口）
    if last_lai_idx + 3 < len(words):
        target_words = [words[last_lai_idx + 1]['word'], words[last_lai_idx + 2]['word'], words[last_lai_idx + 3]['word']]

        # 滑动窗口查找
        # 窗口左边界从 search_start 开始，右边界是 last_lai_idx - 1
        left = search_start
        while left >= search_end:
            # 窗口内的3个字
            window_words = [words[left]['word'], words[left + 1]['word'], words[left + 2]['word']]

            # 统计匹配情况：内容相同 AND 位置相同
            match_count = 0
            for i in range(3):
                if window_words[i] == target_words[i]:
                    match_count += 1

            # 如果有2个以上（含）匹配
            if match_count >= 2:
                match_detail = {
                    'matched_words': ''.join(target_words),
                    'match_count': match_count
                }
                return True, left, match_detail

            # 窗口左移1位
            left -= 1

    # 再尝试规则1（2个字，精确匹配）
    if last_lai_idx + 2 < len(words):
        word_a = words[last_lai_idx + 1]['word']
        word_b = words[last_lai_idx + 2]['word']

        for i in range(search_start, search_end - 1, -1):
            if i + 1 < len(words):
                if words[i]['word'] == word_a and words[i + 1]['word'] == word_b:
                    match_detail = {
                        'matched_words': f"{word_a}{word_b}",
                        'match_count': 2
                    }
                    return True, i, match_detail

    return False, None, None


def cut_timestamps(words, instruction_ranges):
    """
    根据指令区间裁剪时间戳

    Args:
        words: 字列表
        instruction_ranges: 指令区间列表 [{'start_idx':, 'end_idx':, 'start_time':, 'end_time':}]

    Returns:
        remaining_words: 保留的字列表
    """
    if not instruction_ranges:
        return words[:], []

    # 按 start_idx 从大到小排序，这样删除时不会影响前面的索引
    sorted_ranges = sorted(instruction_ranges, key=lambda x: x['start_idx'], reverse=True)

    # 标记要删除的索引
    to_remove = set()
    removed_info = []

    for r in sorted_ranges:
        # 删除从 start_idx 到 end_idx 的所有字
        for idx in range(r['start_idx'], r['end_idx'] + 1):
            if idx < len(words):
                to_remove.add(idx)
        removed_info.append({
            'word_a': words[r['start_idx'] - 2]['word'] if r['start_idx'] >= 2 else '',
            'word_b': words[r['start_idx'] - 1]['word'] if r['start_idx'] >= 1 else '',
            'start_time': r['start_time'],
            'end_time': r['end_time']
        })

    # 保留不在删除集合中的字
    remaining_words = [w for idx, w in enumerate(words) if idx not in to_remove]

    return remaining_words, removed_info


def assemble_script(words):
    """把离散的字拼成连续的演讲稿"""
    return ''.join(w['word'] for w in words)


def generate_marked_script(words, instruction_ranges):
    """
    生成标记后的演讲稿
    被删除的部分用【删除：xxx...xxx】标注
    """
    if not instruction_ranges:
        return assemble_script(words)

    # 按索引从大到小排序
    sorted_ranges = sorted(instruction_ranges, key=lambda x: x['start_idx'], reverse=True)

    # 标记要删除的部分
    script_chars = []
    current_idx = 0

    for r in sorted_ranges:
        # 添加删除区间前面的字
        for i in range(current_idx, r['start_idx']):
            script_chars.append(words[i]['word'])

        # 获取被删除的内容
        deleted_content = ''.join(words[i]['word'] for i in range(r['start_idx'], r['end_idx'] + 1))
        script_chars.append(f"【删除：{deleted_content}】")

        current_idx = r['end_idx'] + 1

    # 添加剩余的字
    for i in range(current_idx, len(words)):
        script_chars.append(words[i]['word'])

    return ''.join(script_chars)


def phase1_process(timestamps_path, script_path, output_prefix='1'):
    """
    第一阶段处理

    Args:
        timestamps_path: 时间戳文件路径
        script_path: 演讲稿文件路径
        output_prefix: 输出文件序号（如 '1'）

    Returns:
        instruction_ranges: 识别出的指令区间
    """
    print("=" * 50)
    print("第一阶段：传统方法裁剪")
    print("=" * 50)

    # 1. 读取文件
    print("\n[1/5] 正在读取文件...")
    lines, words = parse_timestamps(timestamps_path)
    original_script = parse_script(script_path)
    print(f"      时间戳：{len(words)} 个字")
    print(f"      演讲稿：{len(original_script)} 个字符")

    # 2. 找出所有"重来"组
    print("\n[2/5] 正在查找'重来'...")
    chonglai_groups = find_chonglai_groups(words)
    print(f"      共有 {len(chonglai_groups)} 个'重来'组")

    # 3. 判断每个组是否是剪辑指令
    print("\n[3/5] 正在分析剪辑指令...")
    instruction_ranges = []
    prev_end_idx = None

    for i, group in enumerate(chonglai_groups):
        is_inst, match_idx, match_info = is_instruction(group, words, prev_end_idx)

        if is_inst:
            match_words = match_info['matched_words']
            num_chars = len(match_words)

            instruction_ranges.append({
                'index': group['index'],
                'start_idx': match_idx,       # 滑动窗口左边界（要删除的起点）
                'end_idx': group['end_idx'],   # 最后那个"重来"的"来"字索引
                'start_time': words[match_idx]['start'],
                'end_time': group['end_time'],
                'match_words': match_words,
                'num_chars': num_chars
            })
            print(f"      [重来{group['index']}] -> 是指令（匹配{num_chars}字），删除区间 [{words[match_idx]['start']:.2f}s - {group['end_time']:.2f}s]")
            print(f"             匹配：'{match_words}'")

            prev_end_idx = group['end_idx']
        else:
            print(f"      [重来{group['index']}] -> 不是指令（演讲内容）")

    print(f"\n      共识别到 {len(instruction_ranges)} 个剪辑指令")

    # 4. 裁剪时间戳
    print("\n[4/5] 正在裁剪时间戳...")
    remaining_words, removed_info = cut_timestamps(words, instruction_ranges)
    print(f"      原始：{len(words)} 字 -> 裁剪后：{remaining_words} 字")

    # 5. 生成输出文件
    print("\n[5/5] 正在生成输出文件...")

    # 生成 timestamps_1.txt
    timestamps_1_path = f"timestamps_{output_prefix}.txt"
    with open(timestamps_1_path, 'w', encoding='utf-8') as f:
        f.write("=" * 50 + "\n")
        f.write(f"时间戳文本（第一阶段裁剪后）\n")
        f.write("=" * 50 + "\n\n")
        for w in remaining_words:
            f.write(f"[{w['start']:.2f}s - {w['end']:.2f}s] {w['word']}\n")
    print(f"      -> {timestamps_1_path}")

    # 生成 演讲稿文本1.txt（基于 timestamps_1.txt 的内容整理）
    script_1_path = f"演讲稿文本{output_prefix}.txt"
    clean_script = assemble_script(remaining_words)
    with open(script_1_path, 'w', encoding='utf-8') as f:
        f.write("=" * 50 + "\n")
        f.write(f"演讲稿文本（第一阶段裁剪后）\n")
        f.write("=" * 50 + "\n\n")
        f.write(clean_script + "\n")
    print(f"      -> {script_1_path}")

    # 生成 cut_segments.txt（被剪去的时间段，供 edit_video.py 使用）
    cut_segments_path = "cut_segments.txt"
    with open(cut_segments_path, 'w', encoding='utf-8') as f:
        f.write("=" * 50 + "\n")
        f.write(f"被剪去的时间段\n")
        f.write("=" * 50 + "\n\n")
        for r in instruction_ranges:
            f.write(f"[{r['start_time']:.2f}s - {r['end_time']:.2f}s]\n")
    print(f"      -> {cut_segments_path}")

    # 打印被删除的内容
    print("\n----- 被删除的内容 -----")
    for r in instruction_ranges:
        print(f"  [{r['start_time']:.2f}s - {r['end_time']:.2f}s]: 匹配'{r['match_words']}'")
    print("-" * 50)

    return instruction_ranges


def main():
    """运行第一阶段处理"""
    # 配置
    TIMESTAMPS_TXT = r"F:\pycharm\pycharm\视频剪辑\timestamps.txt"
    SCRIPT_TXT = r"F:\pycharm\pycharm\视频剪辑\演讲稿文本.txt"

    # 如果没有演讲稿文本.txt，从 timestamps.txt 生成
    if not os.path.exists(SCRIPT_TXT):
        print("\n未找到 演讲稿文本.txt，正在从 timestamps.txt 生成...")
        lines, words = parse_timestamps(TIMESTAMPS_TXT)
        script_content = assemble_script(words)
        with open(SCRIPT_TXT, 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("演讲稿文本\n")
            f.write("=" * 50 + "\n\n")
            f.write(script_content)
        print(f"已生成: {SCRIPT_TXT}")

    # 执行第一阶段
    instruction_ranges = phase1_process(TIMESTAMPS_TXT, SCRIPT_TXT, output_prefix='1')

    print("\n" + "=" * 50)
    print("第一阶段完成！")
    print(f"共识别 {len(instruction_ranges)} 个剪辑指令")
    print("=" * 50)


if __name__ == "__main__":
    main()
