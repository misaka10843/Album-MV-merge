import librosa
import numpy as np


def find_first_sound_start(audio_path, silence_duration=0.5, min_sound_duration=0.1, threshold_multiplier=2.0):
    """
    查找音频文件中第一个有效声音的起始时间。

    参数:
        audio_path (str): 音频文件路径
        silence_duration (float): 用于计算背景噪音的静音段时长（秒），默认为0.5秒
        min_sound_duration (float): 最小有效声音持续时间（秒），默认为0.1秒
        threshold_multiplier (float): 噪音阈值的倍数，默认为2.0

    返回:
        float: 有效声音的起始时间（秒）
    """
    # 加载音频文件，转换为单声道
    audio, sr = librosa.load(audio_path, sr=None, mono=True)

    # 计算用于背景噪音分析的样本数
    silence_samples = int(sr * silence_duration)
    if silence_samples <= 0:
        silence_samples = 1
    if silence_samples > len(audio):
        raise ValueError("音频长度小于指定的静音时长")

    # 提取静音段并计算背景噪音的RMS
    silence_segment = audio[:silence_samples]
    rms_silence = np.sqrt(np.mean(silence_segment ** 2))

    # 设置声音检测阈值（防止完全静音时阈值为0）
    threshold = max(threshold_multiplier * rms_silence, 0.005)  # 最小阈值设为0.005

    # 计算每个样本的平方能量
    squared_audio = audio ** 2

    # 创建滑动窗口（计算连续有效声音的最小样本数）
    min_samples = int(sr * min_sound_duration)
    window = np.ones(min_samples) / min_samples

    # 计算滑动窗口的平均能量
    moving_avg = np.convolve(squared_audio, window, mode='full')[:len(squared_audio)]

    # 找到第一个超过阈值的窗口位置
    above_threshold = moving_avg > threshold ** 2
    start_index = np.argmax(above_threshold)

    # 转换为时间（秒）
    return start_index / sr if np.any(above_threshold) else 0.0


# 示例用法
start_time = find_first_sound_start("assets/(18) [senya] 華鳥風月.flac")
print(f"有效声音起始时间: {start_time:.3f}秒")