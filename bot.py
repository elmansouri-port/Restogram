from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
import requests
import json
from datetime import datetime

class RestaurantMenuBot:

    def __init__(self, token):
        self.token = token
        self.base_url = "https://cofee.pythonanywhere.com"
        self.updater = Updater(token=self.token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # Register handlers
        self.dispatcher.add_handler(CommandHandler("start", self.start))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))
        self.dispatcher.add_handler(CallbackQueryHandler(self.button_click))
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.fetch_restaurant_info))

    def start(self, update: Update, context):
        welcome_message = (
            "══════════════════\n"
            " 🍽️ *WELCOME* 🍽️ \n"
            "══════════════════\n\n"
            "👋 *Welcome to the Restaurant Menu Bot!*\n\n"
            "🔍 Send me the name of a restaurant to:\n"
            "• View details and menu\n"
            "• Check opening hours\n"
            "• See current promotions\n\n"
            "💡 Use /help for more information"
        )
        update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

    def help_command(self, update: Update, context):
        help_message = (
            "═══════════════\n"
            " 💡 *HELP* 💡 \n"
            "═══════════════\n\n"
            "🔸 *How to use this bot:*\n\n"
            "1️⃣ Send restaurant name\n"
            "2️⃣ View restaurant details\n"
            "3️⃣ Browse menu categories\n"
            "4️⃣ Check prices and descriptions\n\n"
            "📍 *Available Commands:*\n"
            "• /start - Launch the bot\n"
            "• /help - Show this help message\n\n"
            "📱 *Features:*\n"
            "• Real-time opening hours\n"
            "• Current promotions\n"
            "• Direct contact options\n"
            "• Easy navigation"
        )
        update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)

    def create_restaurant_info_keyboard(self, restaurant_name, info):
        keyboard = [
            [
                InlineKeyboardButton("📋 Menu Categories", callback_data=f"menu:{restaurant_name}"),
                InlineKeyboardButton("📍 Location", url=info.get('map_url', 'https://maps.google.com'))
            ],
            [
                InlineKeyboardButton("📱 WhatsApp", url=f"https://wa.me/{info.get('whatsapp', '')}"),
                InlineKeyboardButton("🌐 Website", url=info.get('website', 'https://example.com'))
            ],
            [
                InlineKeyboardButton("📘 Facebook", url=info.get('fb', 'https://facebook.com')),
                InlineKeyboardButton("📸 Instagram", url=info.get('insta', 'https://instagram.com'))
            ],
            [InlineKeyboardButton("❌ Close", callback_data=f"delete:{restaurant_name}")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def format_opening_hours(self, temp_douv):
        current_day = datetime.now().strftime("%A")
        current_time = datetime.now().strftime("%H:%M")
        
        time_emoji = "🌅" if "06:00" <= current_time < "12:00" else \
                    "☀️" if "12:00" <= current_time < "17:00" else \
                    "🌆" if "17:00" <= current_time < "20:00" else "🌙"
        
        hours_text = f"{time_emoji} *Opening Hours*\n"
        for day, hours in temp_douv.items():
            if day.lower() == current_day.lower():
                hours_text += f"▶️ *{day}:* __{hours}__ (Today)\n"
            else:
                hours_text += f"⏺️ {day}: {hours}\n"
        return hours_text

    def format_restaurant_info(self, data):
        info = data['public_info']
        
        message = "══════════════════\n"
        message += f" 🏪 *{info.get('rest_name', 'Restaurant')}* \n"
        message += "══════════════════\n\n"
        
        message += f"🆔 *ID:* `{info.get('id', 'N/A')}`\n\n"
        
        message += "📞 *Contact Details*\n"
        message += f"☎️ Phone: `{info.get('phone', 'N/A')}`\n"
        message += f"📱 WhatsApp: `{info.get('whatsapp', 'N/A')}`\n\n"
        
        message += f"{self.format_opening_hours(info.get('temp_douv', {}))}\n"
        
        if info.get('promo'):
            message += "🎉 *Current Promotions*\n"
            for promo in info['promo']:
                message += f"└ 🔸 {promo}\n"
        
        return message

    def fetch_restaurant_info(self, update: Update, context):
        try:
            if hasattr(update, 'message'):
                restaurant_name = update.message.text.strip()
                context.user_data['restaurant_msg_id'] = update.message.message_id
                chat_id = update.message.chat_id
            else:
                chat_id = update.chat.id
                restaurant_name = context.user_data.get('restaurant_name', '')

            context.bot.send_chat_action(chat_id=chat_id, action='typing')

            url = f"{self.base_url}/{restaurant_name}/info"
            response = requests.get(url)
            print(response.json())

            if response.status_code == 200:
                data = response.json()

                if data['status'] == 'success':
                    public_info = data['public_info']
                    rest_name = public_info.get('rest_name', restaurant_name)
                    context.user_data['restaurant_name'] = rest_name
                    
                    rest_img = public_info.get('rest_img', '')
                    message = self.format_restaurant_info(data)
                    keyboard = self.create_restaurant_info_keyboard(rest_name, public_info)

                    sent_message = context.bot.send_photo(
                        chat_id=chat_id,
                        photo=rest_img,
                        caption=message,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard
                    )

                    context.user_data['info_msg_id'] = sent_message.message_id
                else:
                    if hasattr(update, 'message'):
                        update.message.reply_text("❌ Failed to fetch restaurant information. Please try again.")
            else:
                if hasattr(update, 'message'):
                    update.message.reply_text("❌ Restaurant not found. Please check the name and try again.")

        except Exception as e:
            print(f"Error: {str(e)}")
            if hasattr(update, 'message'):
                update.message.reply_text("❌ An error occurred. Please try again later.")

    def show_categories(self, query, restaurant_name, context):
        url = f"{self.base_url}/{restaurant_name}/categories"
        url1 = f"{self.base_url}/{restaurant_name}/info"
        rest_img = requests.get(url1).json()['public_info']['rest_img']
        print(rest_img)
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                categories = data.get("categories", [])
                print(categories)
                
                if categories:
                    message = "═══════════════\n"
                    message += " 📋 *MENU* 📋 \n"
                    message += "═══════════════\n\n"
                    message += "*Select a category:*"
                    
                    keyboard = []
                    for i in range(0, len(categories), 2):
                        row = []
                        row.append(InlineKeyboardButton(
                            f"🔸 {categories[i]}",
                            callback_data=f"cat:{restaurant_name}:{categories[i]}"
                        ))
                        if i + 1 < len(categories):
                            row.append(InlineKeyboardButton(
                                f"🔸 {categories[i + 1]}",
                                callback_data=f"cat:{restaurant_name}:{categories[i + 1]}"
                            ))
                        keyboard.append(row)
                    
                    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=f"back_to_info:{restaurant_name}")])
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    query.message.delete()
                    
                    context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=rest_img,
                        caption=message,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    query.edit_message_caption(
                        caption="❌1 No categories found for this restaurant.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("⬅️ Back", callback_data=f"back_to_info:{restaurant_name}")
                        ]])
                    )
            else:
                query.edit_message_caption(
                    caption="❌2 Failed to fetch categories. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Back", callback_data=f"back_to_info:{restaurant_name}")
                    ]])
                )
        except Exception as e:
            print(f"Error in show_categories: {str(e)}")
            query.edit_message_caption(
                caption="❌3 An error occurred. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back", callback_data=f"back_to_info:{restaurant_name}")
                ]])
            )

    def show_products(self, query, restaurant_name, category):
        url = f"{self.base_url}/{restaurant_name}/products"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                products = data.get(category, [])
                
                if products:
                    message = "════════════════\n"
                    message += f" 🍽️ {category} \n"
                    message += "════════════════\n\n"
                    
                    for i, product in enumerate(products, 1):
                        title = product.get('title', 'Untitled')
                        price = product.get('price', 'N/A')
                        desc = product.get('desc', '')
                    
                    keyboard = [
                        *[
                            [InlineKeyboardButton(
                                f"📋 {product.get('title', 'Product Details')}    |    💰 Price: `{price}`", 
                                callback_data=f"product:{restaurant_name}:{category}:{i}"
                            )]
                            for i, product in enumerate(products)
                        ],
                        [InlineKeyboardButton("⬅️ Back to Categories", callback_data=f"menu:{restaurant_name}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    query.edit_message_caption(
                        caption=message,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    query.edit_message_caption(
                        caption="❌ No items found in this category.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("⬅️ Back to Categories", callback_data=f"menu:{restaurant_name}")
                        ]])
                    )
            else:
                query.edit_message_caption(
                    caption="❌ Failed to fetch products. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Back to Categories", callback_data=f"menu:{restaurant_name}")
                    ]])
                )
        except Exception as e:
            print(f"Error in show_products: {str(e)}")
            query.edit_message_caption(
                caption="❌ An error occurred. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back to Categories", callback_data=f"menu:{restaurant_name}")
                ]])
            )

    def button_click(self, update: Update, context):
        query = update.callback_query
        query.answer()
        
        data = query.data.split(':')
        action = data[0]
        restaurant_name = data[1]
        
        if action == "menu":
            self.show_categories(query, restaurant_name, context)
        
        elif action == "cat":
            category = data[2]
            self.show_products(query, restaurant_name, category)
        
        elif action == "product":
            category = data[2]
            product_index = int(data[3])
            url = f"{self.base_url}/{restaurant_name}/products"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    products = data.get(category, [])
                    
                    if 0 <= product_index < len(products):
                        product = products[product_index]
                        
                        message = "════════════════\n"
                        message += f" 🍽️ {product.get('title', 'Product Details')} \n"
                        message += "════════════════\n\n"
                        
                        message += f"💰 *Price:* `{product.get('price', 'N/A')}`\n\n"
                        
                        if product.get('img_url'):
                            img_url = product.get('img_url')
                            print(img_url)

                        if product.get('desc'):
                            message += f"📝 *Description:*\n{product.get('desc')}\n\n"
                            
                        if product.get('ingredients'):
                            message += f"🥗 *Ingredients:*\n{product.get('ingredients')}\n\n"
                        
                        keyboard = [
                            [InlineKeyboardButton("⬅️ Back to Products", 
                                callback_data=f"cat:{restaurant_name}:{category}")]
                        ]
                        
                        query.message.delete()

                # Send a new message with updated image and caption
                        context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=img_url,  # Send the product's image
                        caption=message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    else:
                        query.edit_message_caption(
                            caption="❌ Product not found.",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("⬅️ Back", 
                                    callback_data=f"cat:{restaurant_name}:{category}")
                            ]])
                        )
            except Exception as e:
                print(f"Error in product detail view: {str(e)}")
                query.edit_message_caption(
                    caption="❌ An error occurred. Please try again later.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Back", 
                            callback_data=f"cat:{restaurant_name}:{category}")
                    ]])
                )

        elif action == "back_to_info":
            try:
                url = f"{self.base_url}/{restaurant_name}/info"
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    if data['status'] == 'success':
                        message = self.format_restaurant_info(data)
                        keyboard = self.create_restaurant_info_keyboard(
                            restaurant_name,
                            data['public_info']
                        )
                        
                        query.edit_message_caption(
                            caption=message,
                            reply_markup=keyboard,
                            parse_mode=ParseMode.MARKDOWN
                        )
                else:
                    query.edit_message_caption(
                        caption="❌ Failed to fetch restaurant information. Please try again.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("⬅️ Back to Menu", 
                                callback_data=f"menu:{restaurant_name}")
                        ]])
                    )
            except Exception as e:
                print(f"Error in back_to_info: {str(e)}")
                query.edit_message_caption(
                    caption="❌ An error occurred. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Back to Menu", 
                            callback_data=f"menu:{restaurant_name}")
                    ]])
                )
        
        elif action == "delete":
            try:
                query.message.delete()
                if 'restaurant_msg_id' in context.user_data:
                    context.bot.delete_message(
                        chat_id=query.message.chat_id,
                        message_id=context.user_data['restaurant_msg_id']
                    )
                    context.user_data.clear()
            except Exception as e:
                print(f"Error deleting messages: {str(e)}")

    def run(self):
        print("Bot is starting...")
        self.updater.start_polling()
        self.updater.idle()

def main():
    TOKEN = "your_telegram_bot_token"
    bot = RestaurantMenuBot(TOKEN)
    bot.run()

if __name__ == '__main__':
    main()
