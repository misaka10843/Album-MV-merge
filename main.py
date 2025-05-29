import subprocess
import librosa
import numpy as np
import os
import shutil

# 常量定义
SILENCE_DURATION = 0.5
MIN_SOUND_DURATION = 0.1
THRESHOLD_MULTIPLIER = 2.0
TARGET_SAMPLE_RATE = 48000


def get_audio_info(audio_path):
    """获取音频文件信息"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'a:0',
        '-show_entries', 'stream=codec_name,sample_rate,bit_rate',
        '-of', 'default=nw=1:nk=1',
        audio_path
    ]
    try:
        output = subprocess.check_output(cmd, text=True).strip().split('\n')
        return {
            'codec': output[0],
            'sample_rate': int(output[1]),
            'bit_rate': int(output[2]) if len(output) > 2 and output[2] != 'N/A' else None
        }
    except Exception as e:
        raise ValueError(f"无法获取音频信息: {str(e)}")


def extract_video_audio(video_path, output_path):
    """提取视频中的音频轨道"""
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le',
        '-ar', str(TARGET_SAMPLE_RATE),
        '-ac', '2',
        output_path
    ]
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


def convert_to_flac(input_path, output_path):
    """转换为FLAC格式并确保采样率"""
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-ar', str(TARGET_SAMPLE_RATE),
        '-c:a', 'flac',
        '-compression_level', '12',
        output_path
    ]
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


def find_first_sound_start(audio_path):
    """检测音频首次出现声音的时间点"""
    audio, sr = librosa.load(audio_path, sr=None, mono=True)

    # 静音段分析
    silence_samples = int(sr * SILENCE_DURATION)
    if silence_samples > len(audio):
        return 0.0

    # 计算背景噪声阈值
    silence_segment = audio[:silence_samples]
    rms_silence = np.sqrt(np.mean(silence_segment ** 2))
    threshold = max(THRESHOLD_MULTIPLIER * rms_silence, 0.005)

    # 滑动窗口检测
    min_samples = int(sr * MIN_SOUND_DURATION)
    window = np.ones(min_samples) / min_samples
    moving_avg = np.convolve(audio ** 2, window, 'full')[:len(audio)]

    # 找到第一个超过阈值的连续窗口
    above_threshold = moving_avg > threshold ** 2
    for i in range(len(above_threshold) - min_samples):
        if np.all(above_threshold[i:i + min_samples]):
            return max(0, i - min_samples) / sr

    return 0.0


def align_audio(a_ref_path, b_path, output_path):
    """对齐两个音频的起始时间"""
    a_start = find_first_sound_start(a_ref_path)
    b_start = find_first_sound_start(b_path)
    delta = b_start - a_start
    print(f"\t视频音频头部空白时长：{a_start:.4f}秒\n"
          f"\t替换音频头部空白时长：{b_start:.4f}秒\n"
          f"\t总差：{delta:.4f}秒\n")
    if abs(delta) <= 0.03:
        shutil.copyfile(b_path, output_path)
        return

    # 需要时间对齐
    if delta > 0:
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(delta),
            '-i', b_path,
            '-c:a', 'copy',
            output_path
        ]
    else:
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'anullsrc=cl=stereo:r={TARGET_SAMPLE_RATE}:d={abs(delta)}',
            '-i', b_path,
            '-filter_complex', '[0][1]concat=n=2:v=0:a=1',
            '-c:a', 'flac',
            output_path
        ]
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)


def replace_video_audio(video_path, audio_path, output_path):
    """使用MKVToolnix替换音频轨道"""
    cmd = [
        'mkvmerge', '-o', output_path,
        '--audio-tracks', '0',
        '--language', '0:und',
        video_path,
        audio_path
    ]
    subprocess.run(cmd, check=True)


def main_process(video_path, audio_b_path, output_path):
    # 临时文件定义
    temp_dir = 'temp_audio'
    os.makedirs(temp_dir, exist_ok=True)

    try:
        print("提取视频音频")
        a_path = os.path.join(temp_dir, 'a.wav')
        extract_video_audio(video_path, a_path)

        print("获取音频信息")
        a_info = get_audio_info(a_path)
        b_info = get_audio_info(audio_b_path)

        print("音质比较逻辑")
        quality_better = False
        if b_info['codec'] == 'flac' and a_info['codec'] != 'flac':
            quality_better = True
        elif b_info['codec'] == a_info['codec']:
            quality_better = (b_info.get('bit_rate', 0) or 0) > (a_info.get('bit_rate', 0) or 0)

        if not quality_better:
            print("音质b不优于a，终止处理")
            return

        print("转换音频格式")
        b_flac_path = os.path.join(temp_dir, 'b.flac')
        if b_info['codec'] != 'flac' or b_info['sample_rate'] != TARGET_SAMPLE_RATE:
            convert_to_flac(audio_b_path, b_flac_path)
        else:
            shutil.copyfile(audio_b_path, b_flac_path)

        print("时间对齐处理")
        aligned_b_path = os.path.join(temp_dir, 'b_aligned.flac')
        align_audio(a_path, b_flac_path, aligned_b_path)

        print("替换视频音频")
        replace_video_audio(video_path, aligned_b_path, output_path)
        print(f"处理完成，输出文件: {output_path}")

    finally:
        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)


# 使用示例
if __name__ == "__main__":
    main_process(
        video_path="assets/華鳥風月 [gXCI8vJTjqA].webm",
        audio_b_path="assets/(18) [senya] 華鳥風月.flac",
        output_path="output_video.mkv"
    )