from tool.geofunc import GeoFunc
import pandas as pd
import json

def getData(index):
    '''エラーデータセット（中空）：han,jakobs1,jakobs2 '''
    '''形状数が多すぎて暫定的に未処理：shapes、shirt、swim、trousers'''
    name=["ga","albano","blaz1","blaz2","dighe1","dighe2","fu","han","jakobs1","jakobs2","mao","marques","shapes","shirts","swim","trousers"]
    print(name[index],"データセットの処理を開始")
    '''暫定的に幅は考慮せず、すべてスケーリングで表現'''
    scale=[100,0.5,100,100,20,20,20,10,20,20,0.5,20,50]
    print(scale[index],"倍にスケーリング")
    df = pd.read_csv("data/"+name[index]+".csv")
    polygons=[]
    # print(df.head())
    # exit()
    for i in range(0,df.shape[0]):
        for j in range(0,df['num'][i]):
            # 頂点座標の読み込み
            poly=json.loads(df['polygon'][i])
            
            GeoFunc.normData(poly,scale[index])
            polygons.append(poly)
    return polygons
