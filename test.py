import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, Frame
import requests
import threading
import time
import matplotlib
import numpy as np
import datetime
import json
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon, Circle, Patch, Rectangle
from matplotlib.collections import PatchCollection
from matplotlib.offsetbox import AnchoredText
from matplotlib.text import Text
import config
from matplotlib.transforms import Affine2D
import math
from collections import defaultdict

matplotlib.use('TkAgg')

# Конфигурация
BASE_URL = 'https://games-test.datsteam.dev/api'
HEADERS = {'accept': 'application/json', 'X-Auth-Token': config.TOKEN}

# Цвета для типов гексов (обновлено по правилам игры)
HEX_COLORS = {
    0: '#F0F0F0',  # Пустой
    1: '#D2B48C',  # Грязь
    2: '#A9A9A9',  # Камень
    3: '#32CD32',  # Кислота
    4: '#FF4500',  # Муравейник
}

# Цвета для типов муравьев
ANT_COLORS = {
    0: '#4CAF50',  # Рабочий
    1: '#2196F3',  # Солдат
    2: '#9C27B0',  # Разведчик
}

# Цвета для вражеских муравьев
ENEMY_COLORS = {
    0: '#FF5252',  # Рабочий
    1: '#FF4081',  # Солдат
    2: '#7C4DFF',  # Разведчик
}

# Цвета для ресурсов
FOOD_COLORS = {
    0: '#FFD700',  # Нектар
    1: '#FF6347',  # Падь
    2: '#8B4513',  # Семена
}

# Типы муравьев
ANT_TYPES = {
    0: "Рабочий",
    1: "Солдат",
    2: "Разведчик"
}

# Типы ресурсов
FOOD_TYPES = {
    0: "Нектар",
    1: "Падь",
    2: "Семена"
}

# Типы гексов
HEX_TYPES = {
    0: "Пустой",
    1: "Грязь",
    2: "Камень",
    3: "Кислота",
    4: "Муравейник"
}


class HexMapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DatsPulse Ants Commander")
        self.root.geometry("1800x1000")
        self.root.state('zoomed')

        # Переменные состояния
        self.selected_ant = None
        self.path_points = []
        self.last_update = "Не обновлялось"
        self.base_hex_size = 0.5
        self.zoom_level = 1.0
        self.pan_offset = [0, 0]
        self.map_center = [0, 0]
        self.last_log_update = 0
        self.server_response = "Ожидание действий..."
        self.game_data = {
            'ants': [],
            'enemies': [],
            'food': [],
            'home': [],
            'map': [],
            'score': 0,
            'turnNo': 0,
            'nextTurnIn': 0,
            'spot': {'q': 0, 'r': 0}
        }
        self.logs = []
        self.history_paths = {}
        self.colony_stats = {
            'worker_count': 0,
            'soldier_count': 0,
            'scout_count': 0,
            'total_food': 0,
            'nectar': 0,
            'aphid': 0,
            'seeds': 0,
            'ant_hill_health': 100
        }

        # Основные фреймы
        self.top_frame = ttk.Frame(root, padding=10)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)

        self.left_frame = ttk.Frame(root, width=350)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.center_frame = ttk.Frame(root)
        self.center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.right_frame = ttk.Frame(root, width=350)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        # Инициализация компонентов
        self.init_top_panel()
        self.init_left_panel()
        self.init_center_panel()
        self.init_right_panel()
        self.init_status_bar()

        # Старт потока обновления данных
        self.update_thread = threading.Thread(target=self.update_game_data, daemon=True)
        self.update_thread.start()

    def init_top_panel(self):
        """Инициализация верхней панели"""
        # Информация о ходе
        turn_frame = ttk.LabelFrame(self.top_frame, text="Ход игры", padding=10)
        turn_frame.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=5, expand=True)

        self.turn_var = tk.StringVar()
        self.turn_var.set("Ожидание данных...")
        ttk.Label(turn_frame, textvariable=self.turn_var, font=("Arial", 12)).pack(anchor=tk.W)

        # Информация о счете
        score_frame = ttk.LabelFrame(self.top_frame, text="Счет команды", padding=10)
        score_frame.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=5)

        self.score_var = tk.StringVar()
        self.score_var.set("0")
        ttk.Label(score_frame, textvariable=self.score_var, font=("Arial", 14, "bold")).pack()

        # Кнопка регистрации
        reg_frame = ttk.Frame(self.top_frame)
        reg_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        ttk.Button(reg_frame, text="Зарегистрироваться", command=self.register,
                   style="Accent.TButton").pack(fill=tk.X, pady=5)
        ttk.Button(reg_frame, text="Обновить данные", command=self.manual_update,
                   style="Secondary.TButton").pack(fill=tk.X)

    def init_left_panel(self):
        """Инициализация левой панели (управление и информация)"""
        # Информационная панель
        info_frame = ttk.LabelFrame(self.left_frame, text="Детали муравья", padding=10)
        info_frame.pack(fill=tk.X, pady=5)

        self.info_text = tk.Text(info_frame, height=10, width=30, font=("Arial", 10))
        self.info_text.pack(fill=tk.X)
        self.info_text.insert(tk.END, "Кликните на муравья для просмотра информации")
        self.info_text.config(state=tk.DISABLED)

        # Управление муравьями
        move_frame = ttk.LabelFrame(self.left_frame, text="Управление движением", padding=10)
        move_frame.pack(fill=tk.X, pady=5)

        ttk.Label(move_frame, text="Выбранный муравей:").pack(anchor=tk.W)
        self.selected_ant_label = ttk.Label(move_frame, text="Никто не выбран", font=("Arial", 9))
        self.selected_ant_label.pack(fill=tk.X, pady=2)

        ttk.Label(move_frame, text="Путь движения:").pack(anchor=tk.W)
        self.path_label = ttk.Label(move_frame, text="Не задан", font=("Arial", 9))
        self.path_label.pack(fill=tk.X, pady=2)

        btn_frame = ttk.Frame(move_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Очистить путь", command=self.clear_path).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Отправить путь", command=self.send_path, style="Accent.TButton").pack(side=tk.RIGHT,
                                                                                                          padx=2)

        # Управление зумом
        zoom_frame = ttk.LabelFrame(self.left_frame, text="Управление картой", padding=10)
        zoom_frame.pack(fill=tk.X, pady=5)

        zoom_btn_frame = ttk.Frame(zoom_frame)
        zoom_btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(zoom_btn_frame, text="+ Увеличить", command=lambda: self.adjust_zoom(1.2)).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_btn_frame, text="- Уменьшить", command=lambda: self.adjust_zoom(0.8)).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_btn_frame, text="Сбросить вид", command=self.reset_view).pack(side=tk.RIGHT, padx=2)

        # Ответ сервера
        response_frame = ttk.LabelFrame(self.left_frame, text="Ответ сервера", padding=10)
        response_frame.pack(fill=tk.X, pady=5)

        self.response_text = tk.Text(response_frame, height=4, width=30, font=("Arial", 9))
        self.response_text.pack(fill=tk.X)
        self.response_text.insert(tk.END, self.server_response)
        self.response_text.config(state=tk.DISABLED)

    def init_center_panel(self):
        """Инициализация центральной панели (карта)"""
        map_frame = ttk.LabelFrame(self.center_frame, text="Карта местности", padding=10)
        map_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Создаем холст для карты
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        self.canvas = FigureCanvasTkAgg(self.fig, master=map_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Добавляем тулбар для навигации
        self.toolbar = NavigationToolbar2Tk(self.canvas, map_frame)
        self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Подключение обработчиков событий
        self.canvas.mpl_connect('button_press_event', self.on_map_click)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_release_event', self.on_pan_end)
        self.canvas.mpl_connect('motion_notify_event', self.on_pan_move)

        # Инициализация трансформации
        self.transform = Affine2D()
        self.trans_data = self.ax.transData

    def init_right_panel(self):
        """Инициализация правой панели (статистика и журнал)"""
        # Статистика колонии
        stats_frame = ttk.LabelFrame(self.right_frame, text="Статистика колонии", padding=10)
        stats_frame.pack(fill=tk.X, pady=5)

        # Создаем стиль для меток статистики
        style = ttk.Style()
        style.configure("Stats.TLabel", font=("Arial", 10))
        style.configure("StatsValue.TLabel", font=("Arial", 10, "bold"))

        # Муравьи
        ants_frame = ttk.Frame(stats_frame)
        ants_frame.pack(fill=tk.X, pady=5)

        self.worker_count_var = tk.StringVar(value="0")
        self.soldier_count_var = tk.StringVar(value="0")
        self.scout_count_var = tk.StringVar(value="0")
        self.total_ants_var = tk.StringVar(value="0")

        ttk.Label(ants_frame, text="Муравьи:", style="Stats.TLabel").grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))

        ttk.Label(ants_frame, text="Рабочие:", style="Stats.TLabel").grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Label(ants_frame, textvariable=self.worker_count_var, style="StatsValue.TLabel").grid(row=1, column=1, sticky=tk.W)

        ttk.Label(ants_frame, text="Солдаты:", style="Stats.TLabel").grid(row=2, column=0, sticky=tk.W, padx=5)
        ttk.Label(ants_frame, textvariable=self.soldier_count_var, style="StatsValue.TLabel").grid(row=2, column=1, sticky=tk.W)

        ttk.Label(ants_frame, text="Разведчики:", style="Stats.TLabel").grid(row=3, column=0, sticky=tk.W, padx=5)
        ttk.Label(ants_frame, textvariable=self.scout_count_var, style="StatsValue.TLabel").grid(row=3, column=1, sticky=tk.W)

        ttk.Label(ants_frame, text="Всего:", style="Stats.TLabel").grid(row=4, column=0, sticky=tk.W, padx=5)
        ttk.Label(ants_frame, textvariable=self.total_ants_var, style="StatsValue.TLabel").grid(row=4, column=1, sticky=tk.W)

        # Ресурсы
        resources_frame = ttk.Frame(stats_frame)
        resources_frame.pack(fill=tk.X, pady=5)
        ttk.Label(resources_frame, text="Ресурсы:", style="Stats.TLabel").grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))

        self.nectar_var = tk.StringVar(value="0")
        self.aphid_var = tk.StringVar(value="0")
        self.seeds_var = tk.StringVar(value="0")
        self.total_food_var = tk.StringVar(value="0")

        ttk.Label(resources_frame, text="Нектар:", style="Stats.TLabel").grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Label(resources_frame, textvariable=self.nectar_var, style="StatsValue.TLabel").grid(row=1, column=1, sticky=tk.W)

        ttk.Label(resources_frame, text="Падь:", style="Stats.TLabel").grid(row=2, column=0, sticky=tk.W, padx=5)
        ttk.Label(resources_frame, textvariable=self.aphid_var, style="StatsValue.TLabel").grid(row=2, column=1, sticky=tk.W)

        ttk.Label(resources_frame, text="Семена:", style="Stats.TLabel").grid(row=3, column=0, sticky=tk.W, padx=5)
        ttk.Label(resources_frame, textvariable=self.seeds_var, style="StatsValue.TLabel").grid(row=3, column=1, sticky=tk.W)

        ttk.Label(resources_frame, text="Всего:", style="Stats.TLabel").grid(row=4, column=0, sticky=tk.W, padx=5)
        ttk.Label(resources_frame, textvariable=self.total_food_var, style="StatsValue.TLabel").grid(row=4, column=1, sticky=tk.W)

        # Муравейник
        hill_frame = ttk.Frame(stats_frame)
        hill_frame.pack(fill=tk.X, pady=5)
        ttk.Label(hill_frame, text="Муравейник:", style="Stats.TLabel").grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))

        self.hill_health_var = tk.StringVar(value="100%")
        self.hill_position_var = tk.StringVar(value="0,0")

        ttk.Label(hill_frame, text="Здоровье:", style="Stats.TLabel").grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Label(hill_frame, textvariable=self.hill_health_var, style="StatsValue.TLabel").grid(row=1, column=1, sticky=tk.W)

        ttk.Label(hill_frame, text="Позиция:", style="Stats.TLabel").grid(row=2, column=0, sticky=tk.W, padx=5)
        ttk.Label(hill_frame, textvariable=self.hill_position_var, style="StatsValue.TLabel").grid(row=2, column=1, sticky=tk.W)

        # Журнал событий
        log_frame = ttk.LabelFrame(self.right_frame, text="Журнал событий", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Arial", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def init_status_bar(self):
        """Инициализация статус-бара"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_var = tk.StringVar()
        self.status_var.set("Статус: Ожидание данных...")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W,
                               font=("Arial", 10))
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.update_var = tk.StringVar()
        self.update_var.set("Последнее обновление: никогда")
        update_bar = ttk.Label(status_frame, textvariable=self.update_var, relief=tk.SUNKEN, anchor=tk.E,
                               width=30, font=("Arial", 10))
        update_bar.pack(side=tk.RIGHT, fill=tk.Y)

    def on_scroll(self, event):
        """Обработчик масштабирования колесом мыши"""
        if event.inaxes:
            # Определяем направление скролла
            zoom_factor = 1.1 if event.button == 'up' else 0.9
            self.zoom_level *= zoom_factor

            # Ограничиваем уровень масштаба
            self.zoom_level = max(0.5, min(5.0, self.zoom_level))

            # Обновление карты
            self.update_ui()

    def on_pan_start(self, event):
        """Начало перемещения карты"""
        if event.button == 2:  # Средняя кнопка мыши
            self.pan_start = (event.x, event.y)
            self.canvas._tkcanvas.config(cursor="fleur")

    def on_pan_move(self, event):
        """Перемещение карты"""
        if event.button == 2 and self.pan_start:
            dx = (event.x - self.pan_start[0]) / self.zoom_level
            dy = (event.y - self.pan_start[1]) / self.zoom_level

            self.pan_offset[0] += dx * 0.05
            self.pan_offset[1] -= dy * 0.05

            self.pan_start = (event.x, event.y)
            self.update_ui()

    def on_pan_end(self, event):
        """Завершение перемещения карты"""
        if event.button == 2:
            self.pan_start = None
            self.canvas._tkcanvas.config(cursor="")

    def adjust_zoom(self, factor):
        """Ручное управление зумом"""
        self.zoom_level *= factor
        self.zoom_level = max(0.5, min(5.0, self.zoom_level))
        self.update_ui()

    def reset_view(self):
        """Сброс вида карты"""
        self.zoom_level = 1.0
        self.pan_offset = [0, 0]
        self.update_ui()

    def manual_update(self):
        """Ручное обновление данных"""
        self.update_game_data(force=True)

    def update_game_data(self, force=False):
        """Поток для обновления данных игры"""
        while True:
            try:
                # Имитация ответа сервера
                import json

                dummy_response = """
                {
  "ants": [
    {
      "q": 60,
      "r": 120,
      "type": 1,
      "health": 180,
      "id": "8f389069-1515-4138-94a0-91cebda3d64c",
      "food": {
        "type": 0,
        "amount": 0
      }
    },
    {
      "q": 60,
      "r": 120,
      "type": 2,
      "health": 80,
      "id": "407dd26c-4232-4816-9160-9c75e85dc4b5",
      "food": {
        "type": 0,
        "amount": 0
      }
    },
    {
      "q": 60,
      "r": 120,
      "type": 0,
      "health": 130,
      "id": "4f3234e1-0b04-4489-970d-f2d70c72255a",
      "food": {
        "type": 0,
        "amount": 0
      }
    }
  ],
  "enemies": [],
  "map": [
    {
      "q": 60,
      "r": 124,
      "cost": 1,
      "type": 2
    },
    {
      "q": 61,
      "r": 120,
      "cost": 1,
      "type": 2
    },
    {
      "q": 62,
      "r": 124,
      "cost": 1,
      "type": 2
    },
    {
      "q": 59,
      "r": 117,
      "cost": 1,
      "type": 3
    },
    {
      "q": 62,
      "r": 120,
      "cost": 1,
      "type": 2
    },
    {
      "q": 60,
      "r": 123,
      "cost": 1,
      "type": 2
    },
    {
      "q": 63,
      "r": 122,
      "cost": 1,
      "type": 2
    },
    {
      "q": 61,
      "r": 116,
      "cost": 1,
      "type": 3
    },
    {
      "q": 60,
      "r": 119,
      "cost": 1,
      "type": 1
    },
    {
      "q": 61,
      "r": 124,
      "cost": 1,
      "type": 2
    },
    {
      "q": 58,
      "r": 123,
      "cost": 1,
      "type": 2
    },
    {
      "q": 58,
      "r": 118,
      "cost": 1,
      "type": 2
    },
    {
      "q": 62,
      "r": 117,
      "cost": 1,
      "type": 3
    },
    {
      "q": 58,
      "r": 124,
      "cost": 1,
      "type": 2
    },
    {
      "q": 58,
      "r": 121,
      "cost": 1,
      "type": 2
    },
    {
      "q": 63,
      "r": 121,
      "cost": 1,
      "type": 2
    },
    {
      "q": 59,
      "r": 118,
      "cost": 1,
      "type": 2
    },
    {
      "q": 56,
      "r": 120,
      "cost": 1,
      "type": 2
    },
    {
      "q": 62,
      "r": 123,
      "cost": 1,
      "type": 2
    },
    {
      "q": 62,
      "r": 119,
      "cost": 1,
      "type": 3
    },
    {
      "q": 59,
      "r": 123,
      "cost": 1,
      "type": 2
    },
    {
      "q": 57,
      "r": 119,
      "cost": 1,
      "type": 2
    },
    {
      "q": 58,
      "r": 122,
      "cost": 1,
      "type": 2
    },
    {
      "q": 58,
      "r": 120,
      "cost": 1,
      "type": 2
    },
    {
      "q": 61,
      "r": 117,
      "cost": 1,
      "type": 3
    },
    {
      "q": 62,
      "r": 121,
      "cost": 1,
      "type": 2
    },
    {
      "q": 63,
      "r": 120,
      "cost": 1,
      "type": 2
    },
    {
      "q": 58,
      "r": 119,
      "cost": 1,
      "type": 2
    },
    {
      "q": 60,
      "r": 116,
      "cost": 1,
      "type": 2
    },
    {
      "q": 57,
      "r": 122,
      "cost": 1,
      "type": 2
    },
    {
      "q": 59,
      "r": 122,
      "cost": 1,
      "type": 2
    },
    {
      "q": 59,
      "r": 124,
      "cost": 1,
      "type": 2
    },
    {
      "q": 56,
      "r": 121,
      "cost": 1,
      "type": 4
    },
    {
      "q": 62,
      "r": 118,
      "cost": 1,
      "type": 3
    },
    {
      "q": 61,
      "r": 118,
      "cost": 1,
      "type": 2
    },
    {
      "q": 59,
      "r": 119,
      "cost": 1,
      "type": 1
    },
    {
      "q": 56,
      "r": 119,
      "cost": 1,
      "type": 2
    },
    {
      "q": 64,
      "r": 120,
      "cost": 1,
      "type": 3
    },
    {
      "q": 61,
      "r": 121,
      "cost": 1,
      "type": 2
    },
    {
      "q": 63,
      "r": 118,
      "cost": 1,
      "type": 3
    },
    {
      "q": 58,
      "r": 117,
      "cost": 1,
      "type": 2
    },
    {
      "q": 63,
      "r": 119,
      "cost": 1,
      "type": 3
    },
    {
      "q": 60,
      "r": 117,
      "cost": 1,
      "type": 3
    },
    {
      "q": 60,
      "r": 122,
      "cost": 1,
      "type": 2
    },
    {
      "q": 60,
      "r": 120,
      "cost": 1,
      "type": 1
    },
    {
      "q": 59,
      "r": 120,
      "cost": 1,
      "type": 2
    },
    {
      "q": 57,
      "r": 117,
      "cost": 1,
      "type": 2
    },
    {
      "q": 57,
      "r": 121,
      "cost": 1,
      "type": 2
    },
    {
      "q": 59,
      "r": 116,
      "cost": 1,
      "type": 3
    },
    {
      "q": 60,
      "r": 121,
      "cost": 1,
      "type": 2
    },
    {
      "q": 61,
      "r": 119,
      "cost": 1,
      "type": 2
    },
    {
      "q": 61,
      "r": 122,
      "cost": 1,
      "type": 2
    },
    {
      "q": 58,
      "r": 116,
      "cost": 1,
      "type": 2
    },
    {
      "q": 57,
      "r": 120,
      "cost": 1,
      "type": 4
    },
    {
      "q": 62,
      "r": 122,
      "cost": 1,
      "type": 2
    },
    {
      "q": 62,
      "r": 116,
      "cost": 1,
      "type": 3
    },
    {
      "q": 61,
      "r": 123,
      "cost": 1,
      "type": 2
    },
    {
      "q": 57,
      "r": 123,
      "cost": 1,
      "type": 2
    },
    {
      "q": 59,
      "r": 121,
      "cost": 1,
      "type": 2
    },
    {
      "q": 57,
      "r": 118,
      "cost": 1,
      "type": 2
    },
    {
      "q": 60,
      "r": 118,
      "cost": 1,
      "type": 2
    }
  ],
  "food": [
    {
      "q": 62,
      "r": 120,
      "type": 1,
      "amount": 1
    },
    {
      "q": 63,
      "r": 122,
      "type": 2,
      "amount": 13
    },
    {
      "q": 58,
      "r": 123,
      "type": 2,
      "amount": 7
    },
    {
      "q": 61,
      "r": 117,
      "type": 1,
      "amount": 15
    },
    {
      "q": 57,
      "r": 122,
      "type": 1,
      "amount": 12
    },
    {
      "q": 59,
      "r": 120,
      "type": 1,
      "amount": 8
    },
    {
      "q": 59,
      "r": 121,
      "type": 2,
      "amount": 10
    }
  ],
  "turnNo": 19,
  "nextTurnIn": 1.049,
  "home": [
    {
      "q": 60,
      "r": 120
    },
    {
      "q": 60,
      "r": 119
    },
    {
      "q": 59,
      "r": 119
    }
  ],
  "score": 0,
  "spot": {
    "q": 60,
    "r": 120
  }
}
                """


                self.game_data = json.loads(dummy_response)
                self.last_update = datetime.datetime.now().strftime("%H:%M:%S")

                for ant in self.game_data['ants']:
                    if 'lastMove' in ant and ant['lastMove']:
                        self.history_paths[ant['id']] = ant['lastMove']

                self.update_colony_stats()
                self.root.after(0, self.update_ui)

                current_time = time.time()
                if current_time - self.last_log_update > 5 or force:
                    self.get_logs()
                    self.last_log_update = current_time

            except Exception as e:
                self.status_var.set(f"Ошибка соединения: {str(e)}")
            # try:
            #     response = requests.get(f"{BASE_URL}/arena", headers=HEADERS)
            #     if response.status_code == 200:
            #         self.game_data = response.json()
            #         self.last_update = datetime.datetime.now().strftime("%H:%M:%S")
            #
            #         # Сохраняем историю перемещений
            #         for ant in self.game_data['ants']:
            #             if 'lastMove' in ant and ant['lastMove']:
            #                 self.history_paths[ant['id']] = ant['lastMove']
            #
            #         # Обновляем статистику колонии
            #         self.update_colony_stats()
            #
            #         self.root.after(0, self.update_ui)
            #
            #         # Обновление журнала раз в 5 секунд
            #         current_time = time.time()
            #         if current_time - self.last_log_update > 5 or force:
            #             self.get_logs()
            #             self.last_log_update = current_time
            #     else:
            #         self.status_var.set(f"Ошибка: {response.status_code} - {response.text}")
            # except Exception as e:
            #     self.status_var.set(f"Ошибка соединения: {str(e)}")

            # Обновление каждую секунду или по nextTurnIn
            sleep_time = min(1.0, self.game_data.get('nextTurnIn', 1.0))
            time.sleep(sleep_time)

    def update_colony_stats(self):
        """Обновление статистики колонии"""
        # Сбрасываем счетчики
        self.colony_stats = {
            'worker_count': 0,
            'soldier_count': 0,
            'scout_count': 0,
            'nectar': 0,
            'aphid': 0,
            'seeds': 0,
            'total_food': 0
        }

        # Считаем муравьев
        for ant in self.game_data['ants']:
            if ant['type'] == 0:
                self.colony_stats['worker_count'] += 1
            elif ant['type'] == 1:
                self.colony_stats['soldier_count'] += 1
            elif ant['type'] == 2:
                self.colony_stats['scout_count'] += 1

            # Считаем ресурсы у муравьев
            if 'food' in ant:
                food = ant['food']
                if food['type'] == 0:
                    self.colony_stats['nectar'] += food['amount']
                elif food['type'] == 1:
                    self.colony_stats['aphid'] += food['amount']
                elif food['type'] == 2:
                    self.colony_stats['seeds'] += food['amount']

        # Считаем ресурсы на карте (в зоне видимости)
        for food in self.game_data['food']:
            if food['type'] == 0:
                self.colony_stats['nectar'] += food['amount']
            elif food['type'] == 1:
                self.colony_stats['aphid'] += food['amount']
            elif food['type'] == 2:
                self.colony_stats['seeds'] += food['amount']

        # Общее количество
        self.colony_stats['total_food'] = (
            self.colony_stats['nectar'] +
            self.colony_stats['aphid'] +
            self.colony_stats['seeds']
        )

        # Обновляем переменные интерфейса
        self.worker_count_var.set(str(self.colony_stats['worker_count']))
        self.soldier_count_var.set(str(self.colony_stats['soldier_count']))
        self.scout_count_var.set(str(self.colony_stats['scout_count']))
        self.total_ants_var.set(str(len(self.game_data['ants'])))

        self.nectar_var.set(f"{self.colony_stats['nectar']} ед.")
        self.aphid_var.set(f"{self.colony_stats['aphid']} ед.")
        self.seeds_var.set(f"{self.colony_stats['seeds']} ед.")
        self.total_food_var.set(f"{self.colony_stats['total_food']} ед.")

        # Информация о муравейнике
        if 'spot' in self.game_data:
            spot = self.game_data['spot']
            self.hill_position_var.set(f"{spot['q']},{spot['r']}")
        else:
            self.hill_position_var.set("Неизвестно")

        # Здоровье муравейника (условно)
        self.hill_health_var.set("100%")

    def update_ui(self):
        """Обновление интерфейса с учетом трансформации"""
        # Обновление статус-бара
        status = f"Ход: {self.game_data['turnNo']} | След. ход через: {self.game_data['nextTurnIn']:.1f} сек"
        self.status_var.set(status)
        self.update_var.set(f"Обновлено: {self.last_update}")

        # Обновление верхней панели
        self.turn_var.set(
            f"Текущий ход: {self.game_data['turnNo']} | Следующий ход через: {self.game_data['nextTurnIn']:.1f} сек")
        self.score_var.set(f"{self.game_data['score']}")

        # Очистка карты
        self.ax.clear()
        self.ax.set_aspect('equal')
        self.ax.axis('off')

        # Рассчитываем границы карты
        min_q, max_q, min_r, max_r = 0, 0, 0, 0
        if self.game_data['map']:
            q_values = [cell['q'] for cell in self.game_data['map']]
            r_values = [cell['r'] for cell in self.game_data['map']]
            min_q, max_q = min(q_values), max(q_values)
            min_r, max_r = min(r_values), max(r_values)

        # Динамический размер гекса
        hex_count = len(self.game_data['map'])
        base_hex_size = max(0.4, min(1.0, 15 / np.sqrt(hex_count))) if hex_count > 0 else 0.5
        hex_size = base_hex_size * self.zoom_level

        # Отрисовка гексов
        hex_patches = []
        for cell in self.game_data['map']:
            x, y = self.hex_to_cart(cell['q'], cell['r'])
            hexagon = RegularPolygon(
                (x, y), numVertices=6, radius=hex_size,
                orientation=np.pi / 6,
                facecolor=HEX_COLORS.get(cell['type'], '#F0F0F0'),
                edgecolor='black', alpha=0.8
            )
            hex_patches.append(hexagon)

            # Подписи координат (только при достаточном зуме)
            if self.zoom_level > 1.5:
                self.ax.text(x, y + hex_size * 0.5, f"{cell['q']},{cell['r']}",
                             ha='center', va='center', fontsize=8, color='black')

        # Добавляем все гексы одним вызовом для производительности
        self.ax.add_collection(PatchCollection(hex_patches, match_original=True))

        # Отрисовка муравейника
        for home in self.game_data['home']:
            x, y = self.hex_to_cart(home['q'], home['r'])
            home_patch = RegularPolygon(
                (x, y), numVertices=6, radius=hex_size * 0.9,
                facecolor='red', edgecolor='gold', linewidth=2
            )
            self.ax.add_patch(home_patch)

            # Основной гекс
            if 'spot' in self.game_data and home['q'] == self.game_data['spot']['q'] and home['r'] == \
                self.game_data['spot']['r']:
                self.ax.text(x, y, "Центр", ha='center', va='center', fontsize=9, color='white', weight='bold')

        # Отрисовка ресурсов
        for food in self.game_data['food']:
            x, y = self.hex_to_cart(food['q'], food['r'])
            food_patch = Circle(
                (x, y), radius=hex_size / 3,
                facecolor=FOOD_COLORS.get(food['type'], '#FFD700')
            )
            self.ax.add_patch(food_patch)
            if self.zoom_level > 1.2:
                self.ax.text(x, y, str(food['amount']),
                             ha='center', va='center', fontsize=8, color='white')

        # Отрисовка своих муравьев
        ants_by_cell = defaultdict(list)
        for ant in self.game_data['ants']:
            key = f"{ant['q']},{ant['r']}"
            ants_by_cell[key].append(ant)

        for cell_key, ants in ants_by_cell.items():
            q, r = map(int, cell_key.split(','))
            center_x, center_y = self.hex_to_cart(q, r)
            radius = hex_size * 0.6

            for i, ant in enumerate(ants):
                if len(ants) == 1:
                    # Один муравей - в центре
                    x, y = center_x, center_y
                else:
                    # Несколько муравьев - распределение по кругу
                    angle = 2 * np.pi * i / len(ants)
                    x = center_x + radius * np.cos(angle)
                    y = center_y + radius * np.sin(angle)

                # Цвет по типу муравья
                color = ANT_COLORS.get(ant['type'], 'green')
                ant_patch = Circle(
                    (x, y), radius=hex_size / 2,
                    facecolor=color, edgecolor='black'
                )
                self.ax.add_patch(ant_patch)

                # ID (короткий) и здоровье
                ant_id_short = ant['id'].split('-')[0]
                health = ant['health']
                text = f"{ant_id_short}\n{health}HP"
                self.ax.text(x, y, text, ha='center', va='center',
                             fontsize=7 if len(ants) > 1 else 8,
                             color='white')

        # Отрисовка вражеских муравьев
        enemies_by_cell = defaultdict(list)
        for enemy in self.game_data['enemies']:
            key = f"{enemy['q']},{enemy['r']}"
            enemies_by_cell[key].append(enemy)

        for cell_key, enemies in enemies_by_cell.items():
            q, r = map(int, cell_key.split(','))
            center_x, center_y = self.hex_to_cart(q, r)
            radius = hex_size * 0.6

            for i, enemy in enumerate(enemies):
                if len(enemies) == 1:
                    x, y = center_x, center_y
                else:
                    angle = 2 * np.pi * i / len(enemies)
                    x = center_x + radius * np.cos(angle)
                    y = center_y + radius * np.sin(angle)

                # Цвет по типу муравья
                color = ENEMY_COLORS.get(enemy.get('type', 0), 'red')
                enemy_patch = Circle(
                    (x, y), radius=hex_size / 2,
                    facecolor=color, edgecolor='black'
                )
                self.ax.add_patch(enemy_patch)

                # Тип (краткое обозначение) и здоровье
                enemy_type = "W" if enemy.get('type', 0) == 0 else "S" if enemy.get('type', 0) == 1 else "E"
                health = enemy['health']
                text = f"{enemy_type}\n{health}HP"
                self.ax.text(x, y, text,
                             ha='center', va='center', fontsize=8, color='white', fontweight='bold')

        # Отрисовка пути
        self.draw_path(hex_size)

        # Отрисовка истории перемещений
        self.draw_history_paths(hex_size)

        # Добавление легенды
        self.add_legend()

        # Устанавливаем границы отображения
        if hex_count > 0:
            margin = hex_size * 3
            min_x, min_y = self.hex_to_cart(min_q, min_r)
            max_x, max_y = self.hex_to_cart(max_q, max_r)
            self.ax.set_xlim(min_x - margin, max_x + margin)
            self.ax.set_ylim(min_y - margin, max_y + margin)

        # Обновление холста
        self.canvas.draw()

    def add_legend(self):
        """Добавление легенды в правый верхний угол"""
        legend_elements = [
            Patch(facecolor=HEX_COLORS[0], edgecolor='black', label='Пустой'),
            Patch(facecolor=HEX_COLORS[1], edgecolor='black', label='Грязь'),
            Patch(facecolor=HEX_COLORS[2], edgecolor='black', label='Камень'),
            Patch(facecolor=HEX_COLORS[3], edgecolor='black', label='Кислота'),
            Patch(facecolor=HEX_COLORS[4], edgecolor='black', label='Муравейник'),
            Patch(facecolor=ANT_COLORS[0], edgecolor='black', label='Рабочий (свой)'),
            Patch(facecolor=ANT_COLORS[1], edgecolor='black', label='Солдат (свой)'),
            Patch(facecolor=ANT_COLORS[2], edgecolor='black', label='Разведчик (свой)'),
            Patch(facecolor=ENEMY_COLORS[0], edgecolor='black', label='Рабочий (враг)'),
            Patch(facecolor=ENEMY_COLORS[1], edgecolor='black', label='Солдат (враг)'),
            Patch(facecolor=ENEMY_COLORS[2], edgecolor='black', label='Разведчик (враг)'),
            Patch(facecolor=FOOD_COLORS[0], edgecolor='black', label='Нектар'),
            Patch(facecolor=FOOD_COLORS[1], edgecolor='black', label='Падь'),
            Patch(facecolor=FOOD_COLORS[2], edgecolor='black', label='Семена')
        ]

        # Размещаем легенду в правом верхнем углу
        legend = self.ax.legend(
            handles=legend_elements,
            loc='upper left',
            bbox_to_anchor=(0.02, 0.98),
            fontsize=8,
            title="Легенда",
            title_fontsize=9,
            framealpha=0.8
        )
        legend.get_frame().set_facecolor('white')

        # Добавляем информацию о ходе
        turn_info = f"Ход: {self.game_data['turnNo']} | След. ход через: {self.game_data['nextTurnIn']:.1f} сек"
        self.ax.annotate(
            turn_info,
            xy=(0.5, 0.02),
            xycoords='figure fraction',
            ha='center',
            fontsize=11,
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.7)
        )

    def hex_to_cart(self, q, r):
        """Преобразование гексагональных координат в декартовы"""
        x = self.base_hex_size * 3 / 2 * q
        y = self.base_hex_size * np.sqrt(3) * (r + q / 2)
        return x, y

    def cart_to_hex(self, x, y):
        """Преобразование декартовых координат в гексагональные"""
        q = (2 / 3 * x) / self.base_hex_size
        r = (-1 / 3 * x + np.sqrt(3) / 3 * y) / self.base_hex_size
        return self.axial_round(q, r)

    def axial_round(self, q, r):
        """Округление координат до ближайшего гекса"""
        s = -q - r
        q_rnd = round(q)
        r_rnd = round(r)
        s_rnd = round(s)

        q_diff = abs(q_rnd - q)
        r_diff = abs(r_rnd - r)
        s_diff = abs(s_rnd - s)

        if q_diff > r_diff and q_diff > s_diff:
            q_rnd = -r_rnd - s_rnd
        elif r_diff > s_diff:
            r_rnd = -q_rnd - s_rnd
        else:
            s_rnd = -q_rnd - r_rnd

        return int(q_rnd), int(r_rnd)

    def on_map_click(self, event):
        """Обработчик кликов по карте"""
        if event.xdata is None or event.ydata is None:
            return

        # Определяем гекс по клику
        q, r = self.cart_to_hex(event.xdata, event.ydata)

        # Проверяем, кликнули ли на муравья
        clicked_ant = None
        for ant in self.game_data['ants']:
            if ant['q'] == q and ant['r'] == r:
                clicked_ant = ant
                break

        if clicked_ant:
            # Показываем информацию о муравье
            self.show_ant_info(clicked_ant)

            # Выбираем муравья для управления
            self.selected_ant = clicked_ant
            self.path_points = []
            ant_type = ANT_TYPES.get(clicked_ant['type'], "Неизвестный")
            self.selected_ant_label.config(
                text=f"{ant_type} (ID: {clicked_ant['id'][:8]})"
            )
            self.path_label.config(text="Путь очищен")
        elif self.selected_ant:
            # Добавление точки в путь
            self.path_points.append({"q": q, "r": r})
            self.path_label.config(text=f"Путь: {len(self.path_points)} точек")

            # Перерисовка карты для отображения пути
            self.update_ui()

    def show_ant_info(self, ant):
        """Отображение информации о муравье"""
        # Очищаем предыдущую информацию
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)

        # Собираем информацию
        ant_type = ANT_TYPES.get(ant['type'], "Неизвестный")
        health = ant['health']
        food_type = FOOD_TYPES.get(ant['food']['type'], "Нет") if 'food' in ant else "Нет"
        food_amount = ant['food']['amount'] if 'food' in ant else 0
        ant_id = ant['id']
        position = f"{ant['q']},{ant['r']}"

        # Информация о последнем действии
        last_action = "Неизвестно"
        if 'lastAttack' in ant and ant['lastAttack']:
            last_action = f"Атака на {ant['lastAttack']['q']},{ant['lastAttack']['r']}"
        elif 'lastMove' in ant and ant['lastMove']:
            last_action = f"Перемещение: {len(ant['lastMove'])} шагов"

        # Форматируем информацию
        info = f"Тип: {ant_type}\n\n"
        info += f"Здоровье: {health}\n\n"
        info += f"Ресурсы: {food_type} ({food_amount})\n\n"
        info += f"Позиция: {position}\n\n"
        info += f"Последнее действие: {last_action}\n\n"
        info += f"ID: {ant_id}"

        # Вставляем информацию
        self.info_text.insert(tk.END, info)
        self.info_text.config(state=tk.DISABLED)

    def draw_path(self, hex_size):
        """Отрисовка пути на карте"""
        if not self.selected_ant or not self.path_points:
            return

        # Текущая позиция муравья
        start_q, start_r = self.selected_ant['q'], self.selected_ant['r']
        start_x, start_y = self.hex_to_cart(start_q, start_r)

        # Отрисовка пути
        points_x, points_y = [start_x], [start_y]
        for point in self.path_points:
            x, y = self.hex_to_cart(point['q'], point['r'])
            points_x.append(x)
            points_y.append(y)

            # Отрисовка точки пути
            self.ax.plot(x, y, 'o', markersize=8, color='blue', alpha=0.5)

        # Отрисовка линии пути
        self.ax.plot(points_x, points_y, 'b--', linewidth=1.5, alpha=0.7)

        # Стрелка в конце пути
        if len(points_x) > 1:
            self.ax.annotate('',
                             xy=(points_x[-1], points_y[-1]),
                             xytext=(points_x[-2], points_y[-2]),
                             arrowprops=dict(arrowstyle='->', color='blue', lw=1.5, alpha=0.7)
                             )

    def draw_history_paths(self, hex_size):
        """Отрисовка истории перемещений"""
        for ant_id, path in self.history_paths.items():
            if not path:
                continue

            points_x, points_y = [], []
            for point in path:
                x, y = self.hex_to_cart(point['q'], point['r'])
                points_x.append(x)
                points_y.append(y)

            # Отрисовка линии истории
            self.ax.plot(points_x, points_y, 'g:', linewidth=1.0, alpha=0.4)

            # Стрелка в конце пути
            if len(points_x) > 1:
                self.ax.annotate('',
                                 xy=(points_x[-1], points_y[-1]),
                                 xytext=(points_x[-2], points_y[-2]),
                                 arrowprops=dict(arrowstyle='->', color='green', lw=1.0, alpha=0.4)
                                 )

    def clear_path(self):
        """Очистка пути"""
        self.path_points = []
        self.path_label.config(text="Путь очищен")
        if self.selected_ant:
            self.update_ui()

    def send_path(self):
        """Отправка пути движения"""
        if not self.selected_ant or not self.path_points:
            messagebox.showwarning("Ошибка", "Выберите муравья и задайте путь")
            return

        try:
            move_data = {
                "moves": [{
                    "ant": self.selected_ant['id'],
                    "path": self.path_points
                }]
            }

            response = requests.post(
                f"{BASE_URL}/move",
                headers={**HEADERS, 'Content-Type': 'application/json'},
                json=move_data
            )

            if response.status_code == 200:
                self.server_response = "Путь успешно отправлен!"
                self.path_points = []
                self.path_label.config(text="Путь отправлен")
            else:
                error_msg = response.json().get('message', 'Неизвестная ошибка')
                self.server_response = f"Ошибка {response.status_code}: {error_msg}"

            # Обновляем поле ответа
            self.response_text.config(state=tk.NORMAL)
            self.response_text.delete(1.0, tk.END)
            self.response_text.insert(tk.END, self.server_response)
            self.response_text.config(state=tk.DISABLED)

        except Exception as e:
            self.server_response = f"Ошибка: {str(e)}"
            self.response_text.config(state=tk.NORMAL)
            self.response_text.delete(1.0, tk.END)
            self.response_text.insert(tk.END, self.server_response)
            self.response_text.config(state=tk.DISABLED)

    def register(self):
        """Регистрация команды"""
        try:
            response = requests.post(f"{BASE_URL}/register", headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                self.server_response = f"Регистрация успешна!\nИмя: {data['name']}"

                # Обновляем поле ответа
                self.response_text.config(state=tk.NORMAL)
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(tk.END, self.server_response)
                self.response_text.config(state=tk.DISABLED)
            else:
                self.server_response = f"Ошибка регистрации: {response.status_code}\n{response.text}"
                self.response_text.config(state=tk.NORMAL)
                self.response_text.delete(1.0, tk.END)
                self.response_text.insert(tk.END, self.server_response)
                self.response_text.config(state=tk.DISABLED)
        except Exception as e:
            self.server_response = f"Ошибка: {str(e)}"
            self.response_text.config(state=tk.NORMAL)
            self.response_text.delete(1.0, tk.END)
            self.response_text.insert(tk.END, self.server_response)
            self.response_text.config(state=tk.DISABLED)

    def get_logs(self):
        """Получение журнала событий"""
        try:
            response = requests.get(f"{BASE_URL}/logs", headers=HEADERS)
            if response.status_code == 200:
                self.logs = response.json()
                self.log_text.delete(1.0, tk.END)
                for log in self.logs:
                    self.log_text.insert(tk.END, f"{log['time']}: {log['message']}\n")
                # Прокрутка вниз
                self.log_text.see(tk.END)
        except Exception as e:
            self.status_var.set(f"Ошибка журнала: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()

    # Стилизация интерфейса
    style = ttk.Style()
    style.configure("Accent.TButton", foreground="white", background="#4CAF50", font=("Arial", 10, "bold"))
    style.configure("Secondary.TButton", foreground="white", background="#2196F3", font=("Arial", 10))
    style.configure("Stats.TLabel", font=("Arial", 10))
    style.configure("StatsValue.TLabel", font=("Arial", 10, "bold"))

    app = HexMapApp(root)
    root.mainloop()