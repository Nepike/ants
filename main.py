import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import threading
import time
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon, Circle, Patch
import numpy as np
import datetime

import config

# Конфигурация
BASE_URL = 'https://games-test.datsteam.dev/api'

HEADERS = {'accept': 'application/json', 'X-Auth-Token': config.TOKEN}

# Цвета для типов гексов
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


class HexMapApp:
	def __init__(self, root):
		self.root = root
		self.root.title("DatsPulse Ants Viewer")
		self.root.geometry("1400x900")

		# Переменные состояния
		self.selected_ant = None
		self.path_points = []
		self.last_update = "Не обновлялось"
		self.hex_size = 0.5  # Начальный размер гекса

		# Основные фреймы
		self.left_frame = ttk.Frame(root, width=300)
		self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

		self.right_frame = ttk.Frame(root)
		self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

		# Инициализация компонентов
		self.init_controls()
		self.init_status_bar()
		self.init_map()

		# Данные игры
		self.game_data = {
			'ants': [],
			'enemies': [],
			'food': [],
			'home': [],
			'map': [],
			'score': 0,
			'turnNo': 0,
			'nextTurnIn': 0
		}

		# Старт потока обновления данных
		self.update_thread = threading.Thread(target=self.update_game_data, daemon=True)
		self.update_thread.start()

	def init_controls(self):
		"""Инициализация панели управления"""
		# Панель информации
		info_frame = ttk.LabelFrame(self.left_frame, text="Информация", padding=10)
		info_frame.pack(fill=tk.X, pady=5)

		self.info_text = tk.Text(info_frame, height=8, width=30)
		self.info_text.pack(fill=tk.X)
		self.info_text.config(state=tk.DISABLED)

		# Регистрация
		reg_frame = ttk.LabelFrame(self.left_frame, text="Регистрация", padding=10)
		reg_frame.pack(fill=tk.X, pady=5)
		ttk.Button(reg_frame, text="Зарегистрироваться", command=self.register).pack(fill=tk.X)

		# Управление муравьями
		move_frame = ttk.LabelFrame(self.left_frame, text="Управление муравьями", padding=10)
		move_frame.pack(fill=tk.X, pady=5)

		ttk.Label(move_frame, text="Выбранный муравей:").pack(anchor=tk.W)
		self.selected_ant_label = ttk.Label(move_frame, text="Никто не выбран")
		self.selected_ant_label.pack(fill=tk.X, pady=2)

		ttk.Label(move_frame, text="Путь движения:").pack(anchor=tk.W)
		self.path_label = ttk.Label(move_frame, text="Не задан")
		self.path_label.pack(fill=tk.X, pady=2)

		btn_frame = ttk.Frame(move_frame)
		btn_frame.pack(fill=tk.X, pady=5)

		ttk.Button(btn_frame, text="Очистить путь", command=self.clear_path).pack(side=tk.LEFT, padx=2)
		ttk.Button(btn_frame, text="Отправить путь", command=self.send_path).pack(side=tk.RIGHT, padx=2)

		# Логи
		log_frame = ttk.LabelFrame(self.left_frame, text="Журнал событий", padding=10)
		log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

		self.log_text = scrolledtext.ScrolledText(log_frame, height=12)
		self.log_text.pack(fill=tk.BOTH, expand=True)
		ttk.Button(log_frame, text="Обновить логи", command=self.get_logs).pack(fill=tk.X, pady=5)

		# Легенда
		legend_frame = ttk.LabelFrame(self.left_frame, text="Легенда", padding=10)
		legend_frame.pack(fill=tk.X, pady=5)

		legend_text = (
			"Гексы:\n"
			"▢ Пустой\n"
			"▢ Грязь\n"
			"▢ Камень\n"
			"▢ Кислота\n"
			"▢ Муравейник\n\n"
			"Муравьи:\n"
			"● Рабочий (зеленый)\n"
			"● Солдат (синий)\n"
			"● Разведчик (фиолетовый)\n"
			"● Враг (красный)\n\n"
			"Ресурсы:\n"
			"● Нектар (золотой)\n"
			"● Падь (красный)\n"
			"● Семена (коричневый)"
		)
		ttk.Label(legend_frame, text=legend_text).pack(anchor=tk.W)

		# Кнопка выхода
		ttk.Button(self.left_frame, text="Выход", command=self.root.destroy).pack(fill=tk.X, pady=10)

	def init_status_bar(self):
		"""Инициализация статус-бара"""
		status_frame = ttk.Frame(self.root)
		status_frame.pack(side=tk.BOTTOM, fill=tk.X)

		self.status_var = tk.StringVar()
		self.status_var.set("Статус: Ожидание данных...")
		status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
		status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

		self.update_var = tk.StringVar()
		self.update_var.set("Последнее обновление: никогда")
		update_bar = ttk.Label(status_frame, textvariable=self.update_var, relief=tk.SUNKEN, anchor=tk.E, width=25)
		update_bar.pack(side=tk.RIGHT, fill=tk.Y)

	def init_map(self):
		"""Инициализация карты"""
		self.fig, self.ax = plt.subplots(figsize=(10, 8))
		self.ax.set_aspect('equal')
		self.ax.axis('off')
		self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
		self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

		# Подключение обработчика кликов
		self.canvas.mpl_connect('button_press_event', self.on_map_click)

	def update_game_data(self):
		"""Поток для обновления данных игры"""
		while True:
			try:
				response = requests.get(f"{BASE_URL}/arena", headers=HEADERS)
				if response.status_code == 200:
					self.game_data = response.json()
					self.last_update = datetime.datetime.now().strftime("%H:%M:%S")
					self.root.after(0, self.update_ui)
				else:
					self.status_var.set(f"Ошибка: {response.status_code} - {response.text}")
			except Exception as e:
				self.status_var.set(f"Ошибка соединения: {str(e)}")

			# Обновление каждую секунду или по nextTurnIn
			sleep_time = min(1.0, self.game_data.get('nextTurnIn', 1.0))
			time.sleep(sleep_time)

	def update_ui(self):
		"""Обновление интерфейса"""
		# Обновление статус-бара
		status = f"Ход: {self.game_data['turnNo']} | Счет: {self.game_data['score']} | "
		status += f"След. ход через: {self.game_data['nextTurnIn']:.1f} сек"
		self.status_var.set(status)
		self.update_var.set(f"Обновлено: {self.last_update}")

		# Обновление информационной панели
		self.update_info_panel()

		# Очистка карты
		self.ax.clear()
		self.ax.set_aspect('equal')
		self.ax.axis('off')

		# Динамический размер гекса на основе количества клеток
		hex_count = len(self.game_data['map'])
		self.hex_size = max(0.4, min(1.0, 15 / np.sqrt(hex_count)))

		# Отрисовка гексов
		for cell in self.game_data['map']:
			x, y = self.hex_to_cart(cell['q'], cell['r'])
			hexagon = RegularPolygon(
				(x, y), numVertices=6, radius=self.hex_size,
				orientation=np.pi / 6,
				facecolor=HEX_COLORS.get(cell['type'], '#F0F0F0'),
				edgecolor='black', alpha=0.8
			)
			self.ax.add_patch(hexagon)

			# Подписи координат
			self.ax.text(x, y, f"{cell['q']},{cell['r']}",
			             ha='center', va='center', fontsize=8, color='black')

		# Отрисовка муравейника
		for home in self.game_data['home']:
			x, y = self.hex_to_cart(home['q'], home['r'])
			home_patch = RegularPolygon(
				(x, y), numVertices=6, radius=self.hex_size * 0.9,
				facecolor='red', edgecolor='gold', linewidth=2
			)
			self.ax.add_patch(home_patch)

		# Отрисовка ресурсов
		for food in self.game_data['food']:
			x, y = self.hex_to_cart(food['q'], food['r'])
			food_patch = Circle(
				(x, y), radius=self.hex_size / 3,
				facecolor=FOOD_COLORS.get(food['type'], '#FFD700')
			)
			self.ax.add_patch(food_patch)
			self.ax.text(x, y, str(food['amount']),
			             ha='center', va='center', fontsize=8, color='white')

		# Отрисовка своих муравьев
		ant_positions = {}
		for ant in self.game_data['ants']:
			x, y = self.hex_to_cart(ant['q'], ant['r'])

			# Смещение для нескольких муравьев на одной клетке
			key = f"{ant['q']},{ant['r']}"
			offset = ant_positions.get(key, 0)
			ant_positions[key] = offset + 1
			x += offset * self.hex_size * 0.3
			y += offset * self.hex_size * 0.3

			# Цвет по типу муравья
			color = ANT_COLORS.get(ant['type'], 'green')
			ant_patch = Circle(
				(x, y), radius=self.hex_size / 2,
				facecolor=color, edgecolor='black'
			)
			self.ax.add_patch(ant_patch)

			# ID и здоровье
			ant_id_short = ant['id'].split('-')[0]
			health_percent = ant['health'] // 20  # 5 уровней здоровья
			health_bar = "■" * health_percent + "□" * (5 - health_percent)
			self.ax.text(x, y - self.hex_size * 0.6, f"{ant_id_short}\n{health_bar}",
			             ha='center', va='center', fontsize=7, color='black')

		# Отрисовка вражеских муравьев
		for enemy in self.game_data['enemies']:
			x, y = self.hex_to_cart(enemy['q'], enemy['r'])

			# Смещение для нескольких муравьев на одной клетке
			key = f"{enemy['q']},{enemy['r']}"
			offset = ant_positions.get(key, 0)
			ant_positions[key] = offset + 1
			x += offset * self.hex_size * 0.3
			y += offset * self.hex_size * 0.3

			enemy_patch = Circle(
				(x, y), radius=self.hex_size / 2,
				facecolor='red', edgecolor='black'
			)
			self.ax.add_patch(enemy_patch)
			self.ax.text(x, y - self.hex_size * 0.6, "Враг",
			             ha='center', va='center', fontsize=7, color='black')

		# Отрисовка пути
		self.draw_path()

		# Установка границ карты
		if self.game_data['map']:
			coords = [self.hex_to_cart(h['q'], h['r']) for h in self.game_data['map']]
			x, y = zip(*coords)
			margin = self.hex_size * 3
			self.ax.set_xlim(min(x) - margin, max(x) + margin)
			self.ax.set_ylim(min(y) - margin, max(y) + margin)

		# Обновление холста
		self.canvas.draw()

	def update_info_panel(self):
		"""Обновление информационной панели"""
		self.info_text.config(state=tk.NORMAL)
		self.info_text.delete(1.0, tk.END)

		# Статистика
		info = f"Муравьев: {len(self.game_data['ants'])}\n"
		info += f"Врагов: {len(self.game_data['enemies'])}\n"
		info += f"Ресурсов: {len(self.game_data['food'])}\n"
		info += f"Счет: {self.game_data['score']}\n"
		info += f"Ход: {self.game_data['turnNo']}\n"

		# Типы муравьев
		ant_types = {0: 0, 1: 0, 2: 0}
		for ant in self.game_data['ants']:
			ant_types[ant['type']] += 1

		info += "\nСостав колонии:\n"
		info += f"Рабочие: {ant_types[0]}\n"
		info += f"Солдаты: {ant_types[1]}\n"
		info += f"Разведчики: {ant_types[2]}"

		self.info_text.insert(tk.END, info)
		self.info_text.config(state=tk.DISABLED)

	def hex_to_cart(self, q, r):
		"""Преобразование гексагональных координат в декартовы"""
		x = self.hex_size * 3 / 2 * q
		y = self.hex_size * np.sqrt(3) * (r + q / 2)
		return x, y

	def cart_to_hex(self, x, y):
		"""Преобразование декартовых координат в гексагональные"""
		q = (2 / 3 * x) / self.hex_size
		r = (-1 / 3 * x + np.sqrt(3) / 3 * y) / self.hex_size
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
			# Выбор муравья
			self.selected_ant = clicked_ant
			self.path_points = []
			ant_type = ANT_TYPES.get(clicked_ant['type'], "Неизвестный")
			self.selected_ant_label.config(
				text=f"{ant_type}\nID: {clicked_ant['id'][:8]}\n"
				     f"Позиция: ({q}, {r})\n"
				     f"Здоровье: {clicked_ant['health']}"
			)
			self.path_label.config(text="Путь очищен")
		elif self.selected_ant:
			# Добавление точки в путь
			self.path_points.append({"q": q, "r": r})
			self.path_label.config(text=f"Путь: {len(self.path_points)} точек")

			# Перерисовка карты для отображения пути
			self.root.after(0, self.update_ui)

	def draw_path(self):
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

	def clear_path(self):
		"""Очистка пути"""
		self.path_points = []
		self.path_label.config(text="Путь очищен")
		if self.selected_ant:
			self.root.after(0, self.update_ui)

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
				messagebox.showinfo("Успех", "Путь движения отправлен")
				self.path_points = []
				self.path_label.config(text="Путь отправлен")
			else:
				messagebox.showerror("Ошибка", f"Статус: {response.status_code}\n{response.text}")

		except Exception as e:
			messagebox.showerror("Ошибка", str(e))

	def register(self):
		"""Регистрация команды"""
		try:
			response = requests.post(f"{BASE_URL}/register", headers=HEADERS)
			if response.status_code == 200:
				data = response.json()
				message = f"Регистрация успешна!\nИмя: {data['name']}\n"
				message += f"След. ход через: {data['nextTurn']} сек"
				messagebox.showinfo("Успех", message)
			else:
				messagebox.showerror("Ошибка", f"Статус: {response.status_code}\n{response.text}")
		except Exception as e:
			messagebox.showerror("Ошибка", str(e))

	def get_logs(self):
		"""Получение журнала событий"""
		try:
			response = requests.get(f"{BASE_URL}/logs", headers=HEADERS)
			if response.status_code == 200:
				self.log_text.delete(1.0, tk.END)
				for log in response.json():
					self.log_text.insert(tk.END, f"{log['time']}: {log['message']}\n")
			else:
				messagebox.showerror("Ошибка", f"Статус: {response.status_code}\n{response.text}")
		except Exception as e:
			messagebox.showerror("Ошибка", str(e))


if __name__ == "__main__":
	root = tk.Tk()
	app = HexMapApp(root)
	root.mainloop()