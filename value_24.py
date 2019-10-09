import requests
import bs4
import json
import math
import lxml.html
import pandas as pd
from pymongo import MongoClient


def get_bs(url):
  return bs4.BeautifulSoup(requests.get(url).text, 'lxml')

def FindInfo(stockcode):
  url_header = 'http://comp.fnguide.com/SVO2/ASP/SVD_main.asp?pGB=1&gicode=A'
  url_footer = '&cID=&MenuYn=Y&ReportGB=&NewMenuID=11&stkGb=&strResearchYN='

  url = url_header + stockcode + url_footer

  html = lxml.html.parse(url)
  
  '''
  PER, PBR, 배당수익률 등
  '''
  packages = html.xpath('//div[@class="corp_group2"]/dl/dd/text()')

  STCInfo = []

  for valinfo in packages:
    STCInfo.append(valinfo)

  '''
  Business Summary
  '''
  packages = html.xpath('//ul[@id="bizSummaryContent"]/li/text()')

  for valinfo in packages:
    STCInfo.append(valinfo)

  return STCInfo


def get_payload(work_dt, pageNum, adjSEQ):
  payload = {'market':'0', 'industry':'G0', 'size':'0', 'workDT':work_dt, 'termCount':'6', 'currentPage':pageNum, 'orderKey':'I2', 'orderDirect':'D', \
           'jsonParam':'[{"Group":"I","SEQ":"2","MIN_VAL":"3279","MAX_VAL":"100000.00","Ogb":"3"}, \
           {"Group":"V","SEQ":"'+str(3+adjSEQ)+'","MIN_VAL":"0","MAX_VAL":"31886","Ogb":"2"}, \
           {"Group":"V","SEQ":"'+str(5+adjSEQ)+'","MIN_VAL":"0.20","MAX_VAL":"0.90","Ogb":"1"}, \
           {"Group":"V","SEQ":"'+str(11+adjSEQ)+'","MIN_VAL":"1.00","MAX_VAL":"2.00","Ogb":"1"}, \
           {"Group":"V","SEQ":"'+str(7+adjSEQ)+'","MIN_VAL":"0","MAX_VAL":"88970","Ogb":"2"}, \
           {"Group":"V","SEQ":"31","MIN_VAL":"1.00","MAX_VAL":"24","Ogb":"2"}]'}
  
  return payload


def m_db_init(coll):

  MONGO_HOST = "ds241668.mlab.com"
  MONGO_PORT = 41668
  MONGO_DB = "hyunsikhwang"
  MONGO_USER = "realg"
  MONGO_PASS = "ofsm9dml"
  
  connection = MongoClient(MONGO_HOST, MONGO_PORT)
  db = connection[MONGO_DB]
  check = db.authenticate(MONGO_USER, MONGO_PASS)
  collection = db[coll]
  
  return collection
 

def m_db_insert(collection, json):
  for item in json:
    collection.insert_one(item)


'''
>>>Step 1
데이터를 받아오기 위한 가장 최근 기준일자 정보(work_dt) 획득
select tag 중 id 가 "workDT-select" 인 최초 결과의 value 값을 받아옴
yyyy-mm-dd 형태로 되어있기 때문에 "-" 문자를 replace 로 제거
'''
url_1 = 'http://wise.thewm.co.kr/ASP/Screener/Screener1.asp?ud='
work_dt = get_bs(url_1).find('select', id='workDT-select').option['value'].replace('-', '')
#print(work_dt)

'''
>>>Step 2
Step 1 에서 얻은 기준일자를 적용하여 필터링 된 데이터 획득
jsonParam 파라미터
Group I / SEQ 2 : 시가총액, 1000억 이하
Group V / SEQ 3 : PER,  > 0
Group V / SEQ 5 : PBR, 0.2 ~ 0.9
Group V / SEQ 11 : PSR, 1 ~ 2
Group V / SEQ 7 : PCR, > 0
Group V / SEQ 31 : 배당수익률, > 1%
Ogb : 1 - 구간, 2 - 이상, 3 - 이하
FY0 대신 FY1 을 사용할 경우는 SEQ 을 1 씩 더하면 됨 
'''
adjSEQ = 0

url_2 = 'http://wise.thewm.co.kr/ASP/Screener/data/Screener_Termtabledata.asp'
pageNum = 1
payload = get_payload(work_dt, pageNum, adjSEQ)
'''payload = {'market':'0', 'industry':'G0', 'size':'0', 'workDT':work_dt, 'termCount':'6', 'currentPage':pageNum, 'orderKey':'I2', 'orderDirect':'D', \
           'jsonParam':'[{"Group":"I","SEQ":"2","MIN_VAL":"3279","MAX_VAL":"100000.00","Ogb":"3"}, \
           {"Group":"V","SEQ":"'+str(3+adjSEQ)+'","MIN_VAL":"0","MAX_VAL":"31886","Ogb":"2"}, \
           {"Group":"V","SEQ":"'+str(5+adjSEQ)+'","MIN_VAL":"0.20","MAX_VAL":"0.90","Ogb":"1"}, \
           {"Group":"V","SEQ":"'+str(11+adjSEQ)+'","MIN_VAL":"1.00","MAX_VAL":"2.00","Ogb":"1"}, \
           {"Group":"V","SEQ":"'+str(7+adjSEQ)+'","MIN_VAL":"0","MAX_VAL":"88970","Ogb":"2"}, \
           {"Group":"V","SEQ":"31","MIN_VAL":"1.00","MAX_VAL":"24","Ogb":"2"}]'}
'''
temp = requests.post(url_2, data=payload).text
data = json.loads(temp)

'''
>>>Step 3
결과 10 종목 표시
sAllCnt : 결과 목록 수
총 페이지 수 환산 : RoundUp(sAllCnt / 10, 0)
currentPage 반복해서 모든 결과 획득
'''
numPage = math.ceil(data['sAllCnt'] / 10)
result = []

for idx in range(numPage):
  pageNum = idx+1
  payload = get_payload(work_dt, pageNum, adjSEQ)
  tempR = requests.post(url_2, data=payload).text
  dataR = json.loads(tempR)
  for item in dataR['resultList']:
    result.append(item)

'''
>>>Step 4
전체 결과 확인(종목명, 종목코드)
'''
printStyle = 0
dfList = []
stockInfoUrlHeader = 'http://comp.fnguide.com/SVO2/ASP/SVD_main.asp?pGB=1&gicode=A'
stockInfoUrlFooter = '&cID=&MenuYn=Y&ReportGB=&NewMenuID=11&stkGb=&strResearchYN='

for idx, item in enumerate(result, start=1):
  stockInfo = FindInfo(item['CMP_CD'])
  #print(a[0].text)
  stockInfoUrl = stockInfoUrlHeader+item['CMP_CD']+stockInfoUrlFooter 
  print(idx, item['CMP_NM_KOR'], item['CMP_CD'], 'PER', stockInfo[0], 'PBR', stockInfo[3], '배당수익률', stockInfo[4], 'URL', stockInfoUrl)
  
  if printStyle == 0:
    dfList.append([item['CMP_NM_KOR'], item['CMP_CD'], stockInfo[0],  stockInfo[3], stockInfo[4], stockInfoUrl])
    df = pd.DataFrame(dfList, columns=("회사명", "종목코드", "PER", "PBR", "배당수익률", "URL"))
  elif printStyle == 1:
    dfList.append([item['CMP_NM_KOR'], item['CMP_CD'], stockInfo[0],  stockInfo[3], stockInfo[4], stockInfo[5] , stockInfo[6], stockInfoUrl])
    df = pd.DataFrame(dfList, columns=("회사명", "종목코드", "PER", "PBR", "배당수익률", "회사설명1", "회사설명2", "URL"))
    print(stockInfo[5], '\n', stockInfo[6], '\n')
  
# df.sort_values(by=['회사명'], axis=0, inplace=True)
print(df)

records = json.loads(df.T.to_json()).values()
print(records)

'''
>>>Step 5
mongoDB 적재
'''
dbSave = 1

if dbSave == 1:

  coll = 'test_invest'

  collection = m_db_init(coll)
  print(collection)

  collection.delete_many({})
  collection.insert_many(records)
