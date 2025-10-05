from tool.nfp import NFP
from tool.show import PltFunc
from shapely.geometry import Polygon,Point,mapping,LineString
from shapely.ops import unary_union
from shapely import affinity
from tool.geofunc import GeoFunc
import pyclipper 
import math
import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt
import csv
import logging
import random
import copy
import os

def getNFP(poly1,poly2): # 这个函数必须放在class外面否则多进程报错
    nfp=NFP(poly1,poly2).nfp
    return nfp

        
class Poly(object):
    '''
    用于后续的Poly对象
    '''
    def __init__(self,num,poly,allowed_rotation):
        self.num=num
        self.poly=poly
        self.cur_poly=poly
        self.allowed_rotation=[0,180]

class GeoFunc(object):

    def checkBottom(poly):
        polyP=Polygon(poly)
        min_y=polyP.bounds[1]
        for index,point in enumerate(poly):
            if point[1]==min_y:
                return index

    def checkTop(poly):
        polyP=Polygon(poly)
        max_y=polyP.bounds[3]
        for index,point in enumerate(poly):
            if point[1]==max_y:
                return index
    
    def checkLeft(poly):
        polyP=Polygon(poly)
        min_x=polyP.bounds[0]
        for index,point in enumerate(poly):
            if point[0]==min_x:
                return index
    
    def checkRight(poly):
        polyP=Polygon(poly)
        max_x=polyP.bounds[2]
        for index,point in enumerate(poly):
            if point[0]==max_x:
                return index

    def checkBound(poly):
        return GeoFunc.checkLeft(poly), GeoFunc.checkBottom(poly), GeoFunc.checkRight(poly), GeoFunc.checkTop(poly)


    def slideToPoint(poly,pt1,pt2):
        GeoFunc.slidePoly(poly,pt2[0]-pt1[0],pt2[1]-pt1[1])

    def getSlide(poly,x,y):
        new_vertex=[]
        for point in poly:
            new_point=[point[0]+x,point[1]+y]
            new_vertex.append(new_point)
        return new_vertex

    def slidePoly(poly,x,y):
        for point in poly:
            point[0]=point[0]+x
            point[1]=point[1]+y

    def polyToArr(inter):
        res=mapping(inter)
        _arr=[]
        if res["type"]=="MultiPolygon":
            for poly in res["coordinates"]:
                for point in poly[0]:
                    _arr.append([point[0],point[1]])
        elif res["type"]=="GeometryCollection":
            for item in res["geometries"]:
                if item["type"]=="Polygon":
                    for point in item["coordinates"][0]:
                        _arr.append([point[0],point[1]])
        else:
            if res["coordinates"][0][0]==res["coordinates"][0][-1]:
                for point in res["coordinates"][0][0:-1]:
                    _arr.append([point[0],point[1]])
            else:
                for point in res["coordinates"][0]:
                    _arr.append([point[0],point[1]])
        return _arr


    def getPt(point):
        mapping_result=mapping(point)
        return [mapping_result["coordinates"][0],mapping_result["coordinates"][1]]


class PackingUtil(object):
    
    @staticmethod
    def getInnerFitRectangle(poly,x,y):
        left_index,bottom_index,right_index,top_index=GeoFunc.checkBound(poly) # 获得边界
        new_poly=GeoFunc.getSlide(poly,-poly[left_index][0],-poly[bottom_index][1]) # 获得平移后的结果

        refer_pt=[new_poly[top_index][0],new_poly[top_index][1]]
        ifr_width=x-new_poly[right_index][0]
        ifr_height=y-new_poly[top_index][1]

        IFR=[refer_pt,[refer_pt[0]+ifr_width,refer_pt[1]],[refer_pt[0]+ifr_width,refer_pt[1]+ifr_height],[refer_pt[0],refer_pt[1]+ifr_height]]
        return IFR
    
class NFPAssistant(object):
    def __init__(self,polys,**kw):
        self.polys=PolyListProcessor.deleteRedundancy(copy.deepcopy(polys))
        self.area_list,self.first_vec_list,self.centroid_list=[],[],[] # 作为参考
        for poly in self.polys:
            P=Polygon(poly)
            self.centroid_list.append(GeoFunc.getPt(P.centroid))
            self.area_list.append(int(P.area))
            self.first_vec_list.append([poly[1][0]-poly[0][0],poly[1][1]-poly[0][1]])
        # NFPの座標を格納するリスト
        # nfp_list[i][j] = 多角形i（固定）に対する多角形j（移動）のNFP
        self.nfp_list=[[0]*len(self.polys) for i in range(len(self.polys))]
        self.load_history=False
        self.history_path=None
        self.history=None
        if 'history_path' in kw:
            self.history_path=kw['history_path']

        if 'load_history' in kw:
            if kw['load_history']==True:
                
                if 'history' in kw:
                    self.history=kw['history']
                self.load_history=True
                self.loadHistory()
        
        self.store_nfp=False
        if 'store_nfp' in kw:
            print(f'store_nfp')
            if kw['store_nfp']==True:
                self.store_nfp=True
        
        self.store_path=None
        if 'store_path' in kw:
            self.store_path=kw['store_path']

        if 'get_all_nfp' in kw:
            print(f'get_all_nfp')
            if kw['get_all_nfp']==True and self.load_history==False:
                self.getAllNFP()
        
        

    def loadHistory(self):
        if not self.history:
            if not self.history_path:
                path="record/nfp.csv"
            else:
                path=self.history_path
            df = pd.read_csv(path,header=None)
        else:
            df = self.history
        for index in range(df.shape[0]):
            i=self.getPolyIndex(json.loads(df[0][index]))
            j=self.getPolyIndex(json.loads(df[1][index]))
            if i>=0 and j>=0:
                self.nfp_list[i][j]=json.loads(df[2][index])
        # print(self.nfp_list)
        
    # targetの図形と同じものを探索
    def getPolyIndex(self,target):
        area=int(Polygon(target).area)
        first_vec=[target[1][0]-target[0][0],target[1][1]-target[0][1]]
        # 面積を基準にしてtargetの図形のindexを取得
        area_index=PolyListProcessor.getIndexMulti(area,self.area_list)
        if len(area_index)==1: 
            return area_index[0]
        else:
            # 最初のベクトルを基準にして絞り込み
            vec_index=PolyListProcessor.getIndexMulti(first_vec,self.first_vec_list)
            index=[x for x in area_index if x in vec_index]
            if len(index)==0:
                return -1
            return index[0]
    
    # Get all shapes NFP
    def getAllNFP(self):

        for i,poly1 in enumerate(self.polys):
            for j,poly2 in enumerate(self.polys):
                nfp=NFP(poly1,poly2).nfp
                # print(f'poly1_no{i+1}, poly2_{j+1} : {poly1}, {poly2}')
                # NFP(poly1,poly2).showResult()
                self.nfp_list[i][j]=GeoFunc.getSlide(nfp,-self.centroid_list[i][0],-self.centroid_list[i][1])
                    
        # print(f'nfp_list shape: {self.nfp_list.shape}')
        # exit()
        if self.store_nfp==True:
            self.storeNFP()
    
    def storeNFP(self):
        if self.store_path==None:
            path="record/nfp.csv"
        else:
            path=self.store_path
        with open(path,"a+") as csvfile:
            writer = csv.writer(csvfile)
            for i in range(len(self.polys)):
                for j in range(len(self.polys)):
                    writer.writerows([[self.polys[i],self.polys[j],self.nfp_list[i][j]]])

    # poly1が固定，poly2が移動した時のnfpを取得
    def getDirectNFP(self,poly1,poly2,**kw):
        # poly1が固定，poly2が移動
        if 'index' in kw:
            i=kw['index'][0]
            j=kw['index'][1]
            centroid=GeoFunc.getPt(Polygon(self.polys[i]).centroid)
        else:
            # poly1,poly2のindexを取得
            i=self.getPolyIndex(poly1)
            j=self.getPolyIndex(poly2)
            centroid=GeoFunc.getPt(Polygon(poly1).centroid)

        if self.nfp_list[i][j]==0:
            nfp=NFP(poly1,poly2).nfp
            #self.nfp_list[i][j]=GeoFunc.getSlide(nfp,-centroid[0],-centroid[1])
            if self.store_nfp==True:
                with open("record/nfp.csv","a+") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows([[poly1,poly2,nfp]])
            return nfp
        else:
            return GeoFunc.getSlide(self.nfp_list[i][j],centroid[0],centroid[1])

class PolyListProcessor(object):
    
    @staticmethod
    def getIndexMulti(item,_list):
        index_list=[]
        for i in range(len(_list)):
            if item==_list[i]:
                index_list.append(i)
        return index_list

    
    @staticmethod
    def deleteRedundancy(_arr):
        new_arr = []
        for item in _arr:
            if not item in new_arr:
                new_arr.append(item)
        return new_arr

 
