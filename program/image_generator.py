"""
Модуль для генерации математических изображений на лету
Создает графики функций, диаграммы и визуализации для обучения математике
"""

import matplotlib
matplotlib.use('Agg')  # Используем backend без GUI

# Отключаем предупреждения matplotlib о шрифтах
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

import matplotlib.pyplot as plt
import numpy as np
import io
import os
import tempfile
from typing import Optional, Tuple, List
from colorama import Fore, Style, init

init(autoreset=True)

class MathImageGenerator:
    """Генератор математических изображений"""
    
    def __init__(self):
        """Инициализация генератора"""
        # Настройка matplotlib для русского языка (Windows-совместимые шрифты)
        import platform
        if platform.system() == "Windows":
            # Шрифты, которые точно есть в Windows
            plt.rcParams['font.family'] = ['Segoe UI', 'Tahoma', 'Arial', 'sans-serif']
        else:
            # Для Linux/Mac
            plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Liberation Sans']
        
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['figure.figsize'] = (10, 8)
        plt.rcParams['figure.dpi'] = 100
        
        # Создаем временную папку для изображений
        self.temp_dir = tempfile.mkdtemp(prefix='mathbot_images_')
        
        # Проверяем и настраиваем лучшие доступные шрифты
        self._setup_best_fonts()
        
        print(f"{Fore.GREEN}📊 [IMAGE GEN]{Style.RESET_ALL} Инициализирован генератор изображений, папка: {self.temp_dir}")
    
    def _setup_best_fonts(self):
        """Настраивает лучшие доступные шрифты для русского языка"""
        try:
            import matplotlib.font_manager as fm
            
            # Список предпочтительных шрифтов (в порядке приоритета)
            preferred_fonts = [
                'Segoe UI',           # Windows 10/11 по умолчанию
                'Tahoma',             # Старые версии Windows  
                'Verdana',            # Широко доступен
                'Arial',              # Классический
                'Calibri',            # Современный Windows
                'Times New Roman',    # Универсальный
                'DejaVu Sans',        # Linux
                'Liberation Sans',    # Linux альтернатива
                'Arial Unicode MS'    # Mac/старые системы
            ]
            
            # Получаем список всех доступных шрифтов
            available_fonts = [f.name for f in fm.fontManager.ttflist]
            
            # Ищем первый доступный шрифт из предпочтительных
            best_font = None
            for font in preferred_fonts:
                if font in available_fonts:
                    best_font = font
                    break
            
            if best_font:
                plt.rcParams['font.family'] = [best_font]
                self._log(f"Используется шрифт: {best_font}", "SUCCESS")
            else:
                # Откатываемся к системному шрифту по умолчанию
                plt.rcParams['font.family'] = ['sans-serif']
                self._log("Использую системный шрифт по умолчанию", "WARNING")
                
            # Дополнительная настройка для кириллицы
            plt.rcParams['font.sans-serif'] = plt.rcParams['font.family'] + ['DejaVu Sans', 'Tahoma', 'Arial']
            
        except Exception as e:
            self._log(f"Ошибка настройки шрифтов: {e}", "ERROR")
            # Безопасная настройка по умолчанию
            plt.rcParams['font.family'] = ['sans-serif']
    
    def _log(self, message: str, level: str = "INFO"):
        """Логирование для генератора изображений"""
        try:
            if level == "INFO": 
                color, emoji = Fore.CYAN, "📊"
            elif level == "ERROR": 
                color, emoji = Fore.RED, "❌"
            elif level == "SUCCESS": 
                color, emoji = Fore.GREEN, "✅"
            else: 
                color, emoji = Fore.WHITE, "📝"
            
            print(f"{color}[{emoji} IMAGE GEN]{Style.RESET_ALL} {message}")
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка логирования изображений: {e}{Style.RESET_ALL}")
    
    def generate_trigonometric_circle(self) -> Optional[str]:
        """Генерирует изображение тригонометрической окружности"""
        try:
            self._log("Генерация тригонометрической окружности")
            
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            
            # Создаем единичную окружность
            theta = np.linspace(0, 2*np.pi, 100)
            x_circle = np.cos(theta)
            y_circle = np.sin(theta)
            
            # Рисуем окружность
            ax.plot(x_circle, y_circle, 'b-', linewidth=2, label='Единичная окружность')
            
            # Оси координат
            ax.axhline(y=0, color='k', linewidth=1)
            ax.axvline(x=0, color='k', linewidth=1)
            
            # Основные углы
            angles = [0, np.pi/6, np.pi/4, np.pi/3, np.pi/2, 2*np.pi/3, 3*np.pi/4, 5*np.pi/6, np.pi]
            angle_labels = ['0°', '30°', '45°', '60°', '90°', '120°', '135°', '150°', '180°']
            
            for angle, label in zip(angles, angle_labels):
                x = np.cos(angle)
                y = np.sin(angle)
                ax.plot(x, y, 'ro', markersize=8)
                
                # Подписи углов
                offset = 0.15
                ax.annotate(label, (x + offset*np.cos(angle), y + offset*np.sin(angle)), 
                          fontsize=10, ha='center', va='center')
                
                # Линии к точкам
                ax.plot([0, x], [0, y], 'r--', alpha=0.5, linewidth=1)
            
            # Подписи осей
            ax.text(1.1, 0, 'cos θ', fontsize=12, ha='center', va='bottom')
            ax.text(0, 1.1, 'sin θ', fontsize=12, ha='right', va='center')
            
            # Настройка осей
            ax.set_xlim(-1.3, 1.3)
            ax.set_ylim(-1.3, 1.3)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            ax.set_title('Тригонометрическая окружность', fontsize=16, fontweight='bold')
            
            # Сохраняем изображение
            filename = os.path.join(self.temp_dir, 'trigonometric_circle.png')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            self._log(f"Тригонометрическая окружность сохранена: {filename}", "SUCCESS")
            return filename
            
        except Exception as e:
            self._log(f"Ошибка генерации тригонометрической окружности: {e}", "ERROR")
            return None
    
    def generate_trigonometric_functions(self) -> Optional[str]:
        """Генерирует графики основных тригонометрических функций"""
        try:
            self._log("Генерация графиков тригонометрических функций")
            
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('Основные тригонометрические функции', fontsize=16, fontweight='bold')
            
            x = np.linspace(-2*np.pi, 2*np.pi, 1000)
            
            # sin(x)
            axes[0,0].plot(x, np.sin(x), 'b-', linewidth=2, label='y = sin(x)')
            axes[0,0].set_title('Синус', fontweight='bold')
            axes[0,0].grid(True, alpha=0.3)
            axes[0,0].set_ylim(-1.5, 1.5)
            axes[0,0].axhline(y=0, color='k', linewidth=0.8)
            axes[0,0].axvline(x=0, color='k', linewidth=0.8)
            
            # cos(x)
            axes[0,1].plot(x, np.cos(x), 'r-', linewidth=2, label='y = cos(x)')
            axes[0,1].set_title('Косинус', fontweight='bold')
            axes[0,1].grid(True, alpha=0.3)
            axes[0,1].set_ylim(-1.5, 1.5)
            axes[0,1].axhline(y=0, color='k', linewidth=0.8)
            axes[0,1].axvline(x=0, color='k', linewidth=0.8)
            
            # tan(x)
            x_tan = np.linspace(-2*np.pi, 2*np.pi, 1000)
            y_tan = np.tan(x_tan)
            # Убираем разрывы
            y_tan[np.abs(y_tan) > 10] = np.nan
            axes[1,0].plot(x_tan, y_tan, 'g-', linewidth=2, label='y = tan(x)')
            axes[1,0].set_title('Тангенс', fontweight='bold')
            axes[1,0].grid(True, alpha=0.3)
            axes[1,0].set_ylim(-5, 5)
            axes[1,0].axhline(y=0, color='k', linewidth=0.8)
            axes[1,0].axvline(x=0, color='k', linewidth=0.8)
            
            # Асимптоты для тангенса
            for k in range(-2, 3):
                axes[1,0].axvline(x=np.pi/2 + k*np.pi, color='r', linestyle='--', alpha=0.5)
            
            # cot(x)
            x_cot = np.linspace(-2*np.pi, 2*np.pi, 1000)
            y_cot = 1/np.tan(x_cot)
            y_cot[np.abs(y_cot) > 10] = np.nan
            axes[1,1].plot(x_cot, y_cot, 'm-', linewidth=2, label='y = cot(x)')
            axes[1,1].set_title('Котангенс', fontweight='bold')
            axes[1,1].grid(True, alpha=0.3)
            axes[1,1].set_ylim(-5, 5)
            axes[1,1].axhline(y=0, color='k', linewidth=0.8)
            axes[1,1].axvline(x=0, color='k', linewidth=0.8)
            
            # Асимптоты для котангенса
            for k in range(-2, 3):
                axes[1,1].axvline(x=k*np.pi, color='r', linestyle='--', alpha=0.5)
            
            # Настройка всех осей
            for ax in axes.flat:
                ax.set_xlabel('x (радианы)')
                ax.set_ylabel('y')
                
                # Отметки на оси X
                pi_ticks = [-2*np.pi, -np.pi, -np.pi/2, 0, np.pi/2, np.pi, 2*np.pi]
                pi_labels = ['-2π', '-π', '-π/2', '0', 'π/2', 'π', '2π']
                ax.set_xticks(pi_ticks)
                ax.set_xticklabels(pi_labels)
            
            plt.tight_layout()
            
            # Сохраняем изображение
            filename = os.path.join(self.temp_dir, 'trigonometric_functions.png')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            self._log(f"Графики тригонометрических функций сохранены: {filename}", "SUCCESS")
            return filename
            
        except Exception as e:
            self._log(f"Ошибка генерации графиков тригонометрических функций: {e}", "ERROR")
            return None
    
    def generate_function_graph(self, function_type: str, params: dict = None) -> Optional[str]:
        """Генерирует график конкретной функции"""
        try:
            self._log(f"Генерация графика функции: {function_type}")
            
            fig, ax = plt.subplots(1, 1, figsize=(12, 8))
            
            if function_type == "linear":
                # Линейная функция y = kx + b
                k = params.get('k', 1) if params else 1
                b = params.get('b', 0) if params else 0
                
                x = np.linspace(-10, 10, 100)
                y = k * x + b
                
                ax.plot(x, y, 'b-', linewidth=2, label=f'y = {k}x + {b}')
                ax.set_title(f'Линейная функция: y = {k}x + {b}', fontweight='bold')
                
            elif function_type == "quadratic":
                # Квадратичная функция y = ax² + bx + c
                a = params.get('a', 1) if params else 1
                b = params.get('b', 0) if params else 0
                c = params.get('c', 0) if params else 0
                
                x = np.linspace(-10, 10, 100)
                y = a * x**2 + b * x + c
                
                ax.plot(x, y, 'r-', linewidth=2, label=f'y = {a}x² + {b}x + {c}')
                ax.set_title(f'Квадратичная функция: y = {a}x² + {b}x + {c}', fontweight='bold')
                
                # Вершина параболы
                x_vertex = -b / (2*a) if a != 0 else 0
                y_vertex = a * x_vertex**2 + b * x_vertex + c
                ax.plot(x_vertex, y_vertex, 'ro', markersize=8, label=f'Вершина ({x_vertex:.1f}, {y_vertex:.1f})')
                
            elif function_type == "hyperbola":
                # Гипербола y = k/x
                k = params.get('k', 1) if params else 1
                
                x_pos = np.linspace(0.1, 10, 100)
                x_neg = np.linspace(-10, -0.1, 100)
                y_pos = k / x_pos
                y_neg = k / x_neg
                
                ax.plot(x_pos, y_pos, 'g-', linewidth=2, label=f'y = {k}/x')
                ax.plot(x_neg, y_neg, 'g-', linewidth=2)
                ax.set_title(f'Гипербола: y = {k}/x', fontweight='bold')
                
                # Асимптоты
                ax.axhline(y=0, color='r', linestyle='--', alpha=0.5, label='Асимптоты')
                ax.axvline(x=0, color='r', linestyle='--', alpha=0.5)
                
            elif function_type == "absolute":
                # Модуль y = |x|
                x = np.linspace(-10, 10, 100)
                y = np.abs(x)
                
                ax.plot(x, y, 'm-', linewidth=2, label='y = |x|')
                ax.set_title('Функция модуля: y = |x|', fontweight='bold')
                
            elif function_type == "sqrt":
                # Квадратный корень y = √x
                x = np.linspace(0, 10, 100)
                y = np.sqrt(x)
                
                ax.plot(x, y, 'orange', linewidth=2, label='y = √x')
                ax.set_title('Квадратный корень: y = √x', fontweight='bold')
            
            # Настройка осей
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color='k', linewidth=0.8)
            ax.axvline(x=0, color='k', linewidth=0.8)
            ax.set_xlabel('x')
            ax.set_ylabel('y')
            ax.legend()
            
            # Сохраняем изображение
            filename = os.path.join(self.temp_dir, f'graph_{function_type}.png')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            self._log(f"График функции {function_type} сохранен: {filename}", "SUCCESS")
            return filename
            
        except Exception as e:
            self._log(f"Ошибка генерации графика функции {function_type}: {e}", "ERROR")
            return None
    
    def generate_multiple_graphs(self) -> Optional[str]:
        """Генерирует сравнительные графики различных функций"""
        try:
            self._log("Генерация сравнительных графиков функций")
            
            fig, ax = plt.subplots(1, 1, figsize=(14, 10))
            
            x = np.linspace(-5, 5, 1000)
            
            # Различные функции
            functions = [
                (x, 'линейная', 'b-'),
                (x**2, 'квадратичная', 'r-'),
                (x**3, 'кубическая', 'g-'),
                (np.abs(x), 'модуль', 'm-'),
            ]
            
            for y_vals, name, style in functions:
                ax.plot(x, y_vals, style, linewidth=2, label=f'y = {name}')
            
            # Квадратный корень (только для x >= 0)
            x_sqrt = np.linspace(0, 5, 100)
            ax.plot(x_sqrt, np.sqrt(x_sqrt), 'orange', linewidth=2, label='y = √x')
            
            # Гипербола
            x_hyp_pos = np.linspace(0.1, 5, 100)
            x_hyp_neg = np.linspace(-5, -0.1, 100)
            ax.plot(x_hyp_pos, 1/x_hyp_pos, 'cyan', linewidth=2, label='y = 1/x')
            ax.plot(x_hyp_neg, 1/x_hyp_neg, 'cyan', linewidth=2)
            
            ax.set_title('Сравнение различных типов функций', fontsize=16, fontweight='bold')
            ax.set_xlabel('x')
            ax.set_ylabel('y')
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color='k', linewidth=0.8)
            ax.axvline(x=0, color='k', linewidth=0.8)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.set_xlim(-5, 5)
            ax.set_ylim(-5, 5)
            
            plt.tight_layout()
            
            # Сохраняем изображение
            filename = os.path.join(self.temp_dir, 'multiple_graphs.png')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            self._log(f"Сравнительные графики сохранены: {filename}", "SUCCESS")
            return filename
            
        except Exception as e:
            self._log(f"Ошибка генерации сравнительных графиков: {e}", "ERROR")
            return None
    
    # ====== ГЕОМЕТРИЧЕСКИЕ ФИГУРЫ ======
    
    def generate_triangles_diagram(self) -> Optional[str]:
        """Генерирует диаграмму с различными типами треугольников"""
        try:
            self._log("Генерация диаграммы треугольников")
            
            fig, axes = plt.subplots(2, 3, figsize=(15, 10))
            fig.suptitle('Типы треугольников', fontsize=16, fontweight='bold')
            
            # Равносторонний треугольник
            ax = axes[0,0]
            h = np.sqrt(3)/2
            triangle_eq = np.array([[0, 0.5, 1, 0], [0, h, 0, 0]])
            ax.plot(triangle_eq[0], triangle_eq[1], 'b-', linewidth=2)
            ax.fill(triangle_eq[0][:-1], triangle_eq[1][:-1], alpha=0.3, color='blue')
            ax.set_title('Равносторонний\n(все стороны равны)')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Равнобедренный треугольник
            ax = axes[0,1]
            triangle_iso = np.array([[0, 0.5, 1, 0], [0, 0.8, 0, 0]])
            ax.plot(triangle_iso[0], triangle_iso[1], 'r-', linewidth=2)
            ax.fill(triangle_iso[0][:-1], triangle_iso[1][:-1], alpha=0.3, color='red')
            ax.set_title('Равнобедренный\n(две стороны равны)')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Разносторонний треугольник
            ax = axes[0,2]
            triangle_scal = np.array([[0, 0.7, 1, 0], [0, 0.6, 0, 0]])
            ax.plot(triangle_scal[0], triangle_scal[1], 'g-', linewidth=2)
            ax.fill(triangle_scal[0][:-1], triangle_scal[1][:-1], alpha=0.3, color='green')
            ax.set_title('Разносторонний\n(все стороны разные)')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Прямоугольный треугольник
            ax = axes[1,0]
            triangle_right = np.array([[0, 0, 0.8, 0], [0, 0.6, 0, 0]])
            ax.plot(triangle_right[0], triangle_right[1], 'm-', linewidth=2)
            ax.fill(triangle_right[0][:-1], triangle_right[1][:-1], alpha=0.3, color='magenta')
            # Отметка прямого угла
            ax.plot([0, 0.1, 0.1, 0], [0, 0, 0.1, 0.1], 'k-', linewidth=1)
            ax.set_title('Прямоугольный\n(один угол 90°)')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Остроугольный треугольник
            ax = axes[1,1]
            triangle_acute = np.array([[0, 0.5, 0.9, 0], [0, 0.7, 0.1, 0]])
            ax.plot(triangle_acute[0], triangle_acute[1], 'orange', linewidth=2)
            ax.fill(triangle_acute[0][:-1], triangle_acute[1][:-1], alpha=0.3, color='orange')
            ax.set_title('Остроугольный\n(все углы < 90°)')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Тупоугольный треугольник
            ax = axes[1,2]
            triangle_obtuse = np.array([[0, 0.3, 1, 0], [0, 0.2, 0, 0]])
            ax.plot(triangle_obtuse[0], triangle_obtuse[1], 'cyan', linewidth=2)
            ax.fill(triangle_obtuse[0][:-1], triangle_obtuse[1][:-1], alpha=0.3, color='cyan')
            ax.set_title('Тупоугольный\n(один угол > 90°)')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Настройка всех осей
            for ax in axes.flat:
                ax.set_xlim(-0.1, 1.1)
                ax.set_ylim(-0.1, 1)
                ax.set_xticks([])
                ax.set_yticks([])
            
            plt.tight_layout()
            
            # Сохраняем изображение
            filename = os.path.join(self.temp_dir, 'triangles_diagram.png')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            self._log(f"Диаграмма треугольников сохранена: {filename}", "SUCCESS")
            return filename
            
        except Exception as e:
            self._log(f"Ошибка генерации диаграммы треугольников: {e}", "ERROR")
            return None
    
    def generate_quadrilaterals_diagram(self) -> Optional[str]:
        """Генерирует диаграмму четырёхугольников"""
        try:
            self._log("Генерация диаграммы четырёхугольников")
            
            fig, axes = plt.subplots(2, 3, figsize=(15, 10))
            fig.suptitle('Четырёхугольники', fontsize=16, fontweight='bold')
            
            # Квадрат
            ax = axes[0,0]
            square = np.array([[0.2, 0.8, 0.8, 0.2, 0.2], [0.2, 0.2, 0.8, 0.8, 0.2]])
            ax.plot(square[0], square[1], 'b-', linewidth=2)
            ax.fill(square[0], square[1], alpha=0.3, color='blue')
            ax.set_title('Квадрат\n(все стороны равны,\nвсе углы 90°)')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Прямоугольник
            ax = axes[0,1]
            rectangle = np.array([[0.1, 0.9, 0.9, 0.1, 0.1], [0.3, 0.3, 0.7, 0.7, 0.3]])
            ax.plot(rectangle[0], rectangle[1], 'r-', linewidth=2)
            ax.fill(rectangle[0], rectangle[1], alpha=0.3, color='red')
            ax.set_title('Прямоугольник\n(противоположные стороны равны,\nвсе углы 90°)')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Ромб
            ax = axes[0,2]
            rhombus = np.array([[0.5, 0.8, 0.5, 0.2, 0.5], [0.2, 0.5, 0.8, 0.5, 0.2]])
            ax.plot(rhombus[0], rhombus[1], 'g-', linewidth=2)
            ax.fill(rhombus[0], rhombus[1], alpha=0.3, color='green')
            ax.set_title('Ромб\n(все стороны равны,\nпротивоположные углы равны)')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Параллелограмм
            ax = axes[1,0]
            parallelogram = np.array([[0.1, 0.7, 0.9, 0.3, 0.1], [0.2, 0.2, 0.7, 0.7, 0.2]])
            ax.plot(parallelogram[0], parallelogram[1], 'm-', linewidth=2)
            ax.fill(parallelogram[0], parallelogram[1], alpha=0.3, color='magenta')
            ax.set_title('Параллелограмм\n(противоположные стороны\nпараллельны и равны)')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Трапеция
            ax = axes[1,1]
            trapezoid = np.array([[0.2, 0.8, 0.7, 0.3, 0.2], [0.2, 0.2, 0.8, 0.8, 0.2]])
            ax.plot(trapezoid[0], trapezoid[1], 'orange', linewidth=2)
            ax.fill(trapezoid[0], trapezoid[1], alpha=0.3, color='orange')
            ax.set_title('Трапеция\n(одна пара\nпараллельных сторон)')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Произвольный четырёхугольник
            ax = axes[1,2]
            quad = np.array([[0.1, 0.8, 0.7, 0.2, 0.1], [0.3, 0.1, 0.8, 0.6, 0.3]])
            ax.plot(quad[0], quad[1], 'cyan', linewidth=2)
            ax.fill(quad[0], quad[1], alpha=0.3, color='cyan')
            ax.set_title('Произвольный\nчетырёхугольник')
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # Настройка всех осей
            for ax in axes.flat:
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.set_xticks([])
                ax.set_yticks([])
            
            plt.tight_layout()
            
            # Сохраняем изображение
            filename = os.path.join(self.temp_dir, 'quadrilaterals_diagram.png')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            self._log(f"Диаграмма четырёхугольников сохранена: {filename}", "SUCCESS")
            return filename
            
        except Exception as e:
            self._log(f"Ошибка генерации диаграммы четырёхугольников: {e}", "ERROR")
            return None
    
    def generate_circle_diagram(self) -> Optional[str]:
        """Генерирует диаграмму окружности с основными элементами"""
        try:
            self._log("Генерация диаграммы окружности")
            
            fig, ax = plt.subplots(1, 1, figsize=(12, 12))
            
            # Основная окружность
            theta = np.linspace(0, 2*np.pi, 100)
            radius = 3
            center_x, center_y = 0, 0
            x_circle = center_x + radius * np.cos(theta)
            y_circle = center_y + radius * np.sin(theta)
            
            ax.plot(x_circle, y_circle, 'b-', linewidth=3, label='Окружность')
            
            # Центр
            ax.plot(center_x, center_y, 'ro', markersize=8, label='Центр (O)')
            ax.text(center_x-0.3, center_y-0.3, 'O', fontsize=12, fontweight='bold')
            
            # Радиусы
            angles_rad = [0, np.pi/4, np.pi]
            for i, angle in enumerate(angles_rad):
                x_end = center_x + radius * np.cos(angle)
                y_end = center_y + radius * np.sin(angle)
                ax.plot([center_x, x_end], [center_y, y_end], 'r-', linewidth=2)
                if i == 0:
                    ax.text(x_end/2, y_end/2 + 0.2, 'R (радиус)', fontsize=10, ha='center')
            
            # Диаметр
            ax.plot([-radius, radius], [0, 0], 'g-', linewidth=3, label='Диаметр')
            ax.text(0, -0.5, 'D = 2R (диаметр)', fontsize=10, ha='center', color='green')
            
            # Хорда
            chord_angle1, chord_angle2 = np.pi/6, 5*np.pi/6
            x1 = center_x + radius * np.cos(chord_angle1)
            y1 = center_y + radius * np.sin(chord_angle1)
            x2 = center_x + radius * np.cos(chord_angle2)
            y2 = center_y + radius * np.sin(chord_angle2)
            ax.plot([x1, x2], [y1, y2], 'm-', linewidth=2, label='Хорда')
            ax.text((x1+x2)/2, (y1+y2)/2 + 0.3, 'Хорда', fontsize=10, ha='center', color='magenta')
            
            # Касательная
            tang_angle = np.pi/3
            x_tang = center_x + radius * np.cos(tang_angle)
            y_tang = center_y + radius * np.sin(tang_angle)
            
            # Точка касания
            ax.plot(x_tang, y_tang, 'ko', markersize=6)
            ax.text(x_tang + 0.3, y_tang + 0.3, 'T', fontsize=10, fontweight='bold')
            
            # Касательная линия (перпендикулярно радиусу)
            tang_len = 2
            dx = -radius * np.sin(tang_angle)
            dy = radius * np.cos(tang_angle)
            norm = np.sqrt(dx**2 + dy**2)
            dx, dy = dx/norm * tang_len, dy/norm * tang_len
            
            ax.plot([x_tang - dx, x_tang + dx], [y_tang - dy, y_tang + dy], 'orange', linewidth=2, label='Касательная')
            ax.text(x_tang + dx*0.7, y_tang + dy*0.7, 'Касательная', fontsize=10, color='orange')
            
            # Секущая
            sec_angle1, sec_angle2 = -np.pi/4, 3*np.pi/4
            x3 = center_x + radius * np.cos(sec_angle1)
            y3 = center_y + radius * np.sin(sec_angle1)
            x4 = center_x + radius * np.cos(sec_angle2)
            y4 = center_y + radius * np.sin(sec_angle2)
            
            # Продлеваем секущую за пределы окружности
            extend = 1.5
            dx_sec = x4 - x3
            dy_sec = y4 - y3
            norm_sec = np.sqrt(dx_sec**2 + dy_sec**2)
            dx_sec, dy_sec = dx_sec/norm_sec * extend, dy_sec/norm_sec * extend
            
            ax.plot([x3 - dx_sec, x4 + dx_sec], [y3 - dy_sec, y4 + dy_sec], 'cyan', linewidth=2, label='Секущая')
            ax.text((x3+x4)/2 - 1, (y3+y4)/2 - 0.5, 'Секущая', fontsize=10, color='cyan')
            
            ax.set_title('Элементы окружности', fontsize=16, fontweight='bold')
            ax.set_xlabel('x')
            ax.set_ylabel('y')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.set_xlim(-5, 5)
            ax.set_ylim(-5, 5)
            
            plt.tight_layout()
            
            # Сохраняем изображение
            filename = os.path.join(self.temp_dir, 'circle_diagram.png')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            self._log(f"Диаграмма окружности сохранена: {filename}", "SUCCESS")
            return filename
            
        except Exception as e:
            self._log(f"Ошибка генерации диаграммы окружности: {e}", "ERROR")
            return None
    
    def generate_areas_volumes_diagram(self) -> Optional[str]:
        """Генерирует диаграмму с формулами площадей и объёмов"""
        try:
            self._log("Генерация диаграммы площадей и объёмов")
            
            fig = plt.figure(figsize=(16, 12))
            fig.suptitle('Площади и объёмы основных фигур', fontsize=18, fontweight='bold')
            
            # 2D фигуры (площади)
            # Квадрат
            ax1 = plt.subplot(3, 4, 1)
            square = np.array([[0.2, 0.8, 0.8, 0.2, 0.2], [0.2, 0.2, 0.8, 0.8, 0.2]])
            ax1.plot(square[0], square[1], 'b-', linewidth=2)
            ax1.fill(square[0], square[1], alpha=0.3, color='blue')
            ax1.text(0.5, 0.1, 'S = a²', fontsize=12, ha='center', fontweight='bold')
            ax1.set_title('Квадрат')
            ax1.set_aspect('equal')
            ax1.set_xticks([])
            ax1.set_yticks([])
            
            # Прямоугольник
            ax2 = plt.subplot(3, 4, 2)
            rect = np.array([[0.1, 0.9, 0.9, 0.1, 0.1], [0.3, 0.3, 0.7, 0.7, 0.3]])
            ax2.plot(rect[0], rect[1], 'r-', linewidth=2)
            ax2.fill(rect[0], rect[1], alpha=0.3, color='red')
            ax2.text(0.5, 0.1, 'S = a × b', fontsize=12, ha='center', fontweight='bold')
            ax2.set_title('Прямоугольник')
            ax2.set_aspect('equal')
            ax2.set_xticks([])
            ax2.set_yticks([])
            
            # Треугольник
            ax3 = plt.subplot(3, 4, 3)
            triangle = np.array([[0.2, 0.5, 0.8, 0.2], [0.2, 0.8, 0.2, 0.2]])
            ax3.plot(triangle[0], triangle[1], 'g-', linewidth=2)
            ax3.fill(triangle[0][:-1], triangle[1][:-1], alpha=0.3, color='green')
            ax3.text(0.5, 0.1, 'S = ½ × a × h', fontsize=12, ha='center', fontweight='bold')
            ax3.set_title('Треугольник')
            ax3.set_aspect('equal')
            ax3.set_xticks([])
            ax3.set_yticks([])
            
            # Окружность
            ax4 = plt.subplot(3, 4, 4)
            theta = np.linspace(0, 2*np.pi, 100)
            x_circ = 0.5 + 0.3 * np.cos(theta)
            y_circ = 0.5 + 0.3 * np.sin(theta)
            ax4.plot(x_circ, y_circ, 'purple', linewidth=2)
            ax4.fill(x_circ, y_circ, alpha=0.3, color='purple')
            ax4.text(0.5, 0.1, 'S = π × r²', fontsize=12, ha='center', fontweight='bold')
            ax4.set_title('Круг')
            ax4.set_aspect('equal')
            ax4.set_xticks([])
            ax4.set_yticks([])
            
            # 3D фигуры (объёмы)
            # Куб (изометрическая проекция)
            ax5 = plt.subplot(3, 4, 5)
            # Передняя грань
            ax5.plot([0.2, 0.6, 0.6, 0.2, 0.2], [0.2, 0.2, 0.6, 0.6, 0.2], 'b-', linewidth=2)
            # Задняя грань (смещённая)
            ax5.plot([0.4, 0.8, 0.8, 0.4, 0.4], [0.4, 0.4, 0.8, 0.8, 0.4], 'b-', linewidth=2)
            # Соединяющие рёбра
            ax5.plot([0.2, 0.4], [0.2, 0.4], 'b-', linewidth=2)
            ax5.plot([0.6, 0.8], [0.2, 0.4], 'b-', linewidth=2)
            ax5.plot([0.6, 0.8], [0.6, 0.8], 'b-', linewidth=2)
            ax5.plot([0.2, 0.4], [0.6, 0.8], 'b-', linewidth=2)
            ax5.text(0.5, 0.1, 'V = a³', fontsize=12, ha='center', fontweight='bold')
            ax5.set_title('Куб')
            ax5.set_aspect('equal')
            ax5.set_xticks([])
            ax5.set_yticks([])
            
            # Параллелепипед
            ax6 = plt.subplot(3, 4, 6)
            # Передняя грань
            ax6.plot([0.1, 0.7, 0.7, 0.1, 0.1], [0.2, 0.2, 0.5, 0.5, 0.2], 'r-', linewidth=2)
            # Задняя грань
            ax6.plot([0.3, 0.9, 0.9, 0.3, 0.3], [0.4, 0.4, 0.7, 0.7, 0.4], 'r-', linewidth=2)
            # Соединяющие рёбра
            ax6.plot([0.1, 0.3], [0.2, 0.4], 'r-', linewidth=2)
            ax6.plot([0.7, 0.9], [0.2, 0.4], 'r-', linewidth=2)
            ax6.plot([0.7, 0.9], [0.5, 0.7], 'r-', linewidth=2)
            ax6.plot([0.1, 0.3], [0.5, 0.7], 'r-', linewidth=2)
            ax6.text(0.5, 0.1, 'V = a × b × c', fontsize=12, ha='center', fontweight='bold')
            ax6.set_title('Параллелепипед')
            ax6.set_aspect('equal')
            ax6.set_xticks([])
            ax6.set_yticks([])
            
            # Цилиндр
            ax7 = plt.subplot(3, 4, 7)
            # Основания
            theta = np.linspace(0, 2*np.pi, 50)
            x_base1 = 0.5 + 0.2 * np.cos(theta)
            y_base1 = 0.3 + 0.1 * np.sin(theta)  # Эллипс для перспективы
            x_base2 = 0.5 + 0.2 * np.cos(theta)
            y_base2 = 0.7 + 0.1 * np.sin(theta)
            ax7.plot(x_base1, y_base1, 'g-', linewidth=2)
            ax7.plot(x_base2, y_base2, 'g-', linewidth=2)
            # Боковые линии
            ax7.plot([0.3, 0.3], [0.3, 0.7], 'g-', linewidth=2)
            ax7.plot([0.7, 0.7], [0.3, 0.7], 'g-', linewidth=2)
            ax7.text(0.5, 0.1, 'V = π × r² × h', fontsize=12, ha='center', fontweight='bold')
            ax7.set_title('Цилиндр')
            ax7.set_aspect('equal')
            ax7.set_xticks([])
            ax7.set_yticks([])
            
            # Конус
            ax8 = plt.subplot(3, 4, 8)
            # Основание
            x_base = 0.5 + 0.25 * np.cos(theta)
            y_base = 0.2 + 0.1 * np.sin(theta)
            ax8.plot(x_base, y_base, 'orange', linewidth=2)
            # Стороны конуса
            ax8.plot([0.25, 0.5], [0.2, 0.8], 'orange', linewidth=2)
            ax8.plot([0.75, 0.5], [0.2, 0.8], 'orange', linewidth=2)
            ax8.text(0.5, 0.05, 'V = ⅓ × π × r² × h', fontsize=12, ha='center', fontweight='bold')
            ax8.set_title('Конус')
            ax8.set_aspect('equal')
            ax8.set_xticks([])
            ax8.set_yticks([])
            
            # Сфера
            ax9 = plt.subplot(3, 4, 9)
            # Внешний контур
            x_sphere = 0.5 + 0.3 * np.cos(theta)
            y_sphere = 0.5 + 0.3 * np.sin(theta)
            ax9.plot(x_sphere, y_sphere, 'purple', linewidth=2)
            # Внутренние окружности для объёма
            for r in [0.1, 0.2]:
                x_inner = 0.5 + r * np.cos(theta)
                y_inner = 0.5 + r * np.sin(theta)
                ax9.plot(x_inner, y_inner, 'purple', linewidth=1, alpha=0.5)
            ax9.text(0.5, 0.1, 'V = ⁴⁄₃ × π × r³', fontsize=12, ha='center', fontweight='bold')
            ax9.set_title('Сфера')
            ax9.set_aspect('equal')
            ax9.set_xticks([])
            ax9.set_yticks([])
            
            # Пирамида
            ax10 = plt.subplot(3, 4, 10)
            # Основание (квадрат)
            ax10.plot([0.2, 0.8, 0.8, 0.2, 0.2], [0.2, 0.2, 0.8, 0.8, 0.2], 'cyan', linewidth=2)
            # Рёбра к вершине
            ax10.plot([0.2, 0.5], [0.2, 0.9], 'cyan', linewidth=2)
            ax10.plot([0.8, 0.5], [0.2, 0.9], 'cyan', linewidth=2)
            ax10.plot([0.8, 0.5], [0.8, 0.9], 'cyan', linewidth=2)
            ax10.plot([0.2, 0.5], [0.8, 0.9], 'cyan', linewidth=2)
            ax10.text(0.5, 0.05, 'V = ⅓ × S_осн × h', fontsize=12, ha='center', fontweight='bold')
            ax10.set_title('Пирамида')
            ax10.set_aspect('equal')
            ax10.set_xticks([])
            ax10.set_yticks([])
            
            # Настройка всех осей
            for i in range(1, 11):
                ax = plt.subplot(3, 4, i)
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
            
            plt.tight_layout()
            
            # Сохраняем изображение
            filename = os.path.join(self.temp_dir, 'areas_volumes_diagram.png')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            self._log(f"Диаграмма площадей и объёмов сохранена: {filename}", "SUCCESS")
            return filename
            
        except Exception as e:
            self._log(f"Ошибка генерации диаграммы площадей и объёмов: {e}", "ERROR")
            return None
    
    def generate_coordinate_geometry_diagram(self) -> Optional[str]:
        """Генерирует диаграмму координатной геометрии"""
        try:
            self._log("Генерация диаграммы координатной геометрии")
            
            fig, axes = plt.subplots(2, 2, figsize=(14, 12))
            fig.suptitle('Координатная геометрия', fontsize=16, fontweight='bold')
            
            # График 1: Основы координатной плоскости
            ax = axes[0,0]
            ax.axhline(y=0, color='k', linewidth=1)
            ax.axvline(x=0, color='k', linewidth=1)
            ax.grid(True, alpha=0.3)
            
            # Точки
            points = [(2, 3), (-1, 2), (-2, -1), (3, -2)]
            labels = ['A(2, 3)', 'B(-1, 2)', 'C(-2, -1)', 'D(3, -2)']
            colors = ['red', 'blue', 'green', 'purple']
            
            for (x, y), label, color in zip(points, labels, colors):
                ax.plot(x, y, 'o', color=color, markersize=8)
                ax.annotate(label, (x, y), xytext=(5, 5), textcoords='offset points')
            
            ax.set_xlim(-4, 4)
            ax.set_ylim(-4, 4)
            ax.set_xlabel('x')
            ax.set_ylabel('y')
            ax.set_title('Координатная плоскость')
            
            # График 2: Расстояние между точками
            ax = axes[0,1]
            ax.axhline(y=0, color='k', linewidth=1)
            ax.axvline(x=0, color='k', linewidth=1)
            ax.grid(True, alpha=0.3)
            
            # Две точки
            x1, y1 = 1, 1
            x2, y2 = 4, 3
            ax.plot([x1, x2], [y1, y2], 'r-', linewidth=2, label='Расстояние')
            ax.plot(x1, y1, 'bo', markersize=8)
            ax.plot(x2, y2, 'bo', markersize=8)
            ax.annotate(f'A({x1}, {y1})', (x1, y1), xytext=(-10, 10), textcoords='offset points')
            ax.annotate(f'B({x2}, {y2})', (x2, y2), xytext=(5, 5), textcoords='offset points')
            
            # Формула
            ax.text(2.5, 0.5, f'd = √[(x₂-x₁)² + (y₂-y₁)²]', fontsize=12, 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
            
            ax.set_xlim(-1, 5)
            ax.set_ylim(-1, 4)
            ax.set_xlabel('x')
            ax.set_ylabel('y')
            ax.set_title('Расстояние между точками')
            
            # График 3: Уравнение прямой
            ax = axes[1,0]
            ax.axhline(y=0, color='k', linewidth=1)
            ax.axvline(x=0, color='k', linewidth=1)
            ax.grid(True, alpha=0.3)
            
            # Различные прямые
            x = np.linspace(-3, 3, 100)
            
            # y = 2x + 1
            y1 = 2*x + 1
            ax.plot(x, y1, 'r-', linewidth=2, label='y = 2x + 1')
            
            # y = -x + 2
            y2 = -x + 2
            ax.plot(x, y2, 'b-', linewidth=2, label='y = -x + 2')
            
            # y = 0.5x - 1
            y3 = 0.5*x - 1
            ax.plot(x, y3, 'g-', linewidth=2, label='y = 0.5x - 1')
            
            ax.set_xlim(-3, 3)
            ax.set_ylim(-3, 4)
            ax.set_xlabel('x')
            ax.set_ylabel('y')
            ax.set_title('Уравнения прямых')
            ax.legend()
            
            # График 4: Парабола и окружность
            ax = axes[1,1]
            ax.axhline(y=0, color='k', linewidth=1)
            ax.axvline(x=0, color='k', linewidth=1)
            ax.grid(True, alpha=0.3)
            
            # Парабола y = x²/2
            x_par = np.linspace(-3, 3, 100)
            y_par = x_par**2 / 2
            ax.plot(x_par, y_par, 'r-', linewidth=2, label='y = x²/2')
            
            # Окружность x² + y² = 4
            theta = np.linspace(0, 2*np.pi, 100)
            x_circle = 2 * np.cos(theta)
            y_circle = 2 * np.sin(theta)
            ax.plot(x_circle, y_circle, 'b-', linewidth=2, label='x² + y² = 4')
            
            ax.set_xlim(-3, 3)
            ax.set_ylim(-1, 5)
            ax.set_xlabel('x')
            ax.set_ylabel('y')
            ax.set_title('Парабола и окружность')
            ax.legend()
            
            plt.tight_layout()
            
            # Сохраняем изображение
            filename = os.path.join(self.temp_dir, 'coordinate_geometry_diagram.png')
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            self._log(f"Диаграмма координатной геометрии сохранена: {filename}", "SUCCESS")
            return filename
            
        except Exception as e:
            self._log(f"Ошибка генерации диаграммы координатной геометрии: {e}", "ERROR")
            return None
    
    def cleanup(self):
        """Очистка временных файлов"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self._log(f"Временные файлы очищены: {self.temp_dir}", "SUCCESS")
        except Exception as e:
            self._log(f"Ошибка очистки временных файлов: {e}", "ERROR")

# Глобальный экземпляр генератора
math_image_generator = None

def get_math_image_generator():
    """Получить экземпляр генератора изображений"""
    global math_image_generator
    if math_image_generator is None:
        math_image_generator = MathImageGenerator()
    return math_image_generator
