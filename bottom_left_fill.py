"""
该文件实现了主要基于序列的排样算法
-----------------------------------
Created on Wed Dec 11, 2019
@author: seanys,prinway
-----------------------------------
"""
import numpy as np, random, operator, pandas as pd, matplotlib.pyplot as plt
from tool.geofunc import GeoFunc
from tool.show import PltFunc
from tool.data import getData
import tool.packing as packing
from tool.nfp import NFP
from shapely.geometry import Polygon,mapping
from shapely import affinity
import json
import csv
import time
import multiprocessing
import datetime
import random
import copy

class BottomLeftFill(object):
    def __init__(self,width,original_polygons, **kw):
        self.choose_nfp=False
        self.width=width
        self.height=8000
        self.contain_length=2000
        self.polygons=original_polygons
        self.NFPAssistant=None
        
        # 配置された図形の重心座標を格納するリスト
        self.nodes_centroid = []
        if 'NFPAssistant' in kw:
            self.NFPAssistant=kw["NFPAssistant"]
        if 'data_id' in kw:
            self.data_id=kw['data_id']
        # self.vertical=False
        # if 'vertical' in kw:
        #     self.vertical=kw['vertical']
        
        print("Total Num:", len(original_polygons))
        # ここで，最初の図形を左下に配置している
        self.placeFirstPoly()
        # 2番目以降の図形を順次配置していく
        for i in range(1,len(self.polygons)):
            print("############################## Place the ",i+1,"th shape #################################")
            # self.showAll()
            self.placePoly(i)
        
        self.getLength()
        self.startpoint = 0
        tours, total_distance, distance_list = self.nn_tsp(self.nodes_centroid, start_node = self.startpoint)
        self.showAll(total_distance=total_distance, distance_list = distance_list, tours=tours)

    def placeFirstPoly(self):
        poly=self.polygons[0]
        left_index,bottom_index,right_index,top_index=GeoFunc.checkBound(poly)
        GeoFunc.slidePoly(poly,-poly[left_index][0],-poly[bottom_index][1]) 
        self.nodes_centroid.append(GeoFunc.getCentroid(poly))

    def placePoly(self,index):

        adjoin=self.polygons[index]
   
        ifr=packing.PackingUtil.getInnerFitRectangle(self.polygons[index],self.width,self.height)
        # print(f'ifr: {ifr}')
        # exit()          
        differ_region=Polygon(ifr)
        
        for main_index in range(0,index):
            main=self.polygons[main_index]
            if self.NFPAssistant==None:
                nfp=NFP(main,adjoin).nfp
            else:
                # mainが固定，adjoinが移動した時の，nfpを取得
                nfp=self.NFPAssistant.getDirectNFP(main,adjoin)
            nfp_poly=Polygon(nfp)
            try:
                # dirre_regionを逐次更新IFRからnfpを除いた実際の配置可能領域
                differ_region=differ_region.difference(nfp_poly)
                # print(f'differ_region : {differ_region}')
                # exit()
            except:
                print('NFP failure, areas of polygons are:')
                self.showAll()
                for poly in main,adjoin:
                    print(Polygon(poly).area)
                self.showPolys([main]+[adjoin]+[nfp])
                print('NFP loaded from: ',self.NFPAssistant.history_path)

        # 差分で計算した複数の多角形の全ての頂点を統合した単一の座標配列
        print(f'differ {differ_region}')
        differ=GeoFunc.polyToArr(differ_region)
        # print(f'len(differ): {len(differ)}')
        # print(f'differ: {differ}')
        # exit()
        # differ点の中で，左下の点を取得
        differ_index=self.getBottomLeft(differ)
        # adjoin「配置対象図形」の中で，topの点を取得
        refer_pt_index=GeoFunc.checkTop(adjoin)
        # self.polygons[index]（配置対象）の値を更新
        GeoFunc.slideToPoint(self.polygons[index],adjoin[refer_pt_index],differ[differ_index])     
        
        self.nodes_centroid.append(GeoFunc.getCentroid(self.polygons[index]))


    def getBottomLeft(self,poly):
        bl=[] 
        _min=999999
        
        for i,pt in enumerate(poly):
            pt_object={
                    "index":i,
                    "x":pt[0],
                    "y":pt[1]
            }
            target = pt[1]

            if target < _min:
                _min = target
                bl = [pt_object]
            elif target == _min:
                bl.append(pt_object)

        if len(bl) == 1:
            return bl[0]["index"]
            
        else:
            target = "x"
            _min = bl[0][target]
            one_pt = bl[0]
            for pt_index in range(1, len(bl)):
                if bl[pt_index][target] < _min:
                    one_pt = bl[pt_index]
                    _min = one_pt["x"]
            return one_pt["index"]



    def showAll(self, total_distance=None, distance_list=None, tours=None):

        PltFunc.showGif(self.polygons, self.width, self.contain_length, self.data_id)
        exit()
        for i in range(0,len(self.polygons)):
            PltFunc.addPolygon(self.polygons[i])
        # if total_distance!=None:
        #     PltFunc.addWiring(tours, self.startpoint, distance_list)
        #     print(f'total wiring length: {total_distance}')
        print(f'width: {self.width}, contain_length: {self.contain_length}')
        
        length=max(self.width,self.contain_length)
        # PltFunc.addLine([[self.width,0],[self.width,self.contain_height]],color="blue")
        PltFunc.showPlt(width=self.width,height=self.contain_length, id = self.data_id, datasets_id=self.data_id)
        if total_distance!=None:
            PltFunc.addWiring(tours, self.startpoint, distance_list, self.data_id)
            print(f'total wiring length: {total_distance}')
        print(f'width: {self.width}, contain_length: {self.contain_length}')


    def showPolys(self,polys):
        for i in range(0,len(polys)-1):
            PltFunc.addPolygon(polys[i])
        PltFunc.addPolygonColor(polys[len(polys)-1])
        length=max(self.width,self.contain_length)
        PltFunc.showPlt(width=max(length,self.width),height=max(length,self.width),minus=200)    

    def getLength(self):
        _max=0
        for i in range(0,len(self.polygons)):
            extreme_index=GeoFunc.checkTop(self.polygons[i])
            extreme=self.polygons[i][extreme_index][1]
            if extreme>_max:
                _max=extreme
        self.contain_length=_max
        
        return _max
    

    def nn_tsp(self, cities, start_node):
        """ある都市から経路を始め、その都市から一番近い都市へと経路を進め、その次の都市からさらに次の、まだ訪れていない都市へと経路を進める。"""

        total_distance = 0
        distance_list = []
        print(f'cities: {cities}')
        # exit()
        start = cities[start_node]
        tour = [start]
        unvisited = cities.copy() 
        unvisited.remove(start)     

        while len(unvisited) > 0:
            
            distance, next_node = self.nearest_neighbor(tour[-1], unvisited)
            total_distance += distance
            distance_list.append(total_distance)
            tour.append(next_node)
            unvisited.remove(next_node)

        return tour, total_distance, distance_list

    def nearest_neighbor(self, A, cities):
        "citiesのうち、Aに一番近いものを見つける。"
        min = np.inf
        for i in range(len(cities)):
            if distance(A, cities[i]) < min:
                min = distance(A, cities[i])
                n_cities = cities[i]
        return min, n_cities

def distance(A, B):
    "AとBのユークリッド距離を計算"
    return ((A[0] - B[0]) ** 2 + (A[1] - B[1]) ** 2) ** 0.5 



    
if __name__=='__main__':
    # index from 0-15
    
    index=10
    polys=getData(index)
    nfp_ass=packing.NFPAssistant(polys,store_nfp=True,get_all_nfp=True,load_history=False)

    starttime = datetime.datetime.now()
    # bfl=BottomLeftFill(2000,polys,vertical=False)
    bfl=BottomLeftFill(1500,polys, NFPAssistant=nfp_ass, data_id=index)
    
    endtime = datetime.datetime.now()
    print ("total time: ",endtime - starttime)
    bfl.showAll()