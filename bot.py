
import discord
from discord.ext import commands, tasks
from logic import DatabaseManager, hide_img
from config import TOKEN, DATABASE
import os

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

manager = DatabaseManager(DATABASE)
manager.create_tables()


# Kullanıcı kaydı için bir komut
@bot.command()
async def start(ctx):
    user_id = ctx.author.id

    if user_id in manager.get_users():
        await ctx.send("Zaten kayıtlısınız!")
    else:
        manager.add_user(user_id, ctx.author.name)
        await ctx.send(
            "Merhaba! Hoş geldiniz! Başarılı bir şekilde kaydoldunuz! "
            "Her dakika yeni resimler alacaksınız ve bunları elde etme "
            "şansınız olacak! Bunu yapmak için 'Al!' butonuna "
            "tıklamanız gerekiyor! Sadece ilk üç kullanıcı resmi alacaktır!"
        )


# Kullanıcı sıralaması
@bot.command()
async def rating(ctx):
    res = manager.get_rating()

    if not res:
        await ctx.send("Henüz ödül kazanan kullanıcı yok!")
        return

    res = [
        f'| @{x[0]:<11} | {x[1]:<11}|\n{"_"*26}'
        for x in res
    ]

    res = '\n'.join(res)
    res = f'|USER_NAME    |COUNT_PRIZE|\n{"_"*26}\n' + res

    await ctx.send(f"```\n{res}\n```")


# Resim göndermek için zamanlanmış görev
@tasks.loop(minutes=1)
async def send_message():

    for user_id in manager.get_users():

        prize = manager.get_random_prize()
        if prize is None:
         print("Kullanılabilir ödül kalmadı!")
        return

        # Kullanılabilir ödül yoksa hata verme
        if prize is None:
            print("Kullanılabilir ödül kalmadı!")
            return

        prize_id, img = prize[:2]

        try:
            hide_img(img)

            user = await bot.fetch_user(user_id)

            if user:
                await send_image(
                    user,
                    f'hidden_img/{img}',
                    prize_id
                )

                manager.mark_prize_used(prize_id)

        except (discord.HTTPException, OSError) as e:
            print(f"Resim gönderilemedi: {e}")


# Kullanıcıya resim gönderme
async def send_image(user, image_path, prize_id):

    with open(image_path, 'rb') as img:
        file = discord.File(img)

        button = discord.ui.Button(
            label="Al!",
            custom_id=str(prize_id)
        )

        view = discord.ui.View(timeout=None)
        view.add_item(button)

        await user.send(file=file, view=view)


# Al! butonuna tıklanınca
@bot.event
async def on_interaction(interaction):

    if interaction.type == discord.InteractionType.component:

        custom_id = interaction.data.get('custom_id')

        if not custom_id or not custom_id.isdigit():
            return

        user_id = interaction.user.id
        prize_id = int(custom_id)

        if manager.get_winners_count(prize_id) < 3:

            res = manager.add_winner(user_id, prize_id)

            if res:
                img = manager.get_prize_img(prize_id)

                with open(f'img/{img}', 'rb') as photo:
                    file = discord.File(photo)

                    await interaction.response.send_message(
                        file=file,
                        content="Tebrikler, resmi aldınız!"
                    )
            else:
                await interaction.response.send_message(
                    content="Bu resme zaten sahipsiniz!",
                    ephemeral=True
                )

        else:
            await interaction.response.send_message(
                content="Maalesef, ilk üç kazanan belirlendi!",
                ephemeral=True
            )


# Bot hazır olduğunda
@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı!')

    if not send_message.is_running():
        send_message.start()


bot.run(TOKEN)
