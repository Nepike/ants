
# 1. Как поднять сайт у себя?
## 1.1 Зависимости
- Python 3.11+


## 1.2 Windows 10
```powershell
# Клонирование репозитория
git clone https://github.com/Nepike/ants

# Создание и активация виртуального окружения Python
python -m venv virtualenv
.\virtualenv\Scripts\activate

# Установка нужных пакетов Python
pip install -r requirements.txt

# Создание файла конфигурации
cp config_sample.py config.py

# Запуск:
python .\main.py

```


# 2. Файл конфигурации (config.yml)
### 2.1 TOKEN
