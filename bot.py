import logging
import os
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database as db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Faqat shu Telegram ID(lar) botdan foydalana oladi.
# O'zingizning ID'ingizni @userinfobot orqali bilib oling va shu yerga yozing.
ALLOWED_USER_IDS = set()  # bo'sh bo'lsa -- hammaga ochiq (ehtiyot bo'ling)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Conversation state'lar
(
    ADD_EMP_NAME,
    ADD_EMP_SALARY,
    PAY_SELECT_EMP,
    PAY_AMOUNT,
    PAY_CURRENCY,
    EXP_SELECT_CAT,
    EXP_AMOUNT,
    EXP_CURRENCY,
    EXP_NOTE,
    EXC_GIVEN_AMOUNT,
    EXC_GIVEN_CUR,
    EXC_RECEIVED_AMOUNT,
    NEW_CAT_NAME,
) = range(13)

USD = "USD"
UZS = "UZS"


def access_check(update: Update) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return update.effective_user.id in ALLOWED_USER_IDS


def fmt(amount, currency):
    if currency == USD:
        return f"${amount:,.2f}"
    return f"{amount:,.0f} so'm"


# ---------------- MAIN MENU ----------------

def main_menu_kb():
    kb = [
        [InlineKeyboardButton("👤 Oyliklar", callback_data="menu_salary")],
        [InlineKeyboardButton("💱 Kurs ayirboshlash", callback_data="menu_exchange")],
        [InlineKeyboardButton("💸 Rasxodlar", callback_data="menu_expense")],
        [InlineKeyboardButton("📊 Statistika", callback_data="menu_stats")],
    ]
    return InlineKeyboardMarkup(kb)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not access_check(update):
        await update.message.reply_text("Sizga ruxsat berilmagan.")
        return
    await update.message.reply_text(
        "Salom! Oylik va xarajat hisob-kitob botiga xush kelibsiz.\n\nKerakli bo'limni tanlang:",
        reply_markup=main_menu_kb(),
    )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Kerakli bo'limni tanlang:", reply_markup=main_menu_kb())
    return ConversationHandler.END


# ---------------- SALARY MENU ----------------

def salary_menu_kb():
    kb = [
        [InlineKeyboardButton("➕ Xodim qo'shish", callback_data="emp_add")],
        [InlineKeyboardButton("💵 To'lov kiritish", callback_data="emp_pay")],
        [InlineKeyboardButton("📋 Xodimlar holati", callback_data="emp_status")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(kb)


async def salary_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("👤 Oyliklar bo'limi:", reply_markup=salary_menu_kb())


# ---- Add employee flow ----

async def emp_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Xodimning ismini kiriting:")
    return ADD_EMP_NAME


async def emp_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_emp_name"] = update.message.text.strip()
    await update.message.reply_text("Oylik summasini kiriting (USD, masalan: 600):")
    return ADD_EMP_SALARY


async def emp_add_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "")
    try:
        salary = float(text)
    except ValueError:
        await update.message.reply_text("Iltimos, faqat raqam kiriting. Masalan: 600")
        return ADD_EMP_SALARY

    name = context.user_data.pop("new_emp_name")
    db.add_employee(name, salary)
    await update.message.reply_text(
        f"✅ {name} qo'shildi. Oylik: {fmt(salary, USD)}",
        reply_markup=salary_menu_kb(),
    )
    return ConversationHandler.END


# ---- Pay salary flow ----

async def emp_pay_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    employees = db.get_employees()
    if not employees:
        await q.edit_message_text(
            "Hozircha xodim qo'shilmagan. Avval xodim qo'shing.",
            reply_markup=salary_menu_kb(),
        )
        return ConversationHandler.END

    kb = [
        [InlineKeyboardButton(e["name"], callback_data=f"payemp_{e['id']}")]
        for e in employees
    ]
    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_salary")])
    await q.edit_message_text(
        "Kimga to'lov qilindi?", reply_markup=InlineKeyboardMarkup(kb)
    )
    return PAY_SELECT_EMP


async def emp_pay_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    emp_id = int(q.data.split("_")[1])
    context.user_data["pay_emp_id"] = emp_id
    emp = db.get_employee(emp_id)

    paid = db.get_paid_total_usd(emp_id, db.current_month_key())
    remaining = emp["salary_usd"] - paid

    await q.edit_message_text(
        f"{emp['name']} — oylik: {fmt(emp['salary_usd'], USD)}\n"
        f"Shu oy to'langan: {fmt(paid, USD)}\n"
        f"Qolgan: {fmt(remaining, USD)}\n\n"
        f"To'lov summasini kiriting:"
    )
    return PAY_AMOUNT


async def emp_pay_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "")
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("Iltimos, faqat raqam kiriting.")
        return PAY_AMOUNT

    context.user_data["pay_amount"] = amount
    kb = [
        [
            InlineKeyboardButton("💵 USD", callback_data="paycur_USD"),
            InlineKeyboardButton("🇺🇿 So'm", callback_data="paycur_UZS"),
        ]
    ]
    await update.message.reply_text(
        "Qaysi valyutada to'landi?", reply_markup=InlineKeyboardMarkup(kb)
    )
    return PAY_CURRENCY


async def emp_pay_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    currency = q.data.split("_")[1]
    amount = context.user_data.pop("pay_amount")
    emp_id = context.user_data.pop("pay_emp_id")
    emp = db.get_employee(emp_id)

    if currency == UZS:
        # So'mda kiritilgan to'lovni botda saqlash uchun USD ekvivalenti so'raymiz emas,
        # oddiy holatda foydalanuvchidan kursni so'raymiz orqali aniqlashtiramiz.
        context.user_data["pay_amount_raw"] = amount
        context.user_data["pay_emp_id_raw"] = emp_id
        await q.edit_message_text(
            f"{fmt(amount, UZS)} qancha USD ga teng? (joriy kursda hisoblang, masalan: 1$=12700 so'm bo'lsa, "
            f"summani USD da kiriting)"
        )
        return PAY_AMOUNT  # qayta ishlatamiz, lekin alohida flagda

    amount_usd = amount
    db.add_salary_payment(emp_id, amount, currency, amount_usd)
    paid = db.get_paid_total_usd(emp_id, db.current_month_key())
    remaining = emp["salary_usd"] - paid

    await q.edit_message_text(
        f"✅ {emp['name']}ga {fmt(amount, currency)} to'landi.\n\n"
        f"Shu oy jami to'langan: {fmt(paid, USD)}\n"
        f"Qolgan qarz: {fmt(remaining, USD)}",
        reply_markup=salary_menu_kb(),
    )
    return ConversationHandler.END


async def emp_pay_amount_usd_for_uzs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """So'mda to'lov kiritilganda, USD ekvivalentini olish uchun ishlatiladi."""
    text = update.message.text.strip().replace(",", "")
    try:
        amount_usd = float(text)
    except ValueError:
        await update.message.reply_text("Iltimos, faqat raqam kiriting (USD ekvivalenti).")
        return PAY_AMOUNT

    amount_uzs = context.user_data.pop("pay_amount_raw")
    emp_id = context.user_data.pop("pay_emp_id_raw")
    emp = db.get_employee(emp_id)

    db.add_salary_payment(emp_id, amount_uzs, UZS, amount_usd)
    paid = db.get_paid_total_usd(emp_id, db.current_month_key())
    remaining = emp["salary_usd"] - paid

    await update.message.reply_text(
        f"✅ {emp['name']}ga {fmt(amount_uzs, UZS)} ({fmt(amount_usd, USD)} ekvivalent) to'landi.\n\n"
        f"Shu oy jami to'langan: {fmt(paid, USD)}\n"
        f"Qolgan qarz: {fmt(remaining, USD)}",
        reply_markup=salary_menu_kb(),
    )
    return ConversationHandler.END


async def pay_amount_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """PAY_AMOUNT state ikki xil maqsadda ishlatiladi - qaysi bosqichda ekanini aniqlaymiz."""
    if "pay_amount_raw" in context.user_data:
        return await emp_pay_amount_usd_for_uzs(update, context)
    return await emp_pay_amount(update, context)


# ---- Employee status ----

async def emp_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    employees = db.get_employees()
    if not employees:
        await q.edit_message_text(
            "Hozircha xodim qo'shilmagan.", reply_markup=salary_menu_kb()
        )
        return

    month_key = db.current_month_key()
    lines = [f"📋 Xodimlar holati ({month_key}):\n"]
    total_salary = 0
    total_paid = 0
    for e in employees:
        paid = db.get_paid_total_usd(e["id"], month_key)
        remaining = e["salary_usd"] - paid
        total_salary += e["salary_usd"]
        total_paid += paid
        status_icon = "✅" if remaining <= 0 else "⏳"
        lines.append(
            f"{status_icon} {e['name']}: {fmt(e['salary_usd'], USD)} oylik\n"
            f"   To'langan: {fmt(paid, USD)} | Qolgan: {fmt(max(remaining,0), USD)}"
        )

    lines.append(f"\n💰 Jami oyliklar: {fmt(total_salary, USD)}")
    lines.append(f"💰 Jami to'langan: {fmt(total_paid, USD)}")
    lines.append(f"💰 Jami qolgan: {fmt(total_salary - total_paid, USD)}")

    await q.edit_message_text("\n".join(lines), reply_markup=salary_menu_kb())


# ---------------- EXPENSE MENU ----------------

def expense_menu_kb():
    kb = [
        [InlineKeyboardButton("➕ Xarajat kiritish", callback_data="exp_add")],
        [InlineKeyboardButton("🏷 Kategoriya qo'shish", callback_data="exp_addcat")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(kb)


async def expense_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("💸 Rasxodlar bo'limi:", reply_markup=expense_menu_kb())


async def exp_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    categories = db.get_categories()
    kb = [
        [InlineKeyboardButton(c["name"], callback_data=f"expcat_{c['id']}")]
        for c in categories
    ]
    kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu_expense")])
    await q.edit_message_text(
        "Qaysi kategoriya bo'yicha xarajat?", reply_markup=InlineKeyboardMarkup(kb)
    )
    return EXP_SELECT_CAT


async def exp_select_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cat_id = int(q.data.split("_")[1])
    context.user_data["exp_cat_id"] = cat_id
    cat = db.get_category(cat_id)
    await q.edit_message_text(f"Kategoriya: {cat['name']}\n\nXarajat summasini kiriting:")
    return EXP_AMOUNT


async def exp_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "")
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("Iltimos, faqat raqam kiriting.")
        return EXP_AMOUNT

    context.user_data["exp_amount"] = amount
    kb = [
        [
            InlineKeyboardButton("💵 USD", callback_data="expcur_USD"),
            InlineKeyboardButton("🇺🇿 So'm", callback_data="expcur_UZS"),
        ]
    ]
    await update.message.reply_text(
        "Qaysi valyutada?", reply_markup=InlineKeyboardMarkup(kb)
    )
    return EXP_CURRENCY


async def exp_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    currency = q.data.split("_")[1]
    context.user_data["exp_currency"] = currency
    await q.edit_message_text("Izoh kiriting (yoki '-' deb yozing izohsiz davom etish uchun):")
    return EXP_NOTE


async def exp_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text.strip()
    if note == "-":
        note = ""

    cat_id = context.user_data.pop("exp_cat_id")
    amount = context.user_data.pop("exp_amount")
    currency = context.user_data.pop("exp_currency")
    cat = db.get_category(cat_id)

    db.add_expense(cat_id, amount, currency, note)
    await update.message.reply_text(
        f"✅ Xarajat qo'shildi: {cat['name']} - {fmt(amount, currency)}"
        + (f"\nIzoh: {note}" if note else ""),
        reply_markup=expense_menu_kb(),
    )
    return ConversationHandler.END


async def exp_addcat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Yangi kategoriya nomini kiriting:")
    return NEW_CAT_NAME


async def exp_addcat_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    db.add_category(name)
    await update.message.reply_text(
        f"✅ '{name}' kategoriyasi qo'shildi.", reply_markup=expense_menu_kb()
    )
    return ConversationHandler.END


# ---------------- EXCHANGE MENU ----------------

async def exchange_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton("➕ Ayirboshlash kiritish", callback_data="exc_add")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ]
    await q.edit_message_text(
        "💱 Kurs ayirboshlash bo'limi:", reply_markup=InlineKeyboardMarkup(kb)
    )


async def exc_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [
        [
            InlineKeyboardButton("💵 USD berdim", callback_data="excgiven_USD"),
            InlineKeyboardButton("🇺🇿 So'm berdim", callback_data="excgiven_UZS"),
        ]
    ]
    await q.edit_message_text(
        "Qaysi valyutani berdingiz (sotdingiz)?", reply_markup=InlineKeyboardMarkup(kb)
    )
    return EXC_GIVEN_CUR


async def exc_given_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    currency = q.data.split("_")[1]
    context.user_data["exc_given_cur"] = currency
    await q.edit_message_text(f"Qancha {('$' if currency==USD else 'so’m')} berdingiz? Summani kiriting:")
    return EXC_GIVEN_AMOUNT


async def exc_given_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "")
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("Iltimos, faqat raqam kiriting.")
        return EXC_GIVEN_AMOUNT

    context.user_data["exc_given_amount"] = amount
    given_cur = context.user_data["exc_given_cur"]
    received_cur = UZS if given_cur == USD else USD
    await update.message.reply_text(
        f"Qancha {('so’m' if received_cur==UZS else '$')} oldingiz? Summani kiriting:"
    )
    context.user_data["exc_received_cur"] = received_cur
    return EXC_RECEIVED_AMOUNT


async def exc_received_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "")
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("Iltimos, faqat raqam kiriting.")
        return EXC_RECEIVED_AMOUNT

    given_amount = context.user_data.pop("exc_given_amount")
    given_cur = context.user_data.pop("exc_given_cur")
    received_cur = context.user_data.pop("exc_received_cur")

    db.add_exchange(given_amount, given_cur, amount, received_cur)
    rate = amount / given_amount if given_amount else 0

    await update.message.reply_text(
        f"✅ Ayirboshlash qo'shildi:\n"
        f"Berdingiz: {fmt(given_amount, given_cur)}\n"
        f"Oldingiz: {fmt(amount, received_cur)}\n"
        f"Kurs: 1 {given_cur} = {rate:,.2f} {received_cur}",
    )
    await update.message.reply_text("💱 Kurs ayirboshlash bo'limi:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Yana qo'shish", callback_data="exc_add")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")],
    ]))
    return ConversationHandler.END


# ---------------- STATISTICS ----------------

async def stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    month_key = db.current_month_key()
    month_name = datetime.now().strftime("%Y-%m")

    lines = [f"📊 Statistika ({month_name})\n"]

    # Oyliklar
    employees = db.get_employees()
    total_salary = sum(e["salary_usd"] for e in employees)
    total_paid = sum(db.get_paid_total_usd(e["id"], month_key) for e in employees)
    lines.append("👤 OYLIKLAR:")
    lines.append(f"  Jami belgilangan: {fmt(total_salary, USD)}")
    lines.append(f"  Jami to'langan: {fmt(total_paid, USD)}")
    lines.append(f"  Jami qolgan: {fmt(total_salary - total_paid, USD)}")

    # Rasxodlar
    lines.append("\n💸 RASXODLAR:")
    totals = db.get_expense_totals_by_category(month_key)
    if totals:
        grouped = {}
        for t in totals:
            grouped.setdefault(t["category_name"], []).append((t["currency"], t["total"]))
        exp_total_usd = 0
        exp_total_uzs = 0
        for cat_name, items in grouped.items():
            parts = []
            for cur, total in items:
                parts.append(fmt(total, cur))
                if cur == USD:
                    exp_total_usd += total
                else:
                    exp_total_uzs += total
            lines.append(f"  {cat_name}: {', '.join(parts)}")
        lines.append(f"  ─────────")
        lines.append(f"  Jami: {fmt(exp_total_usd, USD)} + {fmt(exp_total_uzs, UZS)}")
    else:
        lines.append("  Hozircha xarajat yo'q")

    # Kurs ayirboshlash
    lines.append("\n💱 KURS AYIRBOSHLASH:")
    exchanges = db.get_exchanges_month(month_key)
    if exchanges:
        for ex in exchanges:
            lines.append(
                f"  {fmt(ex['given_amount'], ex['given_currency'])} → "
                f"{fmt(ex['received_amount'], ex['received_currency'])} "
                f"(kurs: {ex['rate']:,.2f})"
            )
    else:
        lines.append("  Hozircha ayirboshlash yo'q")

    kb = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="back_main")]]
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


# ---------------- CANCEL ----------------

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Bekor qilindi.", reply_markup=main_menu_kb()
    )
    return ConversationHandler.END


# ---------------- APP SETUP ----------------

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable o'rnatilmagan. "
            "export BOT_TOKEN='sizning_tokeningiz' qiling."
        )

    db.init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))

    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_main$"))
    application.add_handler(CallbackQueryHandler(salary_menu, pattern="^menu_salary$"))
    application.add_handler(CallbackQueryHandler(expense_menu, pattern="^menu_expense$"))
    application.add_handler(CallbackQueryHandler(exchange_menu, pattern="^menu_exchange$"))
    application.add_handler(CallbackQueryHandler(stats_menu, pattern="^menu_stats$"))
    application.add_handler(CallbackQueryHandler(emp_status, pattern="^emp_status$"))

    # Add employee conversation
    add_emp_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(emp_add_start, pattern="^emp_add$")],
        states={
            ADD_EMP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, emp_add_name)],
            ADD_EMP_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, emp_add_salary)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(add_emp_conv)

    # Pay salary conversation
    pay_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(emp_pay_start, pattern="^emp_pay$")],
        states={
            PAY_SELECT_EMP: [CallbackQueryHandler(emp_pay_select, pattern="^payemp_")],
            PAY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_amount_router)],
            PAY_CURRENCY: [CallbackQueryHandler(emp_pay_currency, pattern="^paycur_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(pay_conv)

    # Expense conversation
    exp_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(exp_add_start, pattern="^exp_add$")],
        states={
            EXP_SELECT_CAT: [CallbackQueryHandler(exp_select_cat, pattern="^expcat_")],
            EXP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_amount)],
            EXP_CURRENCY: [CallbackQueryHandler(exp_currency, pattern="^expcur_")],
            EXP_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_note)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(exp_conv)

    # Add category conversation
    addcat_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(exp_addcat_start, pattern="^exp_addcat$")],
        states={
            NEW_CAT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_addcat_save)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(addcat_conv)

    # Exchange conversation
    exc_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(exc_add_start, pattern="^exc_add$")],
        states={
            EXC_GIVEN_CUR: [CallbackQueryHandler(exc_given_currency, pattern="^excgiven_")],
            EXC_GIVEN_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exc_given_amount)],
            EXC_RECEIVED_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exc_received_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(exc_conv)

    logger.info("Bot ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    main()
