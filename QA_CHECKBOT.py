import json
from typing import Dict, List, Optional
from telegram import Update, constants, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
from enum import Enum

# Загружаем переменные из .env
load_dotenv()

# Получаем токен
TOKEN = os.getenv("BOT_TOKEN")

# Константы для текстовых сообщений
class MessageText:
    START = (
        "👋 Привет! Я бот для создания чек-листов тестирования.\n\n"
        "📌 Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/template - напоминалка чек-лист\n"
        "/types - виды тестирования\n"
        "/help - я запутался\n\n"
        "🔍 Доступные темы для чек-листов:\n"
        "{available_topics}\n\n"
        "📝 Просто введите название темы (например, 'авторизация', 'регистрация' или 'навигация'), "
        "и я пришлю вам подробный чек-лист для тестирования.\n\n"
        "Или используйте кнопки ниже для быстрого доступа к командам."
    )
    
    HELP = (
        "ℹ️ Помощь по использованию бота:\n\n"
        "1. Чтобы получить чек-лист, просто введите название темы, например:\n"
        "   - 'авторизация'\n"
        "   - 'регистрация'\n"
        "   - 'навигация'\n\n"
        "2. Доступные команды:\n"
        "   - /start - перезапустить бота\n"
        "   - /template - напоминалка чек-лист\n"
        "   - /types - виды тестирования\n"
        "   - /help - я запутался\n\n"
        "3. Используйте кнопки внизу экрана для быстрого доступа к командам."
    )
    
    TEMPLATE_HEADER = "📋 Стандартный чек-лист для тестирования:\n\n"
    TEMPLATE_FOOTER = "\n\nВы можете использовать этот шаблон как основу для своего тестирования."
    
    TESTING_TYPES_HEADER = "🧪 Виды тестирования программного обеспечения:\n\n"
    
    UNKNOWN_COMMAND = "Команда не распознана. Введите /help для списка доступных команд."
    TOPIC_NOT_FOUND = "Тема не найдена. Доступные темы: {available_topics}\n\nПопробуйте одну из этих команд или тем, или отправьте /start для справки."
    ERROR_MESSAGE = "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."

class ButtonText(Enum):
    CHECKLIST_REMINDER = "Напоминалка чек-лист"
    TESTING_TYPES = "Виды тестирования"
    HELP = "Я запутался"

class BotCommands(Enum):
    START = ("start", "Перезапустить бота")
    TEMPLATE = ("template", "Напоминалка чек-лист")
    TYPES = ("types", "Виды тестирования")
    HELP = ("help", "Я запутался")

class KnowledgeBaseLoader:
    """Отвечает за загрузку базы знаний (Single Responsibility Principle)"""
    @staticmethod
    def load(file_path: str = 'checklists.json') -> Dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Файл checklists.json не найден!")
            return {}
        except json.JSONDecodeError:
            print("Ошибка при чтении JSON-файла!")
            return {}

class ChecklistGenerator:
    """Отвечает за генерацию чек-листов (Single Responsibility Principle)"""
    @staticmethod
    def generate(topic: str, knowledge_base: Dict) -> str:
        topic_data = knowledge_base[topic]
        checklist = [f"📌 Чек-лист для темы: {topic.capitalize()}"]
        
        for category in topic_data["categories"]:
            checklist.append(f"\n🔹 {category}:")
            checklist.extend([f"• {item}" for item in topic_data["items"][category]])
            
        return "\n".join(checklist)

class MessageSender:
    """Отвечает за отправку сообщений (Single Responsibility Principle)"""
    @staticmethod
    async def send_long_message(update: Update, text: str, reply_markup=None):
        lines = text.split('\n')
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line) + 1
            
            if current_length + line_length > constants.MessageLimit.MAX_TEXT_LENGTH:
                await update.message.reply_text('\n'.join(current_chunk), reply_markup=reply_markup)
                current_chunk = [line]
                current_length = line_length
                reply_markup = None
            else:
                current_chunk.append(line)
                current_length += line_length
        
        if current_chunk:
            await update.message.reply_text('\n'.join(current_chunk), reply_markup=reply_markup)

class AdvancedChecklistBot:
    def __init__(self):
        self.knowledge_base = KnowledgeBaseLoader.load()
        self._initialize_data()
        
    def _initialize_data(self):
        """Инициализация данных бота"""
        self.default_template = DEFAULT_TEMPLATE
        self.available_topics_list = AVAILABLE_TOPICS
        self.testing_types = TESTING_TYPES
        
    async def setup_commands(self, application: Application):
        """Настройка команд меню бота"""
        commands = [BotCommand(command.value[0], command.value[1]) for command in BotCommands]
        await application.bot.set_my_commands(commands)
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        keyboard = [
            [KeyboardButton(ButtonText.CHECKLIST_REMINDER.value), 
             KeyboardButton(ButtonText.TESTING_TYPES.value)],
            [KeyboardButton(ButtonText.HELP.value)]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        available_topics = "\n".join([f"• {topic.capitalize()}" for topic in self.available_topics_list])
        welcome_text = MessageText.START.format(available_topics=available_topics)
        
        await MessageSender.send_long_message(update, welcome_text, reply_markup)
        
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        await update.message.reply_text(MessageText.HELP)
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        text = update.message.text.lower()
        
        # Обработка нажатий на кнопки
        if text == ButtonText.CHECKLIST_REMINDER.value.lower():
            await self.send_template(update, context)
        elif text == ButtonText.TESTING_TYPES.value.lower():
            await self.send_testing_types(update, context)
        elif text == ButtonText.HELP.value.lower():
            await self.help(update, context)
        elif text in self.knowledge_base:
            checklist = ChecklistGenerator.generate(text, self.knowledge_base)
            await MessageSender.send_long_message(update, checklist)
        elif text.startswith('/'):
            await update.message.reply_text(MessageText.UNKNOWN_COMMAND)
        else:
            available_topics = ", ".join([f"'{topic}'" for topic in self.available_topics_list])
            await update.message.reply_text(
                MessageText.TOPIC_NOT_FOUND.format(available_topics=available_topics)
            )
            
    async def send_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка стандартного шаблона"""
        template = MessageText.TEMPLATE_HEADER + "\n".join([f"• {item}" for item in self.default_template]) + MessageText.TEMPLATE_FOOTER
        await MessageSender.send_long_message(update, template)
        
    async def send_testing_types(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка видов тестирования"""
        types_text = MessageText.TESTING_TYPES_HEADER + "\n".join(self.testing_types)
        await MessageSender.send_long_message(update, types_text)
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        print(f"Произошла ошибка: {context.error}")
        if update and hasattr(update, 'message'):
            await update.message.reply_text(MessageText.ERROR_MESSAGE)

# Константы данных
DEFAULT_TEMPLATE = [
    "UI/Внешний вид – Проверка визуальной корректности и соответствия макетам",
    "Функциональность – Тестирование работы функций согласно требованиям",
    "Валидация данных – Проверка корректности ввода/вывода данных",
    "Обработка ошибок – Реакция системы на нештатные ситуации",
    "Производительность – Скорость работы, отклик системы",
    "Безопасность – Защита от уязвимостей, авторизация, шифрование",
    "Кросс-платформенность – Работа на разных устройствах, ОС, браузерах",
    "Логирование – Корректность записи логов для анализа",
    "Локализация – Поддержка языков, региональных настроек",
    "Документация – Соответствие документации реальному поведению",
    "Юзабилити – Удобство и интуитивность интерфейса",
    "Совместимость – Работа с разными версиями ПО, железа, браузеров",
    "Доступность (a11y) – Поддержка людей с ограниченными возможностями",
    "API-тестирование – Проверка endpoints, запросов и ответов",
    "Интеграционное тестирование – Взаимодействие с внешними сервисами",
    "Нагрузочное тестирование – Поведение системы под высокой нагрузкой",
    "Масштабируемость – Возможность роста без потери производительности",
    "Отказоустойчивость – Работа при сбоях (сеть, серверы)",
    "Восстановление – Откат после сбоев, backup-ы",
    "Конфигурируемость – Работа с разными настройками и окружениями",
    "Миграции данных – Перенос данных между версиями",
    "Установка/Обновление – Корректность инсталляции и апдейтов",
    "Мультитенантность – Изоляция данных для разных клиентов (SaaS)",
    "Юнит-тестирование – Проверка отдельных модулей кода",
    "Регрессионное тестирование – Проверка старых функций после изменений",
    "A/B-тестирование – Сравнение разных версий фич",
    "Тестирование аналитики – Корректность сбора метрик",
    "Тестирование зависимостей – Работа с обновленными библиотеками",
    "Тестирование лицензий – Проверка платных функций, подписок",
    "Тестирование в разных сетях – Работа при медленном/нестабильном соединении"
]

AVAILABLE_TOPICS = [
    "авторизация",
    "регистрация",
    "навигация",
    "форма обратной связи",
    "поиск",
    "безопасность",
    "api"
]

TESTING_TYPES = [
    "1. По типу проверки",
    "• Позитивное тестирование – проверка работы системы на корректных (валидных) данных.",
    "• Негативное тестирование – проверка обработки ошибок и невалидных данных.",
    "",
    "2. По частоте и глубине выполнения",
    "• Регрессионное тестирование – повторный прогон тестов после изменений для выявления регрессий.",
    "• Санитарное (Sanity) – быстрая проверка ключевой функциональности после изменений.",
    "• Дымовое (Smoke) – минимальный набор тестов для подтверждения базовой работоспособности.",
    "",
    "3. Функциональное тестирование",
    "• Проверка соответствия системы функциональным требованиям (что делает система).",
    "",
    "4. Нефункциональное тестирование",
    "• Безопасность – поиск уязвимостей и защита от взлома.",
    "• Нагрузочное – оценка производительности под высокой нагрузкой.",
    "• Стрессовое – тестирование за пределами нормальных условий (нагрузка, ресурсы).",
    "• Тестирование верстки (UI/UX) – проверка соответствия дизайну и удобства интерфейса.",
    "• Тестирование требований – анализ полноты и тестируемости ТЗ.",
    "",
    "5. По уровню доступа к коду",
    "• Белый ящик (White Box) – тестирование с доступом к коду и алгоритмам.",
    "• Черный ящик (Black Box) – тестирование без знания внутренней структуры (только вход/выход).",
    "• Серый ящик (Gray Box) – частичное знание внутренней логики (например, тестирование API).",
    "",
    "6. По уровням тестирования",
    "• Модульное (Unit) – тестирование отдельных функций или классов.",
    "• Интеграционное – проверка взаимодействия между модулями или сервисами.",
    "• Системное – тестирование системы в целом на соответствие требованиям.",
    "• Приемочное (UAT) – финальная проверка заказчиком перед сдачей проекта.",
    "",
    "7. Дополнительные виды",
    "• Сквозное (E2E) – тестирование полного пользовательского сценария от начала до конца.",
    "• Контрактное – проверка соглашений между сервисами (например, API-контракты).",
    "• Компонентное – тестирование изолированных компонентов (микросервисов, библиотек).",
    "",
    "8. По продукту тестирования",
    "• Web – тестирование веб-приложений (браузеры, интерфейсы).",
    "• API – проверка backend-логики через запросы (REST, GraphQL, SOAP).",
    "• Mobile – тестирование мобильных приложений (iOS, Android).",
    "",
    "9. По автоматизации",
    "• Ручное тестирование – выполнение тестов вручную (исследовательское, UI-тесты).",
    "• Автоматизиное – прогон тестов с помощью скриптов (unit, API, e2e).",
    "",
    "10. По подготовке тестов",
    "• Исследовательское (Ad-hoc) – спонтанное тестирование без предварительных сценариев.",
    "• Интуитивное (Error guessing) – поиск ошибок на основе опыта тестировщика.",
    "• По документации – тестирование на основе требований (спецификаций, ТЗ)."
]

def main():
    """Запуск бота"""
    bot = AdvancedChecklistBot()
    app = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler(BotCommands.START.value[0], bot.start))
    app.add_handler(CommandHandler(BotCommands.TEMPLATE.value[0], bot.send_template))
    app.add_handler(CommandHandler(BotCommands.TYPES.value[0], bot.send_testing_types))
    app.add_handler(CommandHandler(BotCommands.HELP.value[0], bot.help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # Настройка команд меню
    app.post_init = bot.setup_commands
    
    # Регистрация обработчика ошибок
    app.add_error_handler(bot.error_handler)
    
    # Запуск бота
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()