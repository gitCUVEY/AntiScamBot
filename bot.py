import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
)
from datetime import datetime
import json
import os

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
CHECK_USER, ADD_SCAMMER_NICK, ADD_SCAMMER_PROOF, MODERATION_CHOICE, MODERATION_EDIT_NICK, MODERATION_EDIT_STATUS = range(6)

# Файл для хранения данных
DATA_FILE = 'scam_db.json'

# Загрузка данных из файла
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        'users': {},
        'moderation_requests': [],
        'moderators': []  # Список ID модераторов
    }

# Сохранение данных в файл
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Проверка, является ли пользователь модератором
def is_moderator(user_id, data):
    return str(user_id) in data['moderators']

# Обработчик команды /start
def start(update: Update, context: CallbackContext) -> None:
    data = load_data()
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить игрока", callback_data='check_user')],
        [InlineKeyboardButton("⚠️ Добавить скамера", callback_data='add_scammer')]
    ]
    
    # Если пользователь модератор, добавляем кнопку модерации
    if is_moderator(user_id, data):
        keyboard.append([InlineKeyboardButton("🛠 Модерация", callback_data='moderation')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        'Добро пожаловать в анти-скам базу Roblox! Выберите действие:',
        reply_markup=reply_markup
    )

# Обработчик кнопки "Проверить игрока"
def check_user(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Введите ник игрока для проверки:")
    return CHECK_USER

# Обработчик введенного ника для проверки
def check_user_nick(update: Update, context: CallbackContext) -> int:
    nick = update.message.text.strip().lower()
    data = load_data()
    user_info = data['users'].get(nick, {})
    
    status = user_info.get('status', 'Неизвестно')
    date_added = user_info.get('date_added', 'Неизвестно')
    likes = user_info.get('likes', 0)
    dislikes = user_info.get('dislikes', 0)
    
    text = f"Информация об игроке:\n\n"
    text += f"Ник: {nick}\n"
    text += f"Статус: {status}\n"
    text += f"Дата добавления: {date_added}\n"
    text += f"👍 {likes} 👎 {dislikes}"
    
    keyboard = [
        [
            InlineKeyboardButton("👍", callback_data=f'like_{nick}'),
            InlineKeyboardButton("👎", callback_data=f'dislike_{nick}')
        ],
        [InlineKeyboardButton("🔙 Меню", callback_data='menu')]
    ]
    
    update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END

# Обработчик лайков/дизлайков
def rate_user(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    action, nick = query.data.split('_')
    data = load_data()
    
    if nick not in data['users']:
        data['users'][nick] = {'status': 'Неизвестно', 'likes': 0, 'dislikes': 0, 'date_added': datetime.now().strftime('%d.%m.%Y')}
    
    if action == 'like':
        data['users'][nick]['likes'] = data['users'][nick].get('likes', 0) + 1
    else:
        data['users'][nick]['dislikes'] = data['users'][nick].get('dislikes', 0) + 1
    
    save_data(data)
    
    likes = data['users'][nick]['likes']
    dislikes = data['users'][nick]['dislikes']
    
    query.answer()
    query.edit_message_text(
        text=query.message.text.split('\n\n')[0] + f"\n\n👍 {likes} 👎 {dislikes}",
        reply_markup=query.message.reply_markup
    )

# Обработчик кнопки "Добавить скамера"
def add_scammer(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Введите ник игрока, которого хотите добавить как скамера:")
    return ADD_SCAMMER_NICK

# Обработчик введенного ника для добавления скамера
def add_scammer_nick(update: Update, context: CallbackContext) -> int:
    nick = update.message.text.strip().lower()
    context.user_data['scammer_nick'] = nick
    update.message.reply_text("Теперь отправьте видео доказательства (можно как файл или ссылкой):")
    return ADD_SCAMMER_PROOF

# Обработчик доказательств скама
def add_scammer_proof(update: Update, context: CallbackContext) -> int:
    proof = ""
    if update.message.video:
        proof = f"Видео доказательство (file_id: {update.message.video.file_id})"
    elif update.message.text:
        proof = update.message.text
    else:
        update.message.reply_text("Пожалуйста, отправьте видео или текст с доказательствами.")
        return ADD_SCAMMER_PROOF
    
    nick = context.user_data['scammer_nick']
    user_id = update.effective_user.id
    date = datetime.now().strftime('%d.%m.%Y')
    
    data = load_data()
    data['moderation_requests'].append({
        'nick': nick,
        'proof': proof,
        'reported_by': user_id,
        'date': date,
        'status': 'pending'
    })
    save_data(data)
    
    update.message.reply_text(
        "Ваша заявка отправлена на модерацию. Спасибо за вклад в сообщество!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Меню", callback_data='menu')]])
    )
    return ConversationHandler.END

# Обработчик кнопки "Модерация" (для модераторов)
def moderation(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📝 Заявки", callback_data='moderation_requests')],
        [InlineKeyboardButton("✏️ Изменить статус", callback_data='moderation_edit')],
        [InlineKeyboardButton("🔙 Меню", callback_data='menu')]
    ]
    
    query.edit_message_text(
        text="Раздел модерации. Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработчик кнопки "Заявки" в разделе модерации
def moderation_requests(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    data = load_data()
    pending_requests = [r for r in data['moderation_requests'] if r['status'] == 'pending']
    
    if not pending_requests:
        query.edit_message_text(
            text="Нет заявок на модерацию.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='moderation')]])
        )
        return
    
    request = pending_requests[0]
    nick = request['nick']
    proof = request['proof']
    date = request['date']
    reporter = request['reported_by']
    
    text = f"Заявка на скамера:\n\n"
    text += f"Ник: {nick}\n"
    text += f"Дата подачи: {date}\n"
    text += f"Отправитель: {reporter}\n"
    text += f"Доказательства: {proof}\n\n"
    text += "Выберите решение:"
    
    keyboard = [
        [
            InlineKeyboardButton("Скамер", callback_data=f'mod_decision_{nick}_scammer'),
            InlineKeyboardButton("Проверенный", callback_data=f'mod_decision_{nick}_verified')
        ],
        [
            InlineKeyboardButton("Неизвестно", callback_data=f'mod_decision_{nick}_unknown'),
            InlineKeyboardButton("Отклонить", callback_data=f'mod_decision_{nick}_reject')
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data='moderation')]
    ]
    
    query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработчик решения модератора по заявке
def moderation_decision(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    _, _, nick, decision = query.data.split('_')
    query.answer()
    
    data = load_data()
    
    # Обновляем статус заявки
    for req in data['moderation_requests']:
        if req['nick'] == nick and req['status'] == 'pending':
            req['status'] = decision
            req['moderated_by'] = query.from_user.id
            req['moderated_date'] = datetime.now().strftime('%d.%m.%Y')
            break
    
    # Если не "отклонить", обновляем статус пользователя
    if decision != 'reject':
        if nick not in data['users']:
            data['users'][nick] = {
                'likes': 0,
                'dislikes': 0,
                'date_added': datetime.now().strftime('%d.%m.%Y')
            }
        data['users'][nick]['status'] = {
            'scammer': 'Скамер',
            'verified': 'Проверенный',
            'unknown': 'Неизвестно'
        }[decision]
    
    save_data(data)
    
    query.edit_message_text(
        text=f"Решение по игроку {nick} сохранено: {decision}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='moderation_requests')]])
    )

# Обработчик кнопки "Изменить статус" в разделе модерации
def moderation_edit(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Введите ник игрока, статус которого хотите изменить:")
    return MODERATION_EDIT_NICK

# Обработчик введенного ника для изменения статуса
def moderation_edit_nick(update: Update, context: CallbackContext) -> int:
    nick = update.message.text.strip().lower()
    context.user_data['edit_nick'] = nick
    data = load_data()
    
    if nick not in data['users']:
        data['users'][nick] = {
            'likes': 0,
            'dislikes': 0,
            'date_added': datetime.now().strftime('%d.%m.%Y'),
            'status': 'Неизвестно'
        }
        save_data(data)
    
    current_status = data['users'][nick]['status']
    
    keyboard = [
        [
            InlineKeyboardButton("Скамер", callback_data='mod_status_scammer'),
            InlineKeyboardButton("Проверенный", callback_data='mod_status_verified')
        ],
        [
            InlineKeyboardButton("Неизвестно", callback_data='mod_status_unknown'),
            InlineKeyboardButton("🔙 Назад", callback_data='moderation')
        ]
    ]
    
    update.message.reply_text(
        f"Текущий статус игрока {nick}: {current_status}\nВыберите новый статус:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MODERATION_EDIT_STATUS

# Обработчик выбора нового статуса
def moderation_edit_status(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    _, _, status = query.data.split('_')
    query.answer()
    
    nick = context.user_data['edit_nick']
    data = load_data()
    
    status_map = {
        'scammer': 'Скамер',
        'verified': 'Проверенный',
        'unknown': 'Неизвестно'
    }
    
    data['users'][nick]['status'] = status_map[status]
    data['users'][nick]['date_added'] = datetime.now().strftime('%d.%m.%Y')
    save_data(data)
    
    query.edit_message_text(
        text=f"Статус игрока {nick} изменен на: {status_map[status]}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='moderation')]])
    )
    return ConversationHandler.END

# Обработчик кнопки "Меню"
def menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    start(update, context)

# Обработчик отмены
def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Действие отменено.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main() -> None:
    # Загрузка токена бота
    with open('config.json') as f:
        config = json.load(f)
    token = config['token']
    
    # Создание Updater и передача токена бота
    updater = Updater(token)
    
    # Получение диспетчера для регистрации обработчиков
    dispatcher = updater.dispatcher
    
    # Обработчик команды /start
    dispatcher.add_handler(CommandHandler('start', start))
    
    # Обработчики callback-кнопок
    dispatcher.add_handler(CallbackQueryHandler(check_user, pattern='^check_user$'))
    dispatcher.add_handler(CallbackQueryHandler(add_scammer, pattern='^add_scammer$'))
    dispatcher.add_handler(CallbackQueryHandler(moderation, pattern='^moderation$'))
    dispatcher.add_handler(CallbackQueryHandler(moderation_requests, pattern='^moderation_requests$'))
    dispatcher.add_handler(CallbackQueryHandler(moderation_edit, pattern='^moderation_edit$'))
    dispatcher.add_handler(CallbackQueryHandler(menu, pattern='^menu$'))
    dispatcher.add_handler(CallbackQueryHandler(rate_user, pattern='^(like|dislike)_'))
    dispatcher.add_handler(CallbackQueryHandler(moderation_decision, pattern='^mod_decision_'))
    dispatcher.add_handler(CallbackQueryHandler(moderation_edit_status, pattern='^mod_status_'))
    
    # ConversationHandler для проверки пользователя
    check_user_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(check_user, pattern='^check_user$')],
        states={
            CHECK_USER: [MessageHandler(Filters.text & ~Filters.command, check_user_nick)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # ConversationHandler для добавления скамера
    add_scammer_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_scammer, pattern='^add_scammer$')],
        states={
            ADD_SCAMMER_NICK: [MessageHandler(Filters.text & ~Filters.command, add_scammer_nick)],
            ADD_SCAMMER_PROOF: [MessageHandler(Filters.video | Filters.text & ~Filters.command, add_scammer_proof)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # ConversationHandler для изменения статуса модератором
    moderation_edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(moderation_edit, pattern='^moderation_edit$')],
        states={
            MODERATION_EDIT_NICK: [MessageHandler(Filters.text & ~Filters.command, moderation_edit_nick)],
            MODERATION_EDIT_STATUS: [CallbackQueryHandler(moderation_edit_status, pattern='^mod_status_')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    dispatcher.add_handler(check_user_conv)
    dispatcher.add_handler(add_scammer_conv)
    dispatcher.add_handler(moderation_edit_conv)
    
    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()