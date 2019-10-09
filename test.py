#%%

# -*- coding: utf-8 -*-
import requests
import bs4
import xml.etree
from datetime import datetime, timedelta
import json
import lxml
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def post_beautiful_soup(url, payload):
	return bs4.BeautifulSoup(requests.post(url, data=payload).text, "lxml")


def get_beautiful_soup(url):
	return bs4.BeautifulSoup(requests.get(url).text, "lxml")


def millis():
	return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)


milli_timestamp = millis()
#print(milli_timestamp)

end_dd = datetime.today().strftime("%Y%m%d")
strt_dd = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

data_type = {}
data_type['IDX'] = 0
data_type['PER'] = 1
data_type['PBR'] = 2
data_type['CPN'] = 3

xx = 'CPN'

url_1 = []
#지수
url_1.append('http://marketdata.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=MKD%2F10%2F1001%2F10010101%2Fmkd10010101_07&name=selectbox&_=' + str(milli_timestamp))

#PER
url_1.append('http://marketdata.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=MKD%2F13%2F1301%2F13010103%2Fmkd13010103_02&name=selectbox&_=' + str(milli_timestamp))

#PBR
url_1.append('http://marketdata.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=MKD%2F13%2F1301%2F13010104%2Fmkd13010104_02&name=selectbox&_=' + str(milli_timestamp))

#개별종목정보
url_1.append('http://marketdata.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=MKD%2F13%2F1302%2F13020401%2Fmkd13020401_chart&name=chart&_=' + str(milli_timestamp))

#변동성지수
url_1.append('http://marketdata.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=MKD%2F13%2F1301%2F13010302%2Fmkd13010302&name=form&_=' + str(milli_timestamp))

#url_2 = 'http://marketdata.krx.co.kr/contents/MKD/99/MKD99000001.jspx?type=1&ind_type=1001&period_strt_dd=20170804&period_end_dd=20170811&pagePath=%2Fcontents%2FMKD%2F10%2F1001%2F10010101%2FMKD10010101.jsp&code=' + OTP + '&pageFirstCall=Y'
url_2 = 'http://marketdata.krx.co.kr/contents/MKD/99/MKD99000001.jspx'


pagePath = []
#지수
pagePath.append('/contents/MKD/10/1001/10010101/MKD10010101.jsp')

#PER
pagePath.append('/contents/MKD/13/1301/13010103/MKD13010103.jsp')

#PBR
pagePath.append('/contents/MKD/13/1301/13010103/MKD13010104.jsp')

#개별종목
pagePath.append('/contents/MKD/13/1302/13020401/MKD13020401.jsp')

#파생상품지수
pagePath.append('/contents/MKD/13/1301/13010302/MKD13010302.jsp')

headers = {'Content-Type': 'application/xml'} 

OTP = get_beautiful_soup(url_1[0]).find('body').text
payload = {'type':'1', 'ind_type':'1001', 'period_strt_dd':strt_dd, 'period_end_dd':end_dd, 'pagePath':'pagePath:'+pagePath[0],'code':OTP, 'pageFirstCall':'Y'}


MktData = post_beautiful_soup(url_2, payload)
data = json.loads(MktData.text)
#print(data)
elevations = json.dumps(data['block1'])
a = pd.read_json(elevations)
aaa = pd.DataFrame(a)
print(aaa)
new_df = aaa
new_df['work_dt'] = pd.to_datetime(aaa['work_dt'])
new_df['indx'] = pd.to_numeric(aaa['indx'].astype(str).str.replace(',',''), errors='coerce')
new_df.set_index('work_dt')


fig = new_df.plot(x='work_dt', y='indx').get_figure()
fig.savefig('test.png')
#plt.show()