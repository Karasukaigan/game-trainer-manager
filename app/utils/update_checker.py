"""
更新检查模块 — 通过 HEAD 请求比对本地修改器与 FLiNG 最新版本。
零爬虫：仅发送一个 HEAD 请求，从 Content-Disposition 响应头提取版本号。
"""
import re
import os
import requests
from typing import Optional, Tuple, List, Dict
from difflib import SequenceMatcher


# ── 版本号提取与解析 ──────────────────────────────────────────────

_VERSION_PATTERN = re.compile(
    r'v(\d[\d\.]*(?:-v?\d[\d\.]*)?)',
    re.IGNORECASE
)


def _parse_version_segment(segment: str) -> Tuple[int, ...]:
    """将 '2.13' 解析为 (2, 13)，'1.0.811' 解析为 (1, 0, 811)"""
    parts = segment.strip().lstrip('v').replace('-', '.').split('.')
    return tuple(int(p) for p in parts if p.isdigit())


def extract_version_tuple(filename: str) -> Optional[Tuple[int, ...]]:
    """
    从修改器文件名中提取版本号元组。
    
    'Cyberpunk 2077 v2.0-v2.13 Plus 46 Trainer.exe' → (2, 13)
    'Easy Red 2 v1.5.1-v1.5.6 Plus 14 Trainer.exe'    → (1, 5, 6)
    'GTA V Enhanced v1.0.811 Plus 22 Trainer.exe'      → (1, 0, 811)
    
    对于范围格式 vA-vB，取最新值 B。
    """
    match = _VERSION_PATTERN.search(filename)
    if not match:
        return None

    raw = match.group(1)
    if '-' in raw:
        parts = raw.split('-')
        right = parts[-1].lstrip('v')
        return _parse_version_segment(right)
    return _parse_version_segment(raw)


def is_newer(local: Tuple[int, ...], remote: Tuple[int, ...]) -> bool:
    """版本比较：remote > local 返回 True"""
    max_len = max(len(local), len(remote))
    a = local + (0,) * (max_len - len(local))
    b = remote + (0,) * (max_len - len(remote))
    return b > a


# ── 游戏名提取与匹配 ──────────────────────────────────────────────

_TRAINER_SUFFIX_PATTERN = re.compile(
    r'( v\d[\d\.\-]*.* Trainer.*$)|'
    r'( Plus \d+ Trainer.*$)|'
    r'( Early Access Plus \d+ Trainer.*$)|'
    r'( Build \d[\d\.\-]*.* Trainer.*$)|'
    r'( \(.*?\) v\d[\d\.\-]*.* Trainer.*$)|'
    r'( Update \d[\d\-]*.* Trainer.*$)|'
    r'( \(Update \d+.*?\) Plus \d+ Trainer.*$)|'
    r'( v[\d\.\-]+.*$)|'
    r'( [\d\.\-]+-Update \d+.*? Trainer.*$)',
    re.IGNORECASE
)


def extract_game_name(filename: str) -> str:
    """从文件名中去除版本号和 Trainer 后缀，提取纯游戏名"""
    base = os.path.splitext(os.path.basename(filename))[0]
    return _TRAINER_SUFFIX_PATTERN.sub('', base).strip()


def match_csv_entry(game_name: str, trainers_data: List[Dict], threshold: float = 0.8) -> Optional[Dict]:
    """
    用游戏名在 trainers_data 中模糊匹配。
    """
    best = None
    best_sim = 0.0
    gn = game_name.lower().replace(':', '')

    for entry in trainers_data:
        csv_name = entry.get('game_name', '').lower().replace(':', '')
        sim = SequenceMatcher(None, gn, csv_name).ratio()
        if sim > best_sim:
            best_sim = sim
            best = entry

    if best_sim >= threshold:
        return best
    return None


# ── 更新检查 ──────────────────────────────────────────────────────

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    )
}

TIMEOUT = 8


def check_trainer_update(
    local_path: str,
    trainers_data: List[Dict],
) -> Optional[Dict]:
    """
    检查单个修改器是否有更新。
    
    返回:
        dict  — {
            'local_path', 'local_name', 'local_version',
            'remote_version', 'has_update', 'download_url',
            'trainer_url', 'game_name', 'error'
        }
    """
    local_name = os.path.basename(local_path)
    local_version_tuple = extract_version_tuple(local_name)

    game_name = extract_game_name(local_name)
    entry = match_csv_entry(game_name, trainers_data)
    if entry is None:
        return {
            'local_path': local_path,
            'local_name': local_name,
            'local_version': _fmt_version(local_version_tuple),
            'remote_version': '?',
            'has_update': False,
            'download_url': '',
            'trainer_url': '',
            'game_name': game_name,
            'error': '未在修改器列表中匹配到对应游戏',
        }

    download_url = entry.get('download_url', '')
    if not download_url:
        return {
            'local_path': local_path,
            'local_name': local_name,
            'local_version': _fmt_version(local_version_tuple),
            'remote_version': '?',
            'has_update': False,
            'download_url': '',
            'trainer_url': entry.get('trainer_url', ''),
            'game_name': entry.get('game_name', ''),
            'error': 'CSV 中无下载链接',
        }

    try:
        resp = requests.head(download_url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        cd = resp.headers.get('Content-Disposition', '')
        filename_match = re.search(r'filename[^;=\n]*=["\']?([^"\'\n;]+)', cd, re.IGNORECASE)
        if not filename_match:
            return {
                'local_path': local_path,
                'local_name': local_name,
                'local_version': _fmt_version(local_version_tuple),
                'remote_version': '?',
                'has_update': False,
                'download_url': download_url,
                'trainer_url': entry.get('trainer_url', ''),
                'game_name': entry.get('game_name', ''),
                'error': '无法从响应头中提取版本信息',
            }

        remote_name = filename_match.group(1).strip().strip('"\'')
        remote_version_tuple = extract_version_tuple(remote_name)

        has_update = False
        if local_version_tuple is not None and remote_version_tuple is not None:
            has_update = is_newer(local_version_tuple, remote_version_tuple)

        return {
            'local_path': local_path,
            'local_name': local_name,
            'local_version': _fmt_version(local_version_tuple),
            'remote_version': _fmt_version(remote_version_tuple),
            'has_update': has_update,
            'download_url': download_url,
            'trainer_url': entry.get('trainer_url', ''),
            'game_name': entry.get('game_name', ''),
            'error': None,
        }

    except requests.RequestException as e:
        return {
            'local_path': local_path,
            'local_name': local_name,
            'local_version': _fmt_version(local_version_tuple),
            'remote_version': '?',
            'has_update': False,
            'download_url': download_url,
            'trainer_url': entry.get('trainer_url', ''),
            'game_name': entry.get('game_name', ''),
            'error': f'网络请求失败: {e}',
        }


def _fmt_version(v: Optional[Tuple[int, ...]]) -> str:
    if v is None:
        return '未知'
    return 'v' + '.'.join(str(n) for n in v)


def check_all_trainers(
    local_trainers: List[str],
    trainers_data: List[Dict],
    progress_callback=None,
) -> List[Dict]:
    """
    批量检查所有本地修改器。
    progress_callback(idx, total, result) — 每检查完一个调用
    """
    results = []
    total = len(local_trainers)
    for i, path in enumerate(local_trainers):
        result = check_trainer_update(path, trainers_data)
        results.append(result)
        if progress_callback:
            progress_callback(i + 1, total, result)
    return results
