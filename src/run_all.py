import os
import subprocess
import sys
import time

def run_all(configs_dir="configs", delay=2):
    # Создаём папку для логов, если её нет
    log_dir = "log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    config_files = sorted([f for f in os.listdir(configs_dir) if f.endswith(".json")])
    if not config_files:
        print("Нет конфигов в папке configs. Сначала запустите generate_configs.py")
        return

    processes = []
    print(f"Найдено {len(config_files)} конфигов. Запускаю ботов...")
    for i, cf in enumerate(config_files):
        full_path = os.path.join(configs_dir, cf)
        # Путь к файлу лога внутри папки log
        log_file_path = os.path.join(log_dir, f"bot_{i+1:02d}.log")
        log_file = open(log_file_path, "w", encoding="utf-8")

        # Устанавливаем кодировку для вывода в подпроцессе
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        proc = subprocess.Popen(
            [sys.executable, "main.py", full_path],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            env=env
        )
        processes.append((proc, log_file))
        print(f"Запущен бот #{i+1:02d} с конфигом {cf} (PID {proc.pid})")
        time.sleep(delay)

    print("\nВсе боты запущены. Для остановки всех нажмите Ctrl+C")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nОстанавливаю всех ботов...")
        for proc, logf in processes:
            proc.terminate()
            proc.wait()
            logf.close()
        print("Все боты остановлены.")

if __name__ == "__main__":
    run_all()