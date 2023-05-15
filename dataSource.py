import pandas as pd                                 #pip install pandas
import requests                                     #pip install requests
import bs4                                          #pip install beautifulsoup4
from geopy.distance import great_circle as GRC      #pip install geopy(The great circle distance,大圆距离)
#from geopy.distance import geodesic as GD          #pip install geopy(Geodesic measure,大地测量法)
                                                    #(Herversine formula)

def DownLoadAtmData():      
    url='https://www-api.moda.gov.tw/OpenData/Files/4161'
    response = requests.get(url)
    response.encoding='utf-8'        
    if response.ok:        
        file=open('atmRowData.csv',mode='w',encoding='utf-8',newline='')
        file.write(response.text)
        file.close()
        
        #modify fieldname from chinese to english
        atmData = pd.read_csv('atmRowData.csv')

        columnNewName = {'編號':'no','銀行代號':'bankcode','分行代號':'branchcode','所屬銀行簡稱':'branchname','裝設型態':'type','裝設地點類別':'placetype','裝設地點':'place','所屬縣市':'county','鄉鎮縣市別':'district','地址':'address','英文地址':'address_eng','區碼':'distcode','聯絡電話':'tel','服務型態':'servicetype','符合輪椅使用':'wheelchair','視障語音':'voice','符合輪椅使用且環境亦符合':'wheelchair_envir','視障語音且環境亦符合':'voice_evnir','備註':'memo','座標X軸':'longitude','座標Y軸':'latitude'}        
        atmData = atmData.rename(columns=columnNewName)  

        #Extra Processing of Data--------------------------------------
        #Error Data-1: atmData.loc[17841,'latitude']
        if atmData.loc[17841,'latitude'] == '22.9991441,120':
            atmData.loc[17841,'latitude'] ='22.9991441'
        atmData['latitude'] = atmData['latitude'].astype(float)

        #Error Data-2: atmData.longitude<30
        atmData = atmData[atmData['longitude']>30]

        #雲林縣臺西鄕/台西鄕,屏東縣三地門/三地門鄕---------------------
        atmData.loc[atmData['district'].str.contains('臺西鄉'), 'district'] = '台西鄉' 
        atmData.loc[atmData['district'].str.contains('三地門'), 'district'] = '三地門鄉' 
        
        # replace fields of placetype : 全聯,家樂福---------------------
        atmData.loc[atmData['place'].str.contains('全聯'), 'placetype'] = 'J1' 
        atmData.loc[atmData['place'].str.contains('家樂福'), 'placetype'] = 'J1'

        #Data is NaN(Null)值, change to ' ',因進行value_counts時,null被忽略
        atmData['placetype']        = atmData['placetype'].fillna(value=' ')
        atmData['wheelchair_envir'] = atmData['wheelchair_envir'].fillna(value=' ')        
        atmData['voice_evnir']      = atmData['voice_evnir'].fillna(value=' ')       
        atmData['memo']             = atmData['memo'].fillna(value=' ')
        
        #Data save
        atmData.to_csv('atmData.csv',encoding='utf_8_sig',index=False)
        #print(atmData.dtypes)   
        print("下載成功")     
    else:
        print("下載失敗")

#Latitude(經度) Longitude(緯度)
class filterAtmListFromInquiry():
    def __init__(self,inquiryAddressFull, radiusValue, atmData):
        self.Address = inquiryAddressFull
        self.atmData = atmData  
        self.radiusValue = radiusValue
        
        # 正常運作: 使用爬蟲
        try: 
            url = "https://www.google.com/maps/place?q=" + self.Address
            html = requests.get(url)
            soup = bs4.BeautifulSoup(html.text, "html.parser")
            text = soup.prettify()
            initial_pos = text.find(";window.APP_INITIALIZATION_STATE") #尋找;window.APP_INITIALIZATION_STATE所在位置
            data = text[initial_pos+36 : initial_pos+85]
            line = tuple(data.split(','))   # ex:3672.9530075659873,120.2050514149671,22.988751484
            self.longitude = float(line[1])      # longitude:經度,X軸
            self.latitude = float(line[2])       # latitude:緯度,Y軸
            print("經緯度資料爬蟲成功")
            print(f"{self.Address}-- longitude:{self.longitude}, latitude: {self.latitude}")
        except:
            print("經緯度資料爬蟲失敗:")
            return
        '''
        # 替代方法-2: 經緯度資料爬蟲失敗, 用以下方法
        #### 新北市板橋區民生路二段232號-- longitude:121.46655211500601, latitude: 25.022648983
        self.longitude = 121.46655211500601
        self.latitude = 25.022648983
        
        #### 台北市大安區信義路三段153號-- longitude:121.54039791500624, latitude: 25.03380218
        self.longitude = 121.54039791500624
        self.latitude = 25.03380218 
        
        #### 嘉義市西區友愛路288號7樓之3-- longitude:120.43168811497637, latitude: 23.484060684
        self.longitude = 120.43168811497637
        self.latitude = 23.484060684   
        
        #### 台北市中山區中山北路二段113號-- longitude:121.52101491500682, latitude: 25.060587683
        self.longitude = 121.52101491500682 
        self.latitude = 25.060587683
        
        #### 高雄市楠梓區金富街1號-- longitude:120.31701181496221, latitude: 22.723982485
        self.longitude = 120.31701181496221
        self.latitude = 22.723982485     
        '''
    def getDistanceBetweenPoints(self):
        # groupby data
        atmAddressData = self.atmData[['bankcode','branchname','type','placetype','place','county','district','address','wheelchair_envir','voice_evnir','memo','longitude','latitude']].value_counts().reset_index()
        atmAddressData = atmAddressData.rename(columns={'count': 'units'}).reset_index()
                
        # calculate distance and filter 
        distance = []        
        for i in range(0, atmAddressData["address"].size):
            calDistance = GRC((self.latitude,self.longitude),(atmAddressData.loc[i,'latitude'],atmAddressData.loc[i,'longitude'])).km*1000 
            distance.append(calDistance)                   
        atmAddressData['distanceM'] = distance        
        #print(atmAddressData.dtypes)
        
        # convert type,placetype: 補k2
        atmAddressData['type'] = atmAddressData['type'].map({1:'行內',2:'行外'}).astype('object')
        dataMap = { 'A1':'火車站(特等站)','A2':'火車站(一等站)','A3':'火車站(二等站)','A4':'火車站(其他等級)',
                    'B1':'地方政府(直轄市)','B2':'地方政府(縣市)',
                    'H1':'醫學中心','H2':'區域醫院','H3':'地區醫院','H4':'其他等級醫院',
                    'I1':'大專院校以上','I2':'高級中等學校','I3':'國中','I4':'小學',
                    'C1':'其他公務機關',
                    'D1':'高鐵站','E1':'長途客運站','F1':'捷運站','G1':'機場',
                    'J1':'大型賣場及百貨公司','K1':'其他公共場所','K2':'其他公共場所',
                    'L1':'便利商店','O1':'其他',' ':' ' }
        atmAddressData['placetype'] = atmAddressData['placetype'].map(dataMap).astype('object')

        # filter data based on radius
        self.filterAtmList = atmAddressData[atmAddressData['distanceM'] <= self.radiusValue] 
        self.filterAtmList = self.filterAtmList.sort_values(by = ['distanceM','county','district','address'])
        self.filterAtmList = self.filterAtmList[['bankcode','branchname','type','placetype','place','county','district','address','wheelchair_envir','voice_evnir','units','distanceM','memo','longitude','latitude']]
        #print(self.filterAtmList.index)
        
        return self.filterAtmList, self.longitude, self.latitude