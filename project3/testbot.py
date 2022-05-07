import discord
from discord.ext import commands
import random
import sqlite3
import datetime as dt
import requests


# флаг для лога сообщений
LOG_MSG_FLAG = [False, None]
# префикс всех команд
prefix = '!'
# сам бот
bot = commands.Bot(command_prefix=prefix)
# база данных бота
db = 'bot_db.db'
con = sqlite3.connect(db)
cur = con.cursor()
# запретные слова
ban_words = []
# словарь для описание команд в !help
dis_slow = {'logging': ['Нужен для записи текста в чатах',
                        'Крайне удобная и полезная функция для слежки за'
                        ' сервером синтакс !logging <старт/стоп> #<канал>'],
            'clear': ['Функция для очистки чата', 'Не вводите слишком больших значений!!'
                                                  '!clear <число>'],
            'pref': ['смена префикса', 'при перезапуске бота автоматом идет на (!)'
                                       '!change_prefix <префикс>'],
            'get_log': ['Получение логов по их id в базе данных', 'при отсутствии id выдает последний лог!'
                                                                  '!get_log <num/None>'],
            'say': ['тестовая команда разработчика', 'синтакс !say <слово> #<канал>'],
            'ban': ['бан он и в африке бан', '!ban @<человек> <причина>'],
            'kick': ['Как бан только кик', '!kick @<человек> <причина>'],
            'unban': ['Разбан (если ваше благородие соизволит)',
                      '!unban <человек> без пуша т.к. человека на сервере уже нет'],
            'add_warn': ['1 предупреждение человеку 3 варна - кик',
                         '!add_warn @<человек> при кике варны человека обнуляются'],
            'remove_warn': ['Убирает 1 варн', '!remove_warn @<человек> у кикнутого человека варнов нету'],
            'randint': ['Случайное число в диапозоне', '!randint <число от> <число до>'],
            'cats': ['случайный кот', '!cats И ВСЕ ПРОСТО СЛУЧАЙНЫЙ КОТ (кстати с API)'],
            'dogs': ['случайный пес', '!dogs случайный пес его картинка да'],
            'add_bad_word': ['Добавляет слово которое'
                             ' нельзя произносить на сервере',
                             'За произнесенное слово выдается варн !add_bad_word <word>']}


# реакция бота на ошибки
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Please pass in all requirements :rolling_eyes:.')
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You dont have all the requirements :angry:")
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Unknown command")


# очистка сообщений
@bot.command(name='clear', pass_context=True, brief=dis_slow['clear'][0], description=dis_slow['clear'][1])
@commands.has_permissions(administrator=True)
async def clear(ctx, amout=10):
    await ctx.channel.purge(limit=amout)


# временная смена префикса при перезагрузке префикс будет базовым (!)
@bot.command(name='change_prefix', brief=dis_slow['pref'][0], description=dis_slow['pref'][1])
@commands.has_permissions(administrator=True)
async def change(ctx, pref):
    global prefix
    x = prefix
    prefix = pref
    bot.command_prefix = prefix
    await ctx.send(f'prefix changed from {x} to {prefix}')


# логирование сообщений в базу данных
@bot.command(name='logging', brief=dis_slow['logging'][0], description=dis_slow['logging'][1])
@commands.has_permissions(ban_members=True)
async def logging(ctx, start, *, channel: discord.TextChannel):
    global LOG_MSG_FLAG
    if start == 'start':
        LOG_MSG_FLAG[0] = True
        LOG_MSG_FLAG[1] = channel.name
        new_log(channel.name)
        await ctx.send('Logging has been started')
    elif start == 'stop':
        end_log(LOG_MSG_FLAG[1])
        LOG_MSG_FLAG[0] = False
        LOG_MSG_FLAG[1] = None
        await ctx.send('Logging has been stopped')
    else:
        await ctx.send("(pref)logging start/stop")


# получение логов сообщений
@bot.command(name='get_log', brief=dis_slow['get_log'][0], description=dis_slow['get_log'][1])
@commands.has_permissions(ban_members=True)
async def get_log(ctx, i_d=None):
    if not i_d:
        i_d = cur.execute("""SELECT MAX(id) FROM loding_tab""").fetchone()[0]
        con.commit()
    x = cur.execute(f"""SELECT msgs FROM loding_tab WHERE id = {i_d}""").fetchone()
    con.commit()
    with open("result.txt", "w") as file:
        file.write(x[0])
    with open("result.txt", "rb") as file:
        await ctx.send("Your file is:", file=discord.File(file, "result.txt"))


# тестовая функция для проверки бота говорит в выбранный пользователем канал
@bot.command(brief=dis_slow['say'][0], description=dis_slow['say'][1])
@commands.has_permissions(administrator=True)
async def say(ctx, arg, *, channel: discord.TextChannel):
    await channel.send(arg)


# бан пользователя на сервере (без разбана зайти не может)
@bot.command(name='ban', pass_context=True, brief=dis_slow['ban'][0], description=dis_slow['ban'][1])
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'{member} был забанен по причине {reason}')


# кик или же удаление пользователя с сервера (может зайти обратно по приглашению)
@bot.command(name='kick', pass_context=True, brief=dis_slow['kick'][0], description=dis_slow['kick'][1])
@commands.has_permissions(ban_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'{member} был кикнут по причине {reason}')


# разбан после которого пользователь может зайти самостоятельно
@bot.command(name='unban', pass_context=True, brief=dis_slow['unban'][0], description=dis_slow['unban'][1])
@commands.has_permissions(administrator=True)
async def unban(ctx, *, member):
    user = None
    banned_users = await ctx.guild.bans()
    member_name, member_dis = member.split('#')
    for ban_ent in banned_users:
        user = ban_ent.user
    if (user.name, user.discriminator) == (member_name, member_dis):
        await ctx.guild.unban(user)
        await ctx.send(f'лошок петушок {member} был разбанен')


# добавление варна в систему варнов бд
@bot.command(name='add_warn', brief=dis_slow['add_warn'][0], description=dis_slow['add_warn'][1])
@commands.has_permissions(kick_members=True)
async def add_warn(ctx, member: discord.Member):
    if add_warn1(member):
        remove_warn(member)
        await member.kick(reason="3 warns")
        await ctx.send(f'{member} been kicked for to many warns!')
    else:
        await ctx.send(f'{member.mention} You Have been WARNED!!!')


# удаление варна из базы данных
@bot.command(name="remove_warn", brief=dis_slow['remove_warn'][0], description=dis_slow['remove_warn'][1])
@commands.has_permissions(kick_members=True)
async def remove_warn1(ctx, member: discord.Member):
    remove_warn(member, 1)
    await ctx.send(f'{member.mention} Your one warn has been removed')


# сдучайное от и до
@bot.command(name='randint', brief=dis_slow['randint'][0], description=dis_slow['randint'][1])
async def my_randint(ctx, min_int, max_int):
    num = random.randint(int(min_int), int(max_int))
    await ctx.send(num)


# реакция бота на сообщения проверка на "плохие слова" и так далее
@bot.listen('on_message')
async def whatever_you_want_to_call_it(message):
    if str(message.author) == 'soglyadatai#7322':
        return
    if message.content.startswith(prefix):
        return
    for i in ban_words:
        if i in message.content.lower():
            if add_warn1(message):
                await message.kick(reason="3 warns")
                remove_warn(message, -1)
                await message.channel.send(f'{message.author} been kicked for to many warns!')
            else:
                await message.channel.send(f'{message.author.mention} You Have been WARNED!!!')
            break
    if LOG_MSG_FLAG[0]:
        if LOG_MSG_FLAG[1] == str(message.channel):
            cur.execute(f"""UPDATE loding_tab SET msgs = msgs || '{
            str(message.author)}: {str(message.content)} {str(dt.datetime.now().strftime('%x %X'))}
'
             WHERE chennel = '{LOG_MSG_FLAG[1]}' AND id = (SELECT MAX(id) FROM loding_tab)""")
            con.commit()


# получение картинок котиков из API о котиках
@bot.command(name='cats', brief=dis_slow['cats'][0], description=dis_slow['cats'][1])
async def cats(ctx):
    response = requests.get(
        "https://api.thecatapi.com/v1/images/search").json()
    await ctx.send(response[0]['url'])


# получение картинок собачек из API о собачках
@bot.command(name='dogs', brief=dis_slow['dogs'][0], description=dis_slow['dogs'][1])
async def dogs(ctx):
    response = requests.get(
        "https://dog.ceo/api/breeds/image/random").json()
    await ctx.send(response['message'])


# добавление плохого слова в список плохих слов
@bot.command(name='add_bad_word', brief=dis_slow['add_bad_word'][0], description=dis_slow['add_bad_word'][1])
@commands.has_permissions(administrator=True)
async def add_ban_word(ctx, word):
    ban_words.append(word)
    await ctx.send(f"Bad word has been added")


# функция для добавления варна в базу данных при наличии трех варнов кик с сервера
def add_warn1(name):
    x = cur.execute(f"""SELECT * FROM warn_tab WHERE user = '{name}'""").fetchone()
    con.commit()
    if not x:
        cur.execute(f"""INSERT INTO warn_tab(user, warns) VALUES('{name}', 1)""")
        con.commit()
    else:
        cur.execute(f"""UPDATE warn_tab SET warns = warns + 1 WHERE user = '{name}'""")
        con.commit()
        y = cur.execute(f"""SELECT warns FROM warn_tab WHERE user = '{name}'""").fetchone()[0]
        if y >= 3:
            return True
        else:
            return False


# функция для удаления варнов из базы данных
def remove_warn(name, z=-1):
    print(z)
    if z < 0:
        cur.execute(f"""DELETE FROM warn_tab WHERE user = '{name}'""")
        con.commit()
    elif z > 0:
        cur.execute(f"""UPDATE warn_tab SET warns = warns - {z} WHERE user = '{name}'""")
        con.commit()


# новый лог сообщений
def new_log(channel):
    cur.execute(f"""
    INSERT INTO loding_tab(time_start, chennel, msgs) VALUES('{str(dt.datetime.now().strftime('%x %X'))}', '{channel}',
    '')
    """)
    con.commit()


# окончание лога
def end_log(channel):
    cur.execute(f"""
    UPDATE loding_tab SET time_end = '{str(dt.datetime.now().strftime('%x %X'))}'
     WHERE chennel = '{channel}' AND (id = (SELECT MAX(id) FROM loding_tab))
    """)
    con.commit()


# токен бота
TOKEN = 'OTY3MTExMzQ3Mzc0NTUxMDgw.YmLioQ.GX8eSjSty2kXtpHhiTmTDxhVn9Q'
# запуск бота
bot.run(TOKEN)
