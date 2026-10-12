# graph_config.py
# matplotlib 공통 그래프 설정

import matplotlib.pyplot as plt
import platform

def set_graph(wi=10, hi=8, fs=12):
    # 한글 폰트 설정
    if platform.system() == 'Windows':
        plt.rcParams['font.family'] = 'Malgun Gothic'
    elif platform.system() == 'Darwin':
        plt.rcParams['font.family'] = 'AppleGothic'
    else:
        plt.rcParams['font.family'] = 'NanumGothic'
    # 마이너스 기호 깨짐 방지
    plt.rcParams['axes.unicode_minus'] = False
    # 기본 그래프 크기
    plt.rcParams['figure.figsize'] = (wi, hi)
    # 기본 글꼴 크기
    plt.rcParams['font.size'] = fs