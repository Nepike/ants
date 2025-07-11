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
from matplotlib.offsetbox import AnchoredText
from matplotlib.font_manager import FontProperties

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

# Типы ресурсов
FOOD_TYPES = {
	0: "Нектар",
	1: "Падь",
	2: "Семена"
}


class HexMapApp:
	def __init__(self, root):
		self.root = root
		self.root.title("DatsPulse Ants Viewer")
		self.root.geometry("1600x1000")
		self.root.state('zoomed')  # Открыть в полноэкранном режиме

		# Переменные состояния
		self.selected_ant = None
		self.path_points = []
		self.last_update = "Не обновлялось"
		self.hex_size = 0.5  # Начальный размер гекса
		self.ant_info_window = None
		self.last_log_update = 0

		# Основные фреймы
		self.top_frame = ttk.Frame(root)
		self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

		self.left_frame = ttk.Frame(root, width=300)
		self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

		self.right_frame = ttk.Frame(root)
		self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

		# Инициализация компонентов
		self.init_top_panel()
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

	def init_top_panel(self):
		"""Инициализация верхней панели"""
		# Информация о ходе
		turn_frame = ttk.LabelFrame(self.top_frame, text="Информация о ходе", padding=10)
		turn_frame.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=5, expand=True)

		self.turn_var = tk.StringVar()
		self.turn_var.set("Ожидание данных...")
		ttk.Label(turn_frame, textvariable=self.turn_var, font=("Arial", 12)).pack()

		# Информация о счете
		score_frame = ttk.LabelFrame(self.top_frame, text="Счет", padding=10)
		score_frame.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=5)

		self.score_var = tk.StringVar()
		self.score_var.set("0")
		ttk.Label(score_frame, textvariable=self.score_var, font=("Arial", 14, "bold")).pack()

		# Кнопка регистрации
		reg_frame = ttk.Frame(self.top_frame)
		reg_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
		ttk.Button(reg_frame, text="Зарегистрироваться", command=self.register,
		           style="Accent.TButton").pack(fill=tk.X)

	def init_controls(self):
		"""Инициализация панели управления"""
		# Информационная панель
		info_frame = ttk.LabelFrame(self.left_frame, text="Детали муравья", padding=10)
		info_frame.pack(fill=tk.X, pady=5)

		self.info_text = tk.Text(info_frame, height=10, width=30, font=("Arial", 10))
		self.info_text.pack(fill=tk.X)
		self.info_text.insert(tk.END, "Кликните на муравья для просмотра информации")
		self.info_text.config(state=tk.DISABLED)

		# Журнал событий
		log_frame = ttk.LabelFrame(self.left_frame, text="Журнал событий", padding=10)
		log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

		self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Arial", 9))
		self.log_text.pack(fill=tk.BOTH, expand=True)

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

	def init_map(self):
		"""Инициализация карты"""
		self.fig, self.ax = plt.subplots(figsize=(14, 10))
		self.ax.set_aspect('equal')
		self.ax.axis('off')
		self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
		self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

		# Подключение обработчиков событий
		self.canvas.mpl_connect('button_press_event', self.on_map_click)
		self.canvas.mpl_connect('motion_notify_event', self.on_map_hover)

	def update_game_data(self):
		"""Поток для обновления данных игры"""
		while True:
			try:
				response = requests.get(f"{BASE_URL}/arena", headers=HEADERS)
				if response.status_code == 200:
					self.game_data = response.json()
					self.last_update = datetime.datetime.now().strftime("%H:%M:%S")
					self.root.after(0, self.update_ui)

					# Обновление журнала раз в 5 секунд
					current_time = time.time()
					if current_time - self.last_log_update > 5:
						self.get_logs()
						self.last_log_update = current_time
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

			# Подписи координат (маленькие, в верхней части)
			self.ax.text(x, y + self.hex_size * 0.5, f"{cell['q']},{cell['r']}",
			             ha='center', va='center', fontsize=6, color='black')

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

			# ID (короткий)
			ant_id_short = ant['id'].split('-')[0]
			self.ax.text(x, y, ant_id_short,
			             ha='center', va='center', fontsize=7, color='white')

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
			self.ax.text(x, y, "E",
			             ha='center', va='center', fontsize=7, color='white')

		# Отрисовка пути
		self.draw_path()

		# Добавление легенды на карту
		self.add_legend_to_map()

		# Установка границ карты
		if self.game_data['map']:
			coords = [self.hex_to_cart(h['q'], h['r']) for h in self.game_data['map']]
			x, y = zip(*coords)
			margin = self.hex_size * 3
			self.ax.set_xlim(min(x) - margin, max(x) + margin)
			self.ax.set_ylim(min(y) - margin, max(y) + margin)

		# Обновление холста
		self.canvas.draw()

	def add_legend_to_map(self):
		"""Добавление легенды на карту"""
		legend_text = (
			"Легенда:\n"
			"Гексы: Пустой, Грязь, Камень, Кислота, Муравейник\n"
			"Муравьи: Рабочий (зел), Солдат (син), Разведчик (фиол), Враг (крас)\n"
			"Ресурсы: Нектар (зол), Падь (крас), Семена (корич)"
		)

		# Создаем аннотацию с легендой
		anchored_text = AnchoredText(
			legend_text,
			loc='upper left',
			frameon=True,
			prop=dict(size=9, family='monospace')
		)
		anchored_text.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
		anchored_text.patch.set_alpha(0.8)
		self.ax.add_artist(anchored_text)

		# Добавляем информацию о ходе внизу
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
			self.root.after(0, self.update_ui)

	def on_map_hover(self, event):
		"""Обработчик наведения курсора на карту"""
		if event.xdata is None or event.ydata is None:
			return

		# Определяем гекс под курсором
		q, r = self.cart_to_hex(event.xdata, event.ydata)

		# Проверяем, есть ли муравей на этом гексе
		hover_ant = None
		for ant in self.game_data['ants']:
			if ant['q'] == q and ant['r'] == r:
				hover_ant = ant
				break

		if hover_ant:
			# Показываем подсказку с краткой информацией
			ant_type = ANT_TYPES.get(hover_ant['type'], "Неизвестный")
			health = hover_ant['health']
			ant_id_short = hover_ant['id'].split('-')[0]

			# Отображаем подсказку рядом с курсором
			self.ax.annotate(
				f"{ant_type} {ant_id_short}\nHP: {health}",
				xy=(event.xdata, event.ydata),
				xytext=(10, 10),
				textcoords='offset points',
				bbox=dict(boxstyle="round,pad=0.5", facecolor='white', alpha=0.9),
				arrowprops=dict(arrowstyle="->")
			)
			self.canvas.draw_idle()

	def show_ant_info(self, ant):
		"""Отображение информации о муравье"""
		# Очищаем предыдущую информацию
		self.info_text.config(state=tk.NORMAL)
		self.info_text.delete(1.0, tk.END)

		# Собираем информацию
		ant_type = ANT_TYPES.get(ant['type'], "Неизвестный")
		health = ant['health']
		food_type = FOOD_TYPES.get(ant['food']['type'], "Нет")
		food_amount = ant['food']['amount']
		ant_id = ant['id']
		position = f"{ant['q']},{ant['r']}"

		# Форматируем информацию
		info = f"Тип: {ant_type}\n\n"
		info += f"Здоровье: {health}\n\n"
		info += f"Ресурсы: {food_type} ({food_amount})\n\n"
		info += f"Позиция: {position}\n\n"
		info += f"ID: {ant_id}"

		# Вставляем информацию
		self.info_text.insert(tk.END, info)
		self.info_text.config(state=tk.DISABLED)

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
				# Прокрутка вниз
				self.log_text.see(tk.END)
		except Exception as e:
			# Не показываем ошибку в сообщении, чтобы не мешать
			self.status_var.set(f"Ошибка журнала: {str(e)}")


if __name__ == "__main__":
	root = tk.Tk()

	# Стилизация интерфейса
	style = ttk.Style()
	style.configure("Accent.TButton", foreground="white", background="#4CAF50", font=("Arial", 10, "bold"))

	app = HexMapApp(root)
	root.mainloop()