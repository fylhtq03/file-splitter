# -*- coding: utf-8 -*-
import os
import argparse
import threading
import queue
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

def calculate_file_hash(file_path, buffer_size=8192):
    """Вычисление хеша файла для проверки целостности с буферизацией"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(buffer_size), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def split_file(file_path, chunk_size, verify_hash=False, buffer_size=8192):
    """
    Дробление файла на части указанного размера с буферизацией
    """
    if not os.path.exists(file_path):
        print(f"Ошибка: Файл '{file_path}' не найден.")
        return
    
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        print("Ошибка: Файл пустой.")
        return
    
    # Вычисляем хеш исходного файла если нужно
    file_hash = None
    if verify_hash:
        print("Вычисление хеша исходного файла...")
        file_hash = calculate_file_hash(file_path)
        print(f"Хеш файла: {file_hash}")
    
    # Создаем папку для частей файла
    base_name = os.path.basename(file_path)
    output_dir = f"{base_name}_parts"
    os.makedirs(output_dir, exist_ok=True)
    
    # Читаем и записываем части файла с буферизацией
    part_num = 1
    bytes_written = 0
    
    with open(file_path, 'rb') as source_file:
        while bytes_written < file_size:
            part_filename = os.path.join(output_dir, f"{base_name}.part{part_num:03d}")
            
            with open(part_filename, 'wb') as part_file:
                remaining = chunk_size
                while remaining > 0 and bytes_written < file_size:
                    # Читаем кусками, не более buffer_size
                    read_size = min(buffer_size, remaining, file_size - bytes_written)
                    chunk = source_file.read(read_size)
                    if not chunk:
                        break
                    
                    part_file.write(chunk)
                    bytes_written += len(chunk)
                    remaining -= len(chunk)
            
            part_size = os.path.getsize(part_filename)
            print(f"Создана часть: {part_filename} ({part_size} байт)")
            part_num += 1
    
    # Создаем файл с информацией для сборки
    info_file = os.path.join(output_dir, f"{base_name}.info")
    with open(info_file, 'w') as f:
        f.write(f"original_name:{base_name}\n")
        f.write(f"parts_count:{part_num-1}\n")
        f.write(f"original_size:{file_size}\n")
        f.write(f"chunk_size:{chunk_size}\n")
        if file_hash:
            f.write(f"original_hash:{file_hash}\n")
    
    print(f"\nФайл разделен на {part_num-1} частей в папке '{output_dir}'")

def read_part_worker_streaming(part_info, result_queue, buffer_size=8192):
    """Рабочая функция для потокового чтения части файла"""
    part_num, part_filename, position, part_size = part_info
    try:
        # Вместо загрузки всего файла в память, читаем и передаем чанками
        with open(part_filename, 'rb') as part_file:
            bytes_read = 0
            while bytes_read < part_size:
                chunk = part_file.read(min(buffer_size, part_size - bytes_read))
                if not chunk:
                    break
                
                # Передаем чанк с информацией о позиции
                chunk_position = position + bytes_read
                result_queue.put((part_num, chunk_position, chunk, None))
                bytes_read += len(chunk)
        
        # Сигнализируем о завершении чтения этой части
        result_queue.put((part_num, None, None, "COMPLETED"))
        print(f"Прочитана часть: {part_filename}")
    except Exception as e:
        result_queue.put((part_num, None, None, str(e)))

def write_part_worker_streaming(output_file, write_queue, total_parts, buffer_size=8192):
    """Рабочая функция для потоковой записи чанков в конечный файл"""
    completed_parts = 0
    part_status = {}  # Отслеживаем статус частей
    
    with open(output_file, 'r+b') as output:
        while completed_parts < total_parts:
            try:
                part_num, position, data, error = write_queue.get(timeout=30)
                
                if error == "COMPLETED":
                    # Часть полностью прочитана
                    completed_parts += 1
                    print(f"Завершена обработка части {part_num} ({completed_parts}/{total_parts})")
                    continue
                
                if error:
                    print(f"Ошибка при обработке части {part_num}: {error}")
                    continue
                
                # Записываем чанк в правильную позицию
                output.seek(position)
                output.write(data)
                
            except queue.Empty:
                print("Таймаут при ожидании данных для записи")
                break
    
    print(f"Запись завершена. Обработано частей: {completed_parts}/{total_parts}")

def join_files_multithreaded_streaming(parts_directory, output_file=None, max_workers=None, buffer_size=8192):
    """
    Многопоточная сборка файла из частей с потоковой обработкой
    """
    if not os.path.exists(parts_directory):
        print(f"Ошибка: Папка '{parts_directory}' не найдена.")
        return
    
    # Ищем файл с информацией
    info_files = [f for f in os.listdir(parts_directory) if f.endswith('.info')]
    if not info_files:
        print("Ошибка: Не найден файл с информацией для сборки.")
        return
    
    info_file_path = os.path.join(parts_directory, info_files[0])
    
    # Читаем информацию о файле
    original_name = None
    parts_count = 0
    original_size = 0
    chunk_size = 0
    original_hash = None
    
    with open(info_file_path, 'r') as f:
        for line in f:
            if line.startswith('original_name:'):
                original_name = line.split(':', 1)[1].strip()
            elif line.startswith('parts_count:'):
                parts_count = int(line.split(':', 1)[1].strip())
            elif line.startswith('original_size:'):
                original_size = int(line.split(':', 1)[1].strip())
            elif line.startswith('chunk_size:'):
                chunk_size = int(line.split(':', 1)[1].strip())
            elif line.startswith('original_hash:'):
                original_hash = line.split(':', 1)[1].strip()
    
    if not original_name or parts_count == 0:
        print("Ошибка: Неверный формат файла информации.")
        return
    
    # Определяем имя выходного файла
    if not output_file:
        output_file = original_name
    
    # Создаем файл нужного размера
    with open(output_file, 'wb') as f:
        f.truncate(original_size)
    
    print(f"Начата многопоточная сборка {parts_count} частей с потоковой обработкой...")
    
    # Создаем очередь для записи
    write_queue = queue.Queue()
    
    # Подготавливаем информацию о частях
    part_infos = []
    for i in range(1, parts_count + 1):
        part_filename = os.path.join(parts_directory, f"{original_name}.part{i:03d}")
        if not os.path.exists(part_filename):
            print(f"Ошибка: Не найдена часть {part_filename}")
            return
        
        part_size = os.path.getsize(part_filename)
        position = (i - 1) * chunk_size
        part_infos.append((i, part_filename, position, part_size))
    
    # Запускаем поток для записи
    writer_thread = threading.Thread(
        target=write_part_worker_streaming, 
        args=(output_file, write_queue, parts_count, buffer_size)
    )
    writer_thread.daemon = True
    writer_thread.start()
    
    # Запускаем потоки для чтения частей
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Отправляем все задачи на чтение
        future_to_part = {
            executor.submit(read_part_worker_streaming, part_info, write_queue, buffer_size): part_info 
            for part_info in part_infos
        }
        
        # Обрабатываем завершенные задачи чтения
        completed = 0
        for future in as_completed(future_to_part):
            part_info = future_to_part[future]
            try:
                future.result()
                completed += 1
            except Exception as e:
                print(f"Ошибка при чтении части {part_info[0]}: {e}")
        
        print(f"Все задачи чтения завершены: {completed}/{parts_count}")
    
    # Ждем завершения потока записи
    writer_thread.join(timeout=60)
    
    print(f"\nФайл собран: {output_file}")
    print(f"Размер: {os.path.getsize(output_file)} байт")
    
    # Проверяем целостность если есть хеш
    if original_hash:
        print("Проверка целостности...")
        current_hash = calculate_file_hash(output_file)
        if current_hash == original_hash:
            print("✓ Целостность файла проверена успешно")
        else:
            print("✗ Ошибка: Целостность файла нарушена!")
            print(f"  Ожидаемый хеш: {original_hash}")
            print(f"  Полученный хеш: {current_hash}")

def join_files_single_streaming(parts_directory, output_file=None, buffer_size=8192):
    """
    Однопоточная сборка файла из частей с потоковой обработкой
    """
    if not os.path.exists(parts_directory):
        print(f"Ошибка: Папка '{parts_directory}' не найдена.")
        return
    
    # Ищем файл с информацией
    info_files = [f for f in os.listdir(parts_directory) if f.endswith('.info')]
    if not info_files:
        print("Ошибка: Не найден файл с информацией для сборки.")
        return
    
    info_file_path = os.path.join(parts_directory, info_files[0])
    
    # Читаем информацию о файле
    original_name = None
    parts_count = 0
    original_size = 0
    chunk_size = 0
    original_hash = None
    
    with open(info_file_path, 'r') as f:
        for line in f:
            if line.startswith('original_name:'):
                original_name = line.split(':', 1)[1].strip()
            elif line.startswith('parts_count:'):
                parts_count = int(line.split(':', 1)[1].strip())
            elif line.startswith('original_size:'):
                original_size = int(line.split(':', 1)[1].strip())
            elif line.startswith('chunk_size:'):
                chunk_size = int(line.split(':', 1)[1].strip())
            elif line.startswith('original_hash:'):
                original_hash = line.split(':', 1)[1].strip()
    
    if not original_name or parts_count == 0:
        print("Ошибка: Неверный формат файла информации.")
        return
    
    # Определяем имя выходного файла
    if not output_file:
        output_file = original_name
    
    print(f"Начата однопоточная сборка {parts_count} частей с потоковой обработкой...")
    
    # Создаем выходной файл
    with open(output_file, 'wb') as output:
        # Устанавливаем размер файла
        output.truncate(original_size)
    
    # Собираем файл с буферизацией
    with open(output_file, 'r+b') as output:
        for i in range(1, parts_count + 1):
            part_filename = os.path.join(parts_directory, f"{original_name}.part{i:03d}")
            
            if not os.path.exists(part_filename):
                print(f"Ошибка: Не найдена часть {part_filename}")
                return
            
            position = (i - 1) * chunk_size
            output.seek(position)
            
            with open(part_filename, 'rb') as part_file:
                bytes_copied = 0
                while True:
                    chunk = part_file.read(buffer_size)
                    if not chunk:
                        break
                    output.write(chunk)
                    bytes_copied += len(chunk)
            
            print(f"Добавлена часть: {part_filename} ({bytes_copied} байт)")
    
    print(f"\nФайл собран: {output_file}")
    print(f"Размер: {os.path.getsize(output_file)} байт")
    
    # Проверяем целостность если есть хеш
    if original_hash:
        print("Проверка целостности...")
        current_hash = calculate_file_hash(output_file)
        if current_hash == original_hash:
            print("✓ Целостность файла проверена успешно")
        else:
            print("✗ Ошибка: Целостность файла нарушена!")

def main():
    parser = argparse.ArgumentParser(description='Дробление и сборка файлов с потоковой обработкой')
    subparsers = parser.add_subparsers(dest='command', help='Команда')
    
    # Парсер для дробления
    split_parser = subparsers.add_parser('split', help='Дробление файла на части')
    split_parser.add_argument('file', help='Путь к файлу для дробления')
    split_parser.add_argument('size', type=int, help='Размер части в байтах')
    split_parser.add_argument('--verify-hash', action='store_true', 
                            help='Вычислять и проверять хеш файла')
    split_parser.add_argument('--buffer-size', type=int, default=8192,
                            help='Размер буфера для чтения/записи (по умолчанию 8192)')
    
    # Парсер для сборки
    join_parser = subparsers.add_parser('join', help='Сборка файла из частей')
    join_parser.add_argument('directory', help='Папка с частями файла')
    join_parser.add_argument('-o', '--output', help='Имя выходного файла')
    join_parser.add_argument('-t', '--threads', type=int, default=0,
                           help='Количество потоков для сборки (0 для однопоточной)')
    join_parser.add_argument('--buffer-size', type=int, default=8192,
                           help='Размер буфера для чтения/записи (по умолчанию 8192)')
    
    args = parser.parse_args()
    
    if args.command == 'split':
        split_file(args.file, args.size, args.verify_hash, args.buffer_size)
    elif args.command == 'join':
        if args.threads == 0:
            join_files_single_streaming(args.directory, args.output, args.buffer_size)
        else:
            join_files_multithreaded_streaming(args.directory, args.output, args.threads, args.buffer_size)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()