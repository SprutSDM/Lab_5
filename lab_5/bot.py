#encoding: utf
import telebot
import requests
import datetime
from bs4 import BeautifulSoup


access = {
    'token': '123',
    'domain': 'http://www.ifmo.ru/ru/schedule/0'}

d_week = {
    '/monday': '1',
    '/tuesday': '2',
    '/wednesday': '3',
    '/thursday': '4',
    '/friday': '5',
    '/saturday': '6',
    '/sunday': '7'}

day_week = {0:'/monday',
            1:'/tuesday',
            2:'/wednesday',
            3:'/thursday',
            4:'/friday',
            5:'/saturday',
            6:'/sunday'}

t_lessons = {'8:20-9:50': 0,
             '10:00-11:30': 1,
             '11:40-13:10': 2,
             '13:30-15:00': 3,
             '15:20-16:50': 4,}

times_lessons = {0: 820,
                 1: 1000,
                 2: 1140,
                 3: 1330,
                 4: 1520,
                 5: 2000}

bot = telebot.TeleBot(access['token'])


def get_page(group, week=''):
    if week != '':
        week += '/'
    url = '{domain}/{group}/{week}raspisanie_zanyatiy_{group}.htm'.format(
        domain=access['domain'],
        week=week,
        group=group)
    print(url)
    response = requests.get(url)
    web_page = response.text
    return web_page


def get_schedule(web_page, day):
    soup = BeautifulSoup(web_page, 'html5lib')
    #print(d_week[day])
    schedule_table = soup.find('table', attrs={'id': d_week[day] + 'day'})
    #print(schedule_table)
    
    times_list = schedule_table.find_all('td', attrs={'class': 'time'})
    times_list = [time.span.text for time in times_list]
    #print(times_list)
    
    locations_list = schedule_table.find_all('td', attrs={'class': 'room'})
    rooms_list = [room.dd.text if room.dd.text != '' else 'нет информации об аудитории' for room in locations_list]
    locations_list = [room.span.text for room in locations_list]
    
    
    lessons_list = schedule_table.find_all('td', attrs={'class': 'lesson'})
    lessons_list = [elem.dd.text + ', <b>' + elem.dt.text + '</b>' for elem in lessons_list]
    
    return times_list, rooms_list, locations_list, lessons_list


def _request_schedule(message, text, lesson_number=-1, displ=True, first_lesson=False):
    line = text.split()
    day = line[0].lower()
    if len(line) == 1:
        if displ:
            bot.send_message(message.chat.id, 
                             '<b>Не указанна группа!</b>',
                             parse_mode='HTML')
        return 1
    group = line[1].upper()
    week = ''
    if len(line) >= 3:
        week = '1' if line[2] == 'even' else '2'
    web_page = get_page(group, week)
    if web_page.find('Расписание не найдено') != -1:
        if displ:
            bot.send_message(message.chat.id, 
                             '<b>Расписание не найдено!</b>',
                             parse_mode='HTML')
        return 1
    if day == '/sunday':
        if displ:
            bot.send_message(message.chat.id, 
                             '<b>В этот день выходной!</b>',
                             parse_mode='HTML')
        return -1

    times_lst, rooms_lst, locations_lst, lessons_lst = get_schedule(web_page, day)
    resp = ''
    pr = False
    for time, room, location, lession in zip(times_lst, rooms_lst, 
                                             locations_lst, lessons_lst):
        print(lesson_number)
        print(time)
        if lesson_number != -1 and time.strip() in t_lessons and t_lessons[time.strip()] < lesson_number:
            continue
        resp += '<b>{}</b>, {}, {}. {}\n\n'.format(time.strip(), 
                                                 room.strip(), 
                                                 location.strip(), 
                                                 lession.strip())
        pr = True
        if first_lesson or lesson_number != -1:
            break
    if pr == False:
        resp = '<b>На сегодня все занятия закончились!</b>'
        print(line)
        return -1
    if displ:
        bot.send_message(message.chat.id, resp, parse_mode='HTML')
    return 1


@bot.message_handler(commands=['near_lesson'])
def request_schedule_near_lesson(message):
    line = message.text.split()
    is_even = int(datetime.datetime.today().strftime('%U')) % 2 == 0
    day = datetime.datetime.today().weekday()
    hour = int(datetime.datetime.today().strftime('%H%M'))
    if len(line) == 1:
        bot.send_message(message.chat.id,
                         '<b>Не указанна группа!</b>',
                         parse_mode='HTML')
        return    
    com = day_week[day] + ' ' + line[1]
    com += ' even' if is_even else ' odd'
    #print(com)
    find = False
    for i in range(len(times_lessons)):
        if times_lessons[i] > hour:
            break
    ans = _request_schedule(message, com, i, False, False)
    print(ans)
    if ans == 1:
        _request_schedule(message, com, i, True, False)
    else:
        while True:
            day += 1
            if day >= 6:
                day = 0
                is_even = not is_even
                com = day_week[day] + ' ' + line[1]
                com += ' even' if is_even else ' odd'
                #print(com)
                ans = _request_schedule(message, com, -1, False, True)
                if ans == 1:
                    _request_schedule(message, com, -1, True, True)
                    break

@bot.message_handler(commands=['all'])
def request_schedule_all(message):
    line = message.text.split()
    if len(line) == 1:
        bot.send_message(message.chat.id,
                         '<b>Не указанна группа!</b>',
                         parse_mode='HTML')
        return
    for i in range(6):
        bot.send_message(message.chat.id,
                         '<b>===' + day_week[i][1:] + '===</b>',
                         parse_mode='HTML')        
        com = day_week[i] + ' ' + ' '.join(line[1:])
        _request_schedule(message, com)


@bot.message_handler(commands=['tommorow'])
def request_schedule_tommorow(message):
    line = message.text.split()
    if len(line) == 1:
        bot.send_message(message.chat.id,
                         '<b>Не указанна группа!</b>',
                         parse_mode='HTML')
        return
    is_even = int(datetime.datetime.today().strftime('%U')) % 2 == 0
    day = datetime.datetime.today().weekday() + 1
    if day >= 6:
        day = 0
        is_even = not is_even
    com = day_week[day] + ' ' + line[1]
    com += ' even' if is_even else ' odd'
    _request_schedule(message, com)


@bot.message_handler(commands=['monday', 'tuesday', 'wednesday', 'thursday',
                               'friday', 'saturday', 'sunday'])
def request_schedule(message):
    line = message.text
    _request_schedule(message, line)
    

if __name__ == '__main__':
    bot.polling(none_stop=True)
