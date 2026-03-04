# -*- coding: utf-8 -*-
import telebot
from telebot import types
import sqlite3

# --- Configuration ---
TOKEN = "8525595800:AAG9QYaTCsOosW7qwJZNUKq_kijOLhDIOfA"
ADMIN_ID = 7128914520 
bot = telebot.TeleBot(TOKEN)

BKASH_NO = "01615682337" 
NAGAD_NO = "01615682337"
DB_PATH = '/data/vpn_pro.db' if os.path.exists('/data') else 'vpn_pro.db'
# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS vpns (id INTEGER PRIMARY KEY, name TEXT, price REAL, duration TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS stock (id INTEGER PRIMARY KEY, vpn_id INTEGER, account_info TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS used_trx (trx_id TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

init_db()

# --- Keyboard Menus ---
def main_menu_markup(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if user_id == ADMIN_ID:
        markup.add(" Admin Panel")
    else:
        markup.add(" Buy VPN", " My Account")
        markup.add(" Support")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Welcome! Buy high-quality VPN from our service.", 
                     reply_markup=main_menu_markup(message.from_user.id))

# --- 1. My Account ---
@bot.message_handler(func=lambda message: message.text == " My Account")
def my_account(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "You are currently in Admin Mode.")
    else:
        bot.send_message(message.chat.id, f" Your ID: `{message.from_user.id}`\nClick Buy VPN to purchase.", parse_mode="Markdown")

# --- 2. Support ---
@bot.message_handler(func=lambda message: message.text == " Support")
def support(message):
    bot.send_message(message.chat.id, " Contact Support: @Rakib0343")

# --- 3. Buy VPN ---
@bot.message_handler(func=lambda message: message.text == " Buy VPN")
def buy_list(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, " Admin cannot buy VPN.")
        return
        
    conn = sqlite3.connect('vpn_pro.db'); cursor = conn.cursor()
    cursor.execute("SELECT * FROM vpns"); rows = cursor.fetchall(); conn.close()
    if not rows:
        bot.send_message(message.chat.id, "Currently no VPN packages available.")
        return
    markup = types.InlineKeyboardMarkup()
    for row in rows: 
        btn_text = f"{row[1]} ({row[3]}) - {row[2]} TK"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"order_{row[0]}"))
    bot.send_message(message.chat.id, "Select a VPN package:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_"))
def process_order(call):
    vpn_id = int(call.data.split("_")[1])
    conn = sqlite3.connect('vpn_pro.db'); cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM vpns WHERE id=?", (vpn_id,))
    vpn = cursor.fetchone()
    cursor.execute("SELECT id FROM stock WHERE vpn_id=? LIMIT 1", (vpn_id,))
    if not cursor.fetchone():
        bot.answer_callback_query(call.id, "Sorry, Out of Stock!", show_alert=True)
        conn.close(); return
    conn.close()

    payment_text = (f" **Payment Details**\n\n VPN: **{vpn[0]}**\n Price: **{vpn[1]} TK**\n\n"
                    f"Send Money to:\n bKash (Personal): `{BKASH_NO}`\n Nagad (Personal): `{NAGAD_NO}`\n\n"
                    f"After sending money, enter your **TrxID** here:")
    msg = bot.send_message(call.message.chat.id, payment_text, parse_mode="Markdown")
    bot.register_next_step_handler(msg, verify_payment_logic, vpn_id, vpn[1])

# --- 4. Admin Decisions ---
def verify_payment_logic(message, vpn_id, price):
    trx_id = message.text.strip().upper()
    u_id = message.from_user.id
    u_name = message.from_user.first_name

    conn = sqlite3.connect('vpn_pro.db'); cursor = conn.cursor()
    cursor.execute("SELECT trx_id FROM used_trx WHERE trx_id=?", (trx_id,))
    if cursor.fetchone():
        bot.send_message(u_id, " This TrxID has already been used!")
        conn.close(); return
    conn.close()

    bot.send_message(u_id, " Your TrxID has been sent to Admin. Please wait for approval.")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(" Approve", callback_data=f"approve_{u_id}_{vpn_id}_{trx_id}"),
        types.InlineKeyboardButton(" Reject", callback_data=f"reject_{u_id}")
    )
    # Admin notification with Price and Details
    bot.send_message(ADMIN_ID, f" **New Order Request!**\n\n User: {u_name}\n User ID: `{u_id}`\n Amount: **{price} TK**\n TrxID: `{trx_id}`", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_admin_decision(call):
    data = call.data.split("_")
    action, user_id = data[0], int(data[1])
    if action == "approve":
        v_id, t_id = int(data[2]), data[3]
        deliver_vpn_auto(user_id, v_id, t_id)
        bot.edit_message_text(f" Approved! (Trx: {t_id})", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(user_id, " Sorry! Your payment was rejected.")
        bot.edit_message_text(" Order Rejected.", call.message.chat.id, call.message.message_id)

def deliver_vpn_auto(u_id, vpn_id, trx_id):
    conn = sqlite3.connect('vpn_pro.db'); cursor = conn.cursor()
    cursor.execute("SELECT id, account_info FROM stock WHERE vpn_id=? LIMIT 1", (vpn_id,))
    item = cursor.fetchone()
    if item:
        acc_info = item[1]
        # Splitting info assuming it's stored as "email:password"
        if ":" in acc_info:
            email, password = acc_info.split(":", 1)
            formatted_info = f" **Gmail:** `{email}`\n **Password:** `{password}`"
        else:
            formatted_info = f" **Info:** `{acc_info}`"

        bot.send_message(u_id, f" **Payment Approved!**\n\n **Your VPN Info:**\n{formatted_info}", parse_mode="Markdown")
        cursor.execute("DELETE FROM stock WHERE id=?", (item[0],))
        cursor.execute("INSERT INTO used_trx VALUES (?)", (trx_id,))
        conn.commit()
    else:
        bot.send_message(u_id, " Stock finished! Contact Admin.")
    conn.close()

# --- 5. Admin Panel Functions ---
@bot.message_handler(func=lambda message: message.text == " Admin Panel" and message.from_user.id == ADMIN_ID)
def admin_panel_handler(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(" Add VPN", callback_data="add_vpn"), 
               types.InlineKeyboardButton(" Delete VPN", callback_data="del_vpn_list"))
    markup.add(types.InlineKeyboardButton(" Stock Manager", callback_data="manage_vpn"))
    bot.send_message(message.chat.id, " **Admin Control Panel**", reply_markup=markup)

# Admin logic handles (Add/Delete/Stock) remain same but ensure they match current script flow
@bot.callback_query_handler(func=lambda call: call.data == "add_vpn")
def add_vpn_init(call):
    msg = bot.send_message(call.message.chat.id, "Enter VPN Name:")
    bot.register_next_step_handler(msg, get_vpn_name)

def get_vpn_name(message):
    name = message.text
    msg = bot.send_message(message.chat.id, "Enter Price:")
    bot.register_next_step_handler(msg, get_vpn_price, name)

def get_vpn_price(message, name):
    try:
        price = float(message.text)
        msg = bot.send_message(message.chat.id, "Enter Duration (Ex: 30 Days):")
        bot.register_next_step_handler(msg, finalize_vpn_add, name, price)
    except: bot.send_message(message.chat.id, " Invalid price format.")

def finalize_vpn_add(message, name, price):
    duration = message.text
    conn = sqlite3.connect('vpn_pro.db'); cursor = conn.cursor()
    cursor.execute("INSERT INTO vpns (name, price, duration) VALUES (?, ?, ?)", (name, price, duration))
    conn.commit(); conn.close()
    bot.send_message(message.chat.id, " VPN Added!")

@bot.callback_query_handler(func=lambda call: call.data == "del_vpn_list")
def del_vpn_list(call):
    conn = sqlite3.connect('vpn_pro.db'); cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM vpns"); rows = cursor.fetchall(); conn.close()
    if not rows:
        bot.answer_callback_query(call.id, "No VPN to delete!")
        return
    markup = types.InlineKeyboardMarkup()
    for row in rows: markup.add(types.InlineKeyboardButton(row[1], callback_data=f"delvpn_{row[0]}"))
    bot.edit_message_text("Select VPN to delete:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delvpn_"))
def finalize_del_vpn(call):
    vid = call.data.split("_")[1]
    conn = sqlite3.connect('vpn_pro.db'); cursor = conn.cursor()
    cursor.execute("DELETE FROM vpns WHERE id=?", (vid,))
    cursor.execute("DELETE FROM stock WHERE vpn_id=?", (vid,))
    conn.commit(); conn.close()
    bot.edit_message_text(" VPN and stock deleted!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "manage_vpn")
def manage_options(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(" Add Stock", callback_data="add_stk_start"))
    bot.edit_message_text(" Stock Management:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "add_stk_start")
def add_stk_start(call):
    conn = sqlite3.connect('vpn_pro.db'); cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM vpns"); rows = cursor.fetchall(); conn.close()
    markup = types.InlineKeyboardMarkup()
    for row in rows: markup.add(types.InlineKeyboardButton(row[1], callback_data=f"stk_in_{row[0]}"))
    bot.edit_message_text("Select VPN to add stock:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("stk_in_"))
def get_stk_data(call):
    vid = call.data.split("_")[2]
    msg = bot.send_message(call.message.chat.id, "Send Account Info (Format: email:password):")
    bot.register_next_step_handler(msg, save_stk_db, vid)

def save_stk_db(message, vid):
    accounts = message.text.split('\n')
    conn = sqlite3.connect('vpn_pro.db'); cursor = conn.cursor()
    for acc in accounts:
        if acc.strip(): cursor.execute("INSERT INTO stock (vpn_id, account_info) VALUES (?, ?)", (vid, acc.strip()))
    conn.commit(); conn.close()
    bot.send_message(message.chat.id, " Stock Saved!")

if __name__ == "__main__":
    bot.polling(none_stop=True)
