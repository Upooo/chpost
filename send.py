from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.enums import ParseMode

API_ID = 29564102
API_HASH = '3d4e44824650a1ce0e4ad339f23a4330'
BOT_TOKEN = '7645991590:AAEOHiFJIP6AM8jQJ7kayxQjgUskWrc-330'

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_states = {}
user_data = {}

# --- Commands ---
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    await message.reply(
        "👋 Hai! Aku bot untuk posting pesan ke channel kamu.\n"
        "Ketik /send untuk mulai mengirim postingan ke channel."
    )

@app.on_message(filters.command("send"))
async def send_command(client, message: Message):
    user_id = message.from_user.id
    user_states[user_id] = "wait_channel"
    user_data[user_id] = {"buttons": []}
    await message.reply(
        "💭 Mau post di channel mana? Kirim username atau ID channel-nya.\n\n📝 Contoh: @usernamechannel"
    )

@app.on_message(filters.text & ~filters.private)
async def ignore_group(client, message: Message):
    return

# --- Text & Photo Handlers ---
@app.on_message(filters.text & filters.private)
async def handle_text(client, message: Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if not state:
        return

    text = message.text.strip()

    if state == "wait_channel":
        try:
            await client.get_chat(text)
            user_data[user_id]["chat_id"] = text
            user_states[user_id] = "choose_post_type"
            await message.reply(
                "❓ Pilih jenis postingan yang mau kamu buat:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🖼 Foto", callback_data="post_type_photo"),
                        InlineKeyboardButton("📝 Text", callback_data="post_type_text"),
                        InlineKeyboardButton("❌ Batal", callback_data="post_type_cancel")
                    ]
                ])
            )
        except Exception:
            await message.reply("❗ ID atau username channel-nya gak valid, coba lagi ya...")

    elif state == "wait_message":
        user_data[user_id]["message_text"] = text
        user_states[user_id] = "ask_buttons"
        await ask_add_buttons(message)

    elif state == "wait_caption" or state == "wait_caption_after_photo":
        user_data[user_id]["message_text"] = text
        user_states[user_id] = "ask_buttons"
        await ask_add_buttons(message)

    elif state == "wait_button_input":
        try:
            btn_text, btn_url = map(str.strip, text.split(",", 1))
            user_data[user_id]["current_button"] = InlineKeyboardButton(btn_text, url=btn_url)
            user_states[user_id] = "wait_button_position"
            await message.reply(
                "❓ Mau posisi tombolnya gimana?",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("⬇️ Vertikal", callback_data="pos_vertical"),
                        InlineKeyboardButton("➡️ Horizontal", callback_data="pos_horizontal")
                    ],
                    [InlineKeyboardButton("✅ Selesai", callback_data="done")]
                ])
            )
        except Exception:
            await message.reply("⚠️ Format salah! Gunakan format: Teks, URL")

@app.on_message(filters.photo & filters.private)
async def handle_photo(client, message: Message):
    user_id = message.from_user.id
    if user_states.get(user_id) == "wait_photo":
        user_data[user_id]["photo_file_id"] = message.photo.file_id
        user_states[user_id] = "wait_caption_after_photo"
        await message.reply(
            "✍️ Kirim caption untuk foto (atau tekan tombol Skip jika tidak ingin pakai caption).",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Skip", callback_data="skip_caption")]
            ])
        )

# --- Callback Handler ---
@app.on_callback_query()
async def handle_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    state = user_states.get(user_id)

    if data == "post_type_photo":
        user_states[user_id] = "wait_photo"
        await callback.message.edit("📸 Kirim fotonya sekarang ya!")

    elif data == "post_type_text":
        user_states[user_id] = "wait_message"
        await callback.message.edit("✍️ Kirim teks caption postingannya!")

    elif data == "post_type_cancel":
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        await callback.message.edit("❌ Proses dibatalkan.")

    elif data == "skip_caption" and state == "wait_caption_after_photo":
        user_data[user_id]["message_text"] = ""
        user_states[user_id] = "ask_buttons"
        await ask_add_buttons(callback.message)

    elif data == "add_button_yes":
        user_states[user_id] = "wait_button_input"
        await callback.message.edit("❗ Masukkan tombol pertama (format: Teks, URL):")

    elif data == "add_button_no":
        await send_final_message(client, user_id, callback)

    elif data == "add_more":
        user_states[user_id] = "wait_button_input"
        await callback.message.edit("❗ Masukkan tombol (format: Teks, URL):")

    elif data == "pos_vertical":
        user_data[user_id]["buttons"].append([user_data[user_id]["current_button"]])
        user_states[user_id] = "ask_more_buttons"
        await ask_more_buttons(callback.message)

    elif data == "pos_horizontal":
        if user_data[user_id]["buttons"] and len(user_data[user_id]["buttons"][-1]) < 3:
            user_data[user_id]["buttons"][-1].append(user_data[user_id]["current_button"])
        else:
            user_data[user_id]["buttons"].append([user_data[user_id]["current_button"]])
        user_states[user_id] = "ask_more_buttons"
        await ask_more_buttons(callback.message)

    elif data == "done":
        await send_final_message(client, user_id, callback)

# --- Utility Functions ---
async def ask_add_buttons(msg):
    await msg.reply(
        "❓ Mau tambah tombol di postingan?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Mau", callback_data="add_button_yes"),
                InlineKeyboardButton("❌ Nggak", callback_data="add_button_no")
            ]
        ])
    )

async def ask_more_buttons(msg):
    await msg.edit(
        "❓ Mau tambah tombol lagi?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Tambah", callback_data="add_more")],
            [InlineKeyboardButton("✅ Selesai", callback_data="done")]
        ])
    )

async def send_final_message(client, user_id, callback):
    data = user_data.get(user_id)
    if not data:
        await callback.message.edit("⚠️ Data gak lengkap, gagal kirim.")
        return

    try:
        if "photo_file_id" in data:
            await client.send_photo(
                chat_id=data["chat_id"],
                photo=data["photo_file_id"],
                caption=data.get("message_text", ""),
                reply_markup=InlineKeyboardMarkup(data["buttons"]) if data["buttons"] else None,
                parse_mode=ParseMode.HTML
            )
        else:
            await client.send_message(
                chat_id=data["chat_id"],
                text=data.get("message_text", ""),
                reply_markup=InlineKeyboardMarkup(data["buttons"]) if data["buttons"] else None,
                parse_mode=ParseMode.HTML
            )
        await callback.message.edit("✅ Berhasil posting ke channel! Cek ya.")
    except Exception as e:
        await callback.message.edit(f"⁉️ Gagal mengirim: {e}")

    user_states.pop(user_id, None)
    user_data.pop(user_id, None)

# --- Run the bot ---
app.run()