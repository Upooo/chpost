from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery
)
from pyrogram.enums import ParseMode
import re
import json
import os

API_ID = 29564102
API_HASH = '3d4e44824650a1ce0e4ad339f23a4330'
BOT_TOKEN = '8285614308:AAHjPnJJvGnh4h5hCw3nUsuZw_ogHxzoq7Q'

app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_states = {}
user_data = {}

REACTION_FILE = "reactions.json"


# ==========================
# Reaction Database
# ==========================
def load_reactions():
    if not os.path.exists(REACTION_FILE):
        with open(REACTION_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

    try:
        with open(REACTION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_reactions(data):
    with open(REACTION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ==========================
# Commands
# ==========================
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    await message.reply(
        "👋 Hai! Bot posting channel.\n"
        "Ketik /send buat mulai."
    )


@app.on_message(filters.command("send"))
async def send_command(client, message: Message):
    user_id = message.from_user.id

    user_states[user_id] = "wait_channel"
    user_data[user_id] = {
        "buttons": [],
        "reactions": []
    }

    await message.reply(
        "💭 Mau post di channel mana?\n\n"
        "Contoh: @channel"
    )


@app.on_message(filters.text & ~filters.private)
async def ignore_group(client, message):
    return


# ==========================
# Text Handler
# ==========================
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
                "❓ Pilih jenis postingan:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🖼 Foto / Video",
                            callback_data="post_type_photo"
                        ),
                        InlineKeyboardButton(
                            "📝 Text",
                            callback_data="post_type_text"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ Batal",
                            callback_data="post_type_cancel"
                        )
                    ]
                ])
            )

        except Exception:
            await message.reply(
                "❗ Channel gak valid."
            )

    elif state == "wait_message":
        user_data[user_id]["message_text"] = text
        user_states[user_id] = "ask_buttons"

        await ask_add_buttons(message)

    elif state in [
        "wait_caption",
        "wait_caption_after_photo"
    ]:
        user_data[user_id]["message_text"] = text
        user_states[user_id] = "ask_buttons"

        await ask_add_buttons(message)

    elif state == "wait_reaction_emoji":
        emojis = text.split()

        if len(emojis) == 0:
            await message.reply("❗ Minimal 1 emoji.")
            return

        if len(emojis) > 3:
            await message.reply("❗ Maksimal 3 emoji.")
            return

        user_data[user_id]["reactions"] = emojis
        user_states[user_id] = "ask_buttons"

        await message.reply(
            f"✅ Reaction disimpan: {' '.join(emojis)}"
        )

        await ask_add_buttons(message)

    elif state == "wait_button_input":
        try:
            btn_text, btn_url = map(
                str.strip,
                text.split(",", 1)
            )

            user_data[user_id]["current_button"] = (
                InlineKeyboardButton(
                    btn_text,
                    url=btn_url
                )
            )

            user_states[user_id] = (
                "wait_button_position"
            )

            await message.reply(
                "❓ Mau posisi tombol?",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "⬇️ Vertikal",
                            callback_data="pos_vertical"
                        ),
                        InlineKeyboardButton(
                            "➡️ Horizontal",
                            callback_data="pos_horizontal"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "✅ Selesai",
                            callback_data="done"
                        )
                    ]
                ])
            )

        except Exception:
            await message.reply(
                "⚠️ Format salah!\n"
                "Teks, URL"
            )


# ==========================
# Media Handler
# ==========================
@app.on_message(
    (filters.photo | filters.video)
    & filters.private
)
async def handle_media(client, message: Message):
    user_id = message.from_user.id

    if user_states.get(user_id) == "wait_photo":

        if message.photo:
            user_data[user_id]["media_type"] = "photo"
            user_data[user_id]["file_id"] = (
                message.photo.file_id
            )

        elif message.video:
            user_data[user_id]["media_type"] = "video"
            user_data[user_id]["file_id"] = (
                message.video.file_id
            )

        user_states[user_id] = (
            "wait_caption_after_photo"
        )

        await message.reply(
            "✍️ Kirim caption atau skip",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "Skip",
                        callback_data="skip_caption"
                    )
                ]
            ])
        )


# ==========================
# Callback Handler
# ==========================
@app.on_callback_query()
async def handle_callback(
    client,
    callback: CallbackQuery
):
    user_id = callback.from_user.id
    data = callback.data
    state = user_states.get(user_id)

    # ======================
    # Reaction System
    # ======================
    if data.startswith("react_"):

        reactions_db = load_reactions()

        message_id = str(callback.message.id)
        user_id_str = str(user_id)

        if message_id not in reactions_db:
            reactions_db[message_id] = {}

        new_reaction = data.replace(
            "react_",
            ""
        )

        old_reaction = (
            reactions_db[message_id]
            .get(user_id_str)
        )

        is_unreact = (
            old_reaction == new_reaction
        )

        keyboard = (
            callback.message.reply_markup
            .inline_keyboard
        )

        new_keyboard = []

        for row in keyboard:
            new_row = []

            for button in row:

                if (
                    button.callback_data
                    and button.callback_data.startswith(
                        "react_"
                    )
                ):
                    emoji = (
                        button.callback_data
                        .replace("react_", "")
                    )

                    match = re.search(
                        r"(\d+)$",
                        button.text
                    )

                    count = (
                        int(match.group(1))
                        if match else 0
                    )

                    if old_reaction == emoji:
                        count -= 1

                    if (
                        not is_unreact
                        and new_reaction == emoji
                    ):
                        count += 1

                    count = max(count, 0)

                    new_row.append(
                        InlineKeyboardButton(
                            f"{emoji} {count}",
                            callback_data=
                            button.callback_data
                        )
                    )
                else:
                    new_row.append(button)

            new_keyboard.append(new_row)

        if is_unreact:
            reactions_db[message_id].pop(
                user_id_str,
                None
            )
        else:
            reactions_db[message_id][
                user_id_str
            ] = new_reaction

        save_reactions(reactions_db)

        await callback.message.edit_reply_markup(
            InlineKeyboardMarkup(
                new_keyboard
            )
        )

        if is_unreact:
            await callback.answer(
                "Reaction dihapus."
            )
        elif old_reaction:
            await callback.answer(
                f"Reaction diganti ke {new_reaction}"
            )
        else:
            await callback.answer(
                f"Reaction {new_reaction} ditambahkan"
            )

        return

    # ======================
    # Post Type
    # ======================
    if data == "post_type_photo":
        user_states[user_id] = "wait_photo"

        await callback.message.edit(
            "📸 Kirim foto / video!"
        )

    elif data == "post_type_text":
        user_states[user_id] = "wait_message"

        await callback.message.edit(
            "✍️ Kirim teks postingan!"
        )

    elif data == "post_type_cancel":
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)

        await callback.message.edit(
            "❌ Dibatalkan."
        )

    elif (
        data == "skip_caption"
        and state ==
        "wait_caption_after_photo"
    ):
        user_data[user_id][
            "message_text"
        ] = ""

        user_states[user_id] = (
            "ask_buttons"
        )

        await ask_add_buttons(
            callback.message
        )

    elif data == "enable_reaction":
        user_states[user_id] = (
            "wait_reaction_emoji"
        )

        await callback.message.edit(
            "❤️ Kirim emoji reaction\n"
            "Max 3\n\n"
            "Contoh:\n"
            "❤️ 🔥 😂"
        )

    elif data == "add_button_yes":
        user_states[user_id] = (
            "wait_button_input"
        )

        await callback.message.edit(
            "Teks, URL"
        )

    elif data == "add_button_no":
        await send_final_message(
            client,
            user_id,
            callback
        )

    elif data == "add_more":
        user_states[user_id] = (
            "wait_button_input"
        )

        await callback.message.edit(
            "Teks, URL"
        )

    elif data == "pos_vertical":
        user_data[user_id]["buttons"].append([
            user_data[user_id][
                "current_button"
            ]
        ])

        await ask_more_buttons(
            callback.message
        )

    elif data == "pos_horizontal":

        if (
            user_data[user_id]["buttons"]
            and len(
                user_data[user_id][
                    "buttons"
                ][-1]
            ) < 3
        ):
            user_data[user_id]["buttons"][-1].append(
                user_data[user_id][
                    "current_button"
                ]
            )
        else:
            user_data[user_id]["buttons"].append([
                user_data[user_id][
                    "current_button"
                ]
            ])

        await ask_more_buttons(
            callback.message
        )

    elif data == "done":
        await send_final_message(
            client,
            user_id,
            callback
        )


# ==========================
# Utilities
# ==========================
async def ask_add_buttons(msg):
    await msg.reply(
        "❓ Mau tambah tombol?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Tombol URL",
                    callback_data="add_button_yes"
                ),
                InlineKeyboardButton(
                    "❤️ Reaction",
                    callback_data="enable_reaction"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Selesai",
                    callback_data="add_button_no"
                )
            ]
        ])
    )


async def ask_more_buttons(msg):
    await msg.edit(
        "Tambah tombol lagi?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "➕ Tambah",
                    callback_data="add_more"
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ Selesai",
                    callback_data="done"
                )
            ]
        ])
    )


async def send_final_message(
    client,
    user_id,
    callback
):
    data = user_data.get(user_id)

    if not data:
        return

    try:
        buttons = data["buttons"][:]

        reactions = data.get(
            "reactions",
            []
        )

        if reactions:
            reaction_row = []

            for emoji in reactions:
                reaction_row.append(
                    InlineKeyboardButton(
                        f"{emoji} 0",
                        callback_data=
                        f"react_{emoji}"
                    )
                )

            buttons.append(reaction_row)

        reply_markup = (
            InlineKeyboardMarkup(buttons)
            if buttons else None
        )

        if "file_id" in data:

            if data["media_type"] == "photo":
                await client.send_photo(
                    chat_id=data["chat_id"],
                    photo=data["file_id"],
                    caption=data.get(
                        "message_text",
                        ""
                    ),
                    reply_markup=
                    reply_markup
                )

            else:
                await client.send_video(
                    chat_id=data["chat_id"],
                    video=data["file_id"],
                    caption=data.get(
                        "message_text",
                        ""
                    ),
                    reply_markup=
                    reply_markup
                )

        else:
            await client.send_message(
                chat_id=data["chat_id"],
                text=data.get(
                    "message_text",
                    ""
                ),
                reply_markup=
                reply_markup,
                parse_mode=
                ParseMode.HTML
            )

        await callback.message.edit(
            "✅ Berhasil posting!"
        )

    except Exception as e:
        await callback.message.edit(
            f"❌ Error:\n{e}"
        )

    user_states.pop(user_id, None)
    user_data.pop(user_id, None)


# ==========================
# Run
# ==========================
app.run()
