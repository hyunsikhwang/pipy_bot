import telegram   #텔레그램 모듈을 가져옵니다.
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from lxml import etree
import timeit
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from urllib.request import urlopen
import bs4
from datetime import datetime, timedelta
import json
import pandas as pd
import lxml.html
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import configparser
import FinanceDataReader as fdr
from pymongo import MongoClient
import configparser
import pyEX


print('start telegram chat bot')

def import_json(json_name):
    with open(json_name, 'r') as f:
        config = json.load(f)
    
    return config

def get_token(config):
    telegram_token = config['telegram']
    seibro_token = config['seibro']

    return telegram_token, seibro_token

json_name = 'tokens.json'
config = import_json(json_name)
telegram_token, seibro_token = get_token(config)

#bot = telegram.Bot(token = my_token)
bot = telegram.Bot(token = telegram_token)

updates = bot.getUpdates()
for i in updates:
    print(i)


#여기부터 주식명 조회

def find_stock_info(comp_name, token):

    seibro_token = token
    url = 'http://api.seibro.or.kr/openapi/service/StockSvc/getStkIsinByNmN1?ServiceKey=' + seibro_token + '&secnNm=' + quote(comp_name) + '&pageNo=1&numOfRows=500'

    xml = content = urlopen(url).read()
    context = etree.fromstring(xml)

    i = 0
    temp = etree.XML(xml)

    retlist = []
    retlist1 = []
    retlist2 = []

    start = timeit.default_timer()

    srch = etree.XPath('//item')

    r = context.xpath('//item/korSecnNm/text()')
    i = 0

    for elem in srch(temp):

        if len(srch(temp)[i]) == 7:
            retlist1.append(srch(temp)[i][4].text)
            retlist2.append(srch(temp)[i][6].text)
            #print(retlist1[count], retlist2[count])
        i = i + 1

    return [retlist1, retlist2]

#fnguide 에서 주식 종목별 valuation infomation 을 가져와서 리스트에 저장
def FindInfo(stockcode):
    url_header = 'http://comp.fnguide.com/SVO2/ASP/SVD_main.asp?pGB=1&gicode=A'
    url_footer = '&cID=&MenuYn=Y&ReportGB=&NewMenuID=11&stkGb=&strResearchYN='

    url = url_header + stockcode + url_footer

    html = lxml.html.parse(url)

    packages = html.xpath('//div[@class="corp_group2"]/dl/dd/text()')

    STCInfo = []

    for valinfo in packages:
        STCInfo.append(valinfo)
 
    return STCInfo

code_map = {
        'CD91' : 4000,
        '1Y':3006,
        '3Y':3000,
        '5Y':3007,
        '10Y':3013,
        '20Y':3014,
        '30Y':3017,
        '50Y':3018,
        '3Y_AA-':3009,
        '3Y_BBB-':3010
        }

def build_query(start_date, end_date, codes):
    query = '<?xml version="1.0" encoding="utf-8"?><message>' \
            + '<proframeHeader><pfmAppName>BIS-KOFIABOND</pfmAppName>' \
            + '<pfmSvcName>BISLastAskPrcROPSrchSO</pfmSvcName><pfmFnName>listTrm</pfmFnName>' \
            + '</proframeHeader>  <systemHeader></systemHeader><BISComDspDatDTO>' \
            + '<val1>DD</val1>' 
    #appending start and end dates
    query += '<val2>{}</val2>'.format(start_date)
    query += '<val3>{}</val3>'.format(end_date)
    query += '<val4>1530</val4>'
    
    index = 5
    for code in codes:
        query += '<val{}>{}</val{}>'.format(index, code, index)
        index += 1
    
    query += '</BISComDspDatDTO></message>'
    return query


def toDf(xmlstring, headers):
    root = ET.fromstring(xmlstring)
    dates = []
    retDict = {}
    
    for h in headers:
        retDict[h] = []
    
    skip_index = 1
    for data in root.iter('BISComDspDatDTO'):
        if skip_index <=2 :
            skip_index += 1
            continue
        
        dates.append(data.find('val1').text)
        index = 2
        for h in headers:
            retDict[h].append(data.find('val{}'.format(index)).text)
            index +=1
        
    return pd.DataFrame(retDict, index=dates).reindex_axis(headers, axis = 1)


def cmd_bond2():

    target = ['1Y', '3Y', '5Y', '10Y', '20Y', '30Y']
    codes = [code_map.get(t) for t in target]

    today = datetime.today()
    today_7 = today - timedelta(7)

    query = build_query(today_7.strftime('%Y%m%d'), today.strftime('%Y%m%d'), codes)
    res = requests.post("http://www.kofiabond.or.kr/proframeWeb/XMLSERVICES/", data=query)
    df = toDf(res.text, target)

    df = df.head(2)
    df.loc['전일대비'] = pd.to_numeric(df.ix[0]) - pd.to_numeric(df.ix[1])
    pd.options.display.float_format = '{:,.3f}'.format
    df.drop(df.index[1], inplace=True)

    return str(df.head(2).transpose())


def left(s, amount):
    return s[:amount]

def right(s, amount):
    return s[-amount:]

def mid(s, offset, amount):
    return s[offset:offset+amount]

def post_beautiful_soup(url, payload):
	return bs4.BeautifulSoup(requests.post(url, data=payload).text, "html5lib")

def get_beautiful_soup(url):
	return bs4.BeautifulSoup(requests.get(url).text, "html5lib")

def millis():
    return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)


# message reply function
def get_message(bot, update) :

    update.message.reply_text("잠시만요...")
    #print(update.message.text)
    comp_text = update.message.text
    stock_list = find_stock_info(comp_text, seibro_token)
    update.message.reply_text(update.message.text + ' 에 대해서 총 ' + str(len(stock_list[0])) + ' 개의 결과가 검색되었습니다.')
    
    #검색된 종목 리스트 중 입력명과 일치하는 이름이 있는 경우 해당 종목의 정보를 바로 메시지로 전달
    find_exact = False
    count = 0
    for item in stock_list[0]:
        if item == update.message.text:
            find_exact = True
            break
        count += 1

    #검색된 종목 리스트 중 입력명과 일치하는 이름이 없는 경우에 해당 리스트를 커스텀 키보드로 표시
    if len(stock_list[0]) > 0:
        stock_str = '\n'.join([str(a) + '\t' + b for a,b in zip(stock_list[0], stock_list[1])])
        #print(stock_str)
        kb = []
        for item in stock_list[0]:
            kb.append([telegram.KeyboardButton(item)])
        kb.append([telegram.KeyboardButton('/close')])
        kb_markup = telegram.ReplyKeyboardMarkup(kb)
        bot.send_message(chat_id=update.message.chat_id,
                        text="검색을 원하시는 종목을 선택해주세요.",
                        reply_markup=kb_markup)
    else:
        stock_str = '해당 단어를 포함한 회사가 없네요..?'
    update.message.reply_text(stock_str)
    
    if find_exact == True:
        update.message.reply_text("입력하신 이름과 일치하는 회사가 있습니다..!")
        stock_info = []
        stock_info = FindInfo(stock_list[1][count])
        update.message.reply_text(update.message.text + '/' + stock_list[0][count] + '\n' + \
                                  'PER ' + stock_info[0] + '\n' + \
                                  'PBR ' + stock_info[3] + '\n' + \
                                  '배당률 ' + stock_info[4])


# help reply function
def help_command(bot, update) :
    update.message.reply_text("무엇을 도와드릴까요?")
    kb = [[telegram.KeyboardButton('/help'), telegram.KeyboardButton('/index')],
          [telegram.KeyboardButton('/per'), telegram.KeyboardButton('/pbr')],
          [telegram.KeyboardButton('/bond'), telegram.KeyboardButton('/recommend'), telegram.KeyboardButton('/vol')],
          [telegram.KeyboardButton('/fx'), telegram.KeyboardButton('/usstock')]]
    kb_markup = telegram.ReplyKeyboardMarkup(kb)
    bot.send_message(chat_id=update.message.chat_id,
                     text="커스텀 키보드 테스트중입니다.",
                     reply_markup=kb_markup)


def close_command(bot, update) :
    kb = [[telegram.KeyboardButton('/help'), telegram.KeyboardButton('/index')],
          [telegram.KeyboardButton('/per'), telegram.KeyboardButton('/pbr')],
          [telegram.KeyboardButton('/bond'), telegram.KeyboardButton('/recommend'), telegram.KeyboardButton('/vol')],
          [telegram.KeyboardButton('/fx'), telegram.KeyboardButton('/usstock')]]
    kb_markup = telegram.ReplyKeyboardMarkup(kb)
    bot.send_message(chat_id=update.message.chat_id,
                     text="종목 검색 끝...",
                     reply_markup=kb_markup)

# PER 조회
def per_command(bot, update) :
    update.message.reply_text("잠시만요...")

    milli_timestamp = millis()

    url_1 = 'http://marketdata.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=MKD%2F13%2F1301%2F13010103%2Fmkd13010103_02&name=selectbox&_=' + str(milli_timestamp)
    url_2 = 'http://marketdata.krx.co.kr/contents/MKD/99/MKD99000001.jspx'
    pagePath = '/contents/MKD/13/1301/13010103/MKD13010103.jsp'

    end_dd = datetime.today().strftime("%Y%m%d")
    strt_dd = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    #strt_dd = str(datetime.utcnow().year) + '0101'

    OTP = get_beautiful_soup(url_1).find('body').text
    payload = {'type':'kospi', 'period_selector':'day', 'fromdate':strt_dd, 'todate':end_dd, 'pagePath':'pagePath:'+pagePath,'code':OTP}

    MktData = post_beautiful_soup(url_2, payload)

    data = json.loads(MktData.text)

    results = []
    if data['block1'][0]['idx_type1'] == '-' or data['block1'][0]['idx_type1'] == '0.00':
        results.append(data['block1'][1]['trd_dd'] + '\t' + data['block1'][1]['idx_type1'] + '\t' + data['block1'][1]['idx_type2'])
    else:
        results.append(data['block1'][0]['trd_dd'] + '\t' + data['block1'][0]['idx_type1'] + '\t' + data['block1'][0]['idx_type2'])

    results_str = '\n'.join(results)

    update.message.reply_text(results_str)


# PBR 조회
def pbr_command(bot, update) :
    update.message.reply_text("잠시만요...")

    milli_timestamp = millis()

    url_1 = 'http://marketdata.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=MKD%2F13%2F1301%2F13010104%2Fmkd13010104_02&name=selectbox&_=' + str(milli_timestamp)
    url_2 = 'http://marketdata.krx.co.kr/contents/MKD/99/MKD99000001.jspx'
    pagePath = '/contents/MKD/13/1301/13010103/MKD13010104.jsp'

    end_dd = datetime.today().strftime("%Y%m%d")
    strt_dd = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    #strt_dd = str(datetime.utcnow().year) + '0101'

    OTP = get_beautiful_soup(url_1).find('body').text
    payload = {'type':'kospi', 'period_selector':'day', 'fromdate':strt_dd, 'todate': end_dd, 'pagePath':'pagePath:'+pagePath,'code':OTP}

    MktData = post_beautiful_soup(url_2, payload)

    data = json.loads(MktData.text)

    results = []
    if data['block1'][0]['idx_type1'] == '-' or data['block1'][0]['idx_type1'] == '0.00':
        results.append(data['block1'][1]['trd_dd'] + '\t' + data['block1'][1]['idx_type1'] + '\t' + data['block1'][1]['idx_type2'])
    else:
        results.append(data['block1'][0]['trd_dd'] + '\t' + data['block1'][0]['idx_type1'] + '\t' + data['block1'][0]['idx_type2'])

    results_str = '\n'.join(results)

    update.message.reply_text(results_str)


# 주가지수 조회
def index_command(bot, update) :

    update.message.reply_text("잠시만요...")

    milli_timestamp = millis()

    url_1 = 'http://marketdata.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=MKD%2F10%2F1001%2F10010101%2Fmkd10010101_07&name=selectbox&_=' + str(milli_timestamp)
    url_2 = 'http://marketdata.krx.co.kr/contents/MKD/99/MKD99000001.jspx'
    pagePath = '/contents/MKD/10/1001/10010101/MKD10010101.jsp'

    end_dd = datetime.today().strftime("%Y%m%d")
    strt_dd = (datetime.now() - timedelta(days=364)).strftime("%Y%m%d")
    frst_mon_strt_dd = datetime.today().strftime("%Y-01-01")
    frst_day_strt_dd = datetime.today().strftime("%Y-%m-01")
    frst_mon_end_dd = datetime.today().strftime("%Y-01-31")


    OTP = get_beautiful_soup(url_1).find('body').text
    payload = {'type':'1', 'ind_type':'1001', 'period_strt_dd':strt_dd, 'period_end_dd':end_dd, 'pagePath':'pagePath:'+pagePath,'code':OTP, 'pageFirstCall':'Y'}
    MktData = post_beautiful_soup(url_2, payload)
    data = json.loads(MktData.text)

    elevations = json.dumps(data['block1'])
    day_one = pd.read_json(elevations)
    org_df = pd.DataFrame(day_one)

    day_one['work_dt'] = pd.to_datetime(day_one['work_dt'])
    #매년(현재 날짜 기준) 첫번째 영업일을 구하기 위한 mask
    mask = (day_one['work_dt'] > frst_mon_strt_dd) & (day_one['work_dt'] <= frst_mon_end_dd)
    #매월(현재 날짜 기준) 첫번째 영업일을 구하기 위한 mask
    mask_mon = (day_one['work_dt'] >= frst_day_strt_dd) & (day_one['work_dt'] <= end_dd)
    
    # print(day_one.loc[mask_mon].tail(1)['work_dt'].to_string(index=False) + '\t' + day_one.loc[mask_mon].tail(1)['indx'].to_string(index=False))

    results = []
    results.append(data['block1'][0]['work_dt'] + '\t' + data['block1'][0]['indx'])
    results.append(data['block1'][1]['work_dt'] + '\t' + data['block1'][1]['indx'])
    results.append(day_one.loc[mask_mon].tail(1)['work_dt'].to_string(index=False) + '\t' + day_one.loc[mask_mon].tail(1)['indx'].to_string(index=False))
    results.append(day_one.loc[mask].tail(1)['work_dt'].to_string(index=False) + '\t' + day_one.loc[mask].tail(1)['indx'].to_string(index=False))

    kospi_curr = float(data['block1'][0]['indx'].replace(',',''))
    kospi_mon_1 = float(day_one.loc[mask_mon].tail(1)['indx'].to_string(index=False).replace(',',''))
    kospi_day_1 = float(day_one.loc[mask].tail(1)['indx'].to_string(index=False).replace(',',''))
    kospi_ratio_mon = (kospi_curr / kospi_mon_1 - 1) * 100
    kospi_ratio = (kospi_curr / kospi_day_1 - 1) * 100
    results.append('월초대비 {:.2f}%'.format(kospi_ratio_mon))
    results.append('연초대비 {:.2f}%'.format(kospi_ratio))

    results_str = '\n'.join(results)

    update.message.reply_text(results_str)


    new_df = org_df
    new_df['work_dt'] = pd.to_datetime(org_df['work_dt'])
    new_df['indx'] = pd.to_numeric(org_df['indx'].astype(str).str.replace(',',''), errors='coerce')
    new_df.set_index('work_dt')

    fig = new_df.plot(x='work_dt', y='indx').get_figure()
    fig.savefig('index.png')
    print('index plot saved')
    bot.send_photo(chat_id=update.message.chat_id, photo=open('./index.png', 'rb'))


# 채권금리 조회
def bond_command(bot, update) :
    update.message.reply_text('잠시만요...')

    bond_msg = cmd_bond2()

    update.message.reply_text(bond_msg)


def import_json(json_name):
  with open(json_name, 'r') as f:
    config = json.load(f)
    
  return config

def m_db_init(coll, config):

  MONGO_HOST = config['mlab']['MONGO_HOST']
  MONGO_PORT = config['mlab']['MONGO_PORT']
  MONGO_DB = config['mlab']['MONGO_DB']
  MONGO_USER = config['mlab']['MONGO_USER']
  MONGO_PASS = config['mlab']['MONGO_PASS']

  connection = MongoClient(MONGO_HOST, MONGO_PORT)
  db = connection[MONGO_DB]
  check = db.authenticate(MONGO_USER, MONGO_PASS)
  collection = db[coll]
  
  return collection


#추천종목 조회
def recommend_command(bot, update):
    update.message.reply_text('잠시만요...')
    json_name = 'config.json'
    config = import_json(json_name)
    coll = 'test_invest'
    collection = m_db_init(coll, config)
    result = collection.find({}, {'회사명':1, '종목코드':1, 'URL':1}).sort("회사명")

    recommend = ''
    for idx, item in enumerate(result):
        recommend = recommend + str(idx+1) + '\t'
        #for key, value in item.items():
        #print(idx, item)
        recommend = recommend + item['종목코드'] + '\t' + \
            '['+item['회사명'] + ']' + \
            '('+item['URL'] + ')'
        recommend = recommend + '\n'
    
    #print(recommend)
    bot.send_message(chat_id=update.message.chat_id, text=recommend, parse_mode=telegram.ParseMode.MARKDOWN)
    #update.message.reply_text(recommend)


#변동성지수 조회
def vol_command(bot, update) :
    update.message.reply_text('잠시만요...')

    milli_timestamp = millis()

    url_1 = 'http://marketdata.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=MKD%2F13%2F1301%2F13010302%2Fmkd13010302&name=form&_=' + str(milli_timestamp)
    url_2 = 'http://marketdata.krx.co.kr/contents/MKD/99/MKD99000001.jspx'
    pagePath = '/contents/MKD/13/1301/13010302/MKD13010302.jsp'

    end_dd = datetime.today().strftime("%Y%m%d")
    strt_dd = (datetime.now() - timedelta(days=364)).strftime("%Y%m%d")
    frst_mon_strt_dd = datetime.today().strftime("%Y-01-01")
    frst_mon_end_dd = datetime.today().strftime("%Y-01-31")
    OTP = get_beautiful_soup(url_1).find('body').text
    payload = {'type':'6', 'ind_type':'1300', 'period_strt_dd':strt_dd, 'period_end_dd':end_dd, 'pagePath':'pagePath:'+pagePath,'code':OTP}
    MktData = post_beautiful_soup(url_2, payload)
    data = json.loads(MktData.text)

    elevations = json.dumps(data['block1'])
    day_one = pd.read_json(elevations)
    org_df = pd.DataFrame(day_one)

    day_one['work_dt'] = pd.to_datetime(day_one['work_dt'])
    mask = (day_one['work_dt'] > frst_mon_strt_dd) & (day_one['work_dt'] <= frst_mon_end_dd)

    results = []
    results.append(data['block1'][0]['work_dt'] + '\t' + data['block1'][0]['indx'])
    results.append(data['block1'][1]['work_dt'] + '\t' + data['block1'][1]['indx'])
    results.append(day_one.loc[mask].tail(1)['work_dt'].to_string(index=False) + '\t' + day_one.loc[mask].tail(1)['indx'].to_string(index=False))

    kospi_curr = float(data['block1'][0]['indx'].replace(',',''))
    kospi_day_1 = float(day_one.loc[mask].tail(1)['indx'].to_string(index=False).replace(',',''))
    kospi_ratio = (kospi_curr / kospi_day_1 - 1) * 100
    results.append('연초대비 {:.2f}%'.format(kospi_ratio))

    results_str = '\n'.join(results)

    update.message.reply_text(results_str)


    new_df = org_df
    new_df['work_dt'] = pd.to_datetime(org_df['work_dt'])
    new_df.set_index('work_dt')

    fig = new_df.plot(x='work_dt', y='indx').get_figure()
    fig.savefig('vol.png')
    print('vol plot saved')
    bot.send_photo(chat_id=update.message.chat_id, photo=open('./vol.png', 'rb'))

    mask = (new_df['work_dt'] > frst_mon_strt_dd) & (new_df['work_dt'] <= frst_mon_end_dd)


def fx_command(bot, update):
    today_dt = datetime.utcnow().strftime('%Y-%m-%d')
    ystrday_dt = (datetime.utcnow() - timedelta(1)).strftime('%Y-%m-%d')

    update.message.reply_text('잠시만요...')

    try:
            
        packages_USD = fdr.DataReader('USD/KRW', today_dt)['Close']
        packages_JPY = fdr.DataReader('JPY/KRW', today_dt)['Close']
        packages_EUR = fdr.DataReader('EUR/KRW', today_dt)['Close']

        FXRatesInfo = '환율 정보\n'
        for item in packages_USD:
            FXRatesInfo = FXRatesInfo + '1달러당 {:.2f}원 입니다.\n'.format(item)
        for item in packages_JPY:
            FXRatesInfo = FXRatesInfo + '100엔당 {:.2f}원 입니다.\n'.format(item*100)
        for item in packages_EUR:
            FXRatesInfo = FXRatesInfo + '1유로당 {:.2f}원 입니다.'.format(item)
    except Exception as ex:
        FXRatesInfo = '에러가 발생했습니다.\n' + str(ex)

    update.message.reply_text(FXRatesInfo)


def usstock_command(bot, update) :

    update.message.reply_text('잠시만요...')

    stockList = ['GOOGL', 'BRK.B', 'AMZN', 'DIS', 'BABA', 'V', 'MSFT']
    results = []

    for item in stockList:
        #URL = 'https://api.iextrading.com/1.0/stock/' + item + '/quote'
        #temp = requests.get(URL).text
        #print(temp)
        #data = json.loads(temp)
        data = pyEX.stocks.book(symbol=item)['quote']
        #print(URL)
        results.append(data['symbol'] + ' ' + str(data['peRatio']))

    results_str = '\n'.join(results)
    #print(results_str)

    update.message.reply_text(results_str)


updater = Updater(telegram_token)

message_handler = MessageHandler(Filters.text, get_message)
updater.dispatcher.add_handler(message_handler)

help_handler = CommandHandler('help', help_command)
updater.dispatcher.add_handler(help_handler)

close_handler = CommandHandler('close', close_command)
updater.dispatcher.add_handler(close_handler)

per_handler = CommandHandler('per', per_command)
updater.dispatcher.add_handler(per_handler)

pbr_handler = CommandHandler('pbr', pbr_command)
updater.dispatcher.add_handler(pbr_handler)

index_handler = CommandHandler('index', index_command)
updater.dispatcher.add_handler(index_handler)

bond_handler = CommandHandler('bond', bond_command)
updater.dispatcher.add_handler(bond_handler)

recommend_handler = CommandHandler('recommend', recommend_command)
updater.dispatcher.add_handler(recommend_handler)

vol_handler = CommandHandler('vol', vol_command)
updater.dispatcher.add_handler(vol_handler)

fx_handler = CommandHandler('fx', fx_command)
updater.dispatcher.add_handler(fx_handler)

usstock_handler = CommandHandler('usstock', usstock_command)
updater.dispatcher.add_handler(usstock_handler)

updater.start_polling(timeout=3, clean=True)
updater.idle()


