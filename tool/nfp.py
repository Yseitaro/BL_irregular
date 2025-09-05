from tool.show import PltFunc
from tool.geofunc import GeoFunc
from tool.data import getData
from shapely.geometry import Polygon,Point,mapping,LineString
from shapely.ops import unary_union
import pandas as pd
import json
import copy

class NFP(object):
    def __init__(self,poly1,poly2,**kw):
        self.stationary=copy.deepcopy(poly1)
        self.sliding=copy.deepcopy(poly2)
        # print(f'poly1 : {poly1}')
        # print(f'poly2 : {poly2}')
        start_point_index=GeoFunc.checkBottom(self.stationary)
        self.start_point=[poly1[start_point_index][0],poly1[start_point_index][1]]
        self.locus_index=GeoFunc.checkTop(self.sliding)
        # listを追加しないとoriginal_topはポインタになる
        self.original_top=list(self.sliding[self.locus_index])
        # self.sliding: 移動させていく多角形の座標 self.locus_index: 移動させる多角形の最高点座標（x, y)， self.start_point: 固定多角形の最下点座標 (x,y)
        GeoFunc.slideToPoint(self.sliding,self.sliding[self.locus_index],self.start_point)
        self.start=True 
        self.nfp=[]
        self.rectangle=False
        if 'rectangle' in kw:
            if kw["rectangle"]==True:
                self.rectangle=True
        self.error=1
        self.main()
        if 'show' in kw:
            if kw["show"]==True:
                self.showResult()
        
        # 計算完了後に元の位置に平行移動
        GeoFunc.slideToPoint(self.sliding,self.sliding[self.locus_index],self.original_top)

    def main(self):
        i=0
        if self.rectangle: # 最適化対象が長方形の場合
            width=self.sliding[1][0]-self.sliding[0][0]
            height=self.sliding[3][1]-self.sliding[0][1]
            self.nfp.append([self.stationary[0][0],self.stationary[0][1]])
            self.nfp.append([self.stationary[1][0]+width,self.stationary[1][1]])
            self.nfp.append([self.stationary[2][0]+width,self.stationary[2][1]+height])
            self.nfp.append([self.stationary[3][0],self.stationary[3][1]+height])
        else:
            while self.judgeEnd()==False and i<75: # 75以上で自動終了、一般的には計算エラー
            # while i<7:
                # print("########第",i,"轮##########")
                touching_edges=self.detectTouching()
                all_vectors=self.potentialVector(touching_edges)                
                # print(f'all_vectors : {all_vectors}')
                # exit()
                if len(all_vectors)==0:
                    print("実行可能なベクトルがありません")
                    self.error=-2 # 実行可能なベクトルがありません
                    break

                vector=self.feasibleVector(all_vectors,touching_edges)
                if vector==[]:
                    print("実行可能なベクトルが計算できません")
                    self.error=-5 # 実行可能なベクトルが計算できません
                    break
                
                self.trimVector(vector)
                if vector==[0,0]:
                    print("移動が実行されませんでした")
                    self.error=-3 # 移動が実行されませんでした
                    break

                GeoFunc.slidePoly(self.sliding,vector[0],vector[1])
                self.nfp.append([self.sliding[self.locus_index][0],self.sliding[self.locus_index][1]])
                # print(f'self.nfp : {self.nfp}')
                
                i=i+1
                inter=Polygon(self.sliding).intersection(Polygon(self.stationary))
                if GeoFunc.computeInterArea(inter)>1:
                    print("交差領域が発生しました")
                    self.error=-4 # 交差領域が発生しました
                    break     
                      

        if i==75:
            print("計算回数を超過しました")
            self.error=-1 # 計算回数を超過しました
    
    # 相互の接続状況を検出
    def detectTouching(self):
        touch_edges=[]
        stationary_edges,sliding_edges=self.getAllEdges()
        for edge1 in stationary_edges:
            for edge2 in sliding_edges:
                # print(f'edge1 {edge1}, edge2 {edge2}')
                # exit()
                # edge1とedge2の交点を計算
                inter=GeoFunc.intersection(edge1,edge2)
                if inter!=[]:
                    pt=[inter[0],inter[1]] # 交点
                    edge1_bound=(GeoFunc.almostEqual(edge1[0],pt) or GeoFunc.almostEqual(edge1[1],pt)) # 境界かどうか
                    edge2_bound=(GeoFunc.almostEqual(edge2[0],pt) or GeoFunc.almostEqual(edge2[1],pt)) # 境界かどうか
                    stationary_start=GeoFunc.almostEqual(edge1[0],pt) # 開始点かどうか
                    orbiting_start=GeoFunc.almostEqual(edge2[0],pt) # 開始点かどうか
                    touch_edges.append({
                        "edge1":edge1,
                        "edge2":edge2,
                        "vector1":self.edgeToVector(edge1),
                        "vector2":self.edgeToVector(edge2),
                        "edge1_bound":edge1_bound,
                        "edge2_bound":edge2_bound,
                        "stationary_start":stationary_start,
                        "orbiting_start":orbiting_start,
                        "pt":[inter[0],inter[1]],
                        "type":0
                    })
        return touch_edges 

    # 潜在的な移動可能ベクトルを取得
    def potentialVector(self,touching_edges):
        all_vectors=[]
        # print(len(touching_edges))
        for touching in touching_edges:
            # print("touching:",touching)
            # exit()
            aim_edge=[]
            # ケース1 両方の辺で交点が端点にある = 頂点同士が接触
            if touching["edge1_bound"]==True and touching["edge2_bound"]==True:
                # 2つの辺の位置関係（左側/右側/平行）を判定（edge1を基準として、edge2の位置を判定）
                right,left,parallel=GeoFunc.judgePosition(touching["edge1"],touching["edge2"])
                # print("right,left,parallel:",right,left,parallel)
                if touching["stationary_start"]==True and touching["orbiting_start"]==True:
                    touching["type"]=0
                    if left==True:
                        aim_edge=[touching["edge2"][1],touching["edge2"][0]] # 逆方向
                    if right==True:
                        aim_edge=touching["edge1"]
                if touching["stationary_start"]==True and touching["orbiting_start"]==False:
                    touching["type"]=1
                    if left==True:
                        aim_edge=touching["edge1"]
                if touching["stationary_start"]==False and touching["orbiting_start"]==True:
                    touching["type"]=2
                    if right==True:
                        aim_edge=[touching["edge2"][1],touching["edge2"][0]] # 逆方向
                if touching["stationary_start"]==False and touching["orbiting_start"]==False:
                    touching["type"]=3
    
            # ケース2
            if touching["edge1_bound"]==False and touching["edge2_bound"]==True:
                aim_edge=[touching["pt"],touching["edge1"][1]]
                touching["type"]=4
            
            # ケース3
            if touching["edge1_bound"]==True and touching["edge2_bound"]==False:
                aim_edge=[touching["edge2"][1],touching["pt"]]
                touching["type"]=5

            if aim_edge!=[]:
                vector=self.edgeToVector(aim_edge)
                if self.detectExisting(all_vectors,vector)==False: # 重複ベクトルを削除して計算複雑度を低下
                    all_vectors.append(vector)
        return all_vectors
    
    def detectExisting(self,vectors,judge_vector):
        for vector in vectors:
            if GeoFunc.almostEqual(vector,judge_vector):
                return True
        return False
    
    def edgeToVector(self,edge):
        return [edge[1][0]-edge[0][0],edge[1][1]-edge[0][1]]
    
    # 候補となる移動ベクトルの中から実際に移動可能なものを選択する処理
    def feasibleVector(self,all_vectors,touching_edges):
        '''
        このコード部分は複雑すぎるためリファクタリングが必要
        '''
        res_vector=[]
        # print("\nall_vectors:",all_vectors)
        for vector in all_vectors:
            feasible=True
            # print("\nvector:",vector,"\n")
            for touching in touching_edges:
                vector1=[]
                vector2=[]
                # 方向を判定して転回
                if touching["stationary_start"]==True:
                    vector1=touching["vector1"]
                else:
                    vector1=[-touching["vector1"][0],-touching["vector1"][1]]
                if touching["orbiting_start"]==True:
                    vector2=touching["vector2"]
                else:
                    vector2=[-touching["vector2"][0],-touching["vector2"][1]]
                vector12_product=GeoFunc.crossProduct(vector1,vector2) # 外積、0より大きいと左側、0より小さいと右側、0で平行
                vector_vector1_product=GeoFunc.crossProduct(vector1,vector) # 外積、0より大きいと左側、0より小さいと右側、0で平行
                vector_vector2_product=GeoFunc.crossProduct(vector2,vector) # 外積、0より大きいと左側、0より小さいと右側、0で平行
                # 最後の2つのケース
                if touching["type"]==4 and (vector_vector1_product*vector12_product)<0:
                    feasible=False
                if touching["type"]==5 and (vector_vector2_product*(-vector12_product))>0:
                    feasible=False
                # 通常ケースの処理
                if vector12_product>0:
                    if vector_vector1_product<0 and vector_vector2_product<0:
                        feasible=False
                if vector12_product<0:
                    if vector_vector1_product>0 and vector_vector2_product>0:
                        feasible=False
                # 平行ケース、元の値を使って逐一判定が必要
                if vector12_product==0:
                    inter=GeoFunc.newLineInter(touching["edge1"],touching["edge2"])
                    if inter["geom_type"]=="LineString":
                        if inter["length"]>0.01:
                            # 交点がある場合、左側にある必要がある
                            if (touching["orbiting_start"]==True and vector_vector2_product<0) or (touching["orbiting_start"]==False and vector_vector2_product>0):
                                feasible=False
                    else:
                        # 方向が同じで変換直線も平行の場合、aの方向を取ることができない
                        if touching["orbiting_start"]==True != touching["stationary_start"]==False and vector_vector1_product==0:
                            if touching["vector1"][0]*vector[0]>0: # つまり方向が同じ
                                feasible=False
            if feasible==True:
                res_vector=vector
                break
        return res_vector
        
    # 長すぎるベクトルを削減
    def trimVector(self,vector):
        stationary_edges,sliding_edges=self.getAllEdges()
        new_vectors=[]
        for pt in self.sliding:
            for edge in stationary_edges:
                line_vector=LineString([pt,[pt[0]+vector[0],pt[1]+vector[1]]])
                end_pt=[pt[0]+vector[0],pt[1]+vector[1]]
                line_polygon=LineString(edge)
                inter=line_vector.intersection(line_polygon)
                if inter.geom_type=="Point":
                    inter_mapping=mapping(inter)
                    inter_coor=inter_mapping["coordinates"]
                    if (abs(end_pt[0]-inter_coor[0])>0.01 or abs(end_pt[1]-inter_coor[1])>0.01) and (abs(pt[0]-inter_coor[0])>0.01 or abs(pt[1]-inter_coor[1])>0.01):
                        new_vectors.append([inter_coor[0]-pt[0],inter_coor[1]-pt[1]])

        for pt in self.stationary:
            for edge in sliding_edges:
                line_vector=LineString([pt,[pt[0]-vector[0],pt[1]-vector[1]]])
                end_pt=[pt[0]-vector[0],pt[1]-vector[1]]
                line_polygon=LineString(edge)
                inter=line_vector.intersection(line_polygon)
                if inter.geom_type=="Point":
                    inter_mapping=mapping(inter)
                    inter_coor=inter_mapping["coordinates"]
                    if (abs(end_pt[0]-inter_coor[0])>0.01 or abs(end_pt[1]-inter_coor[1])>0.01) and (abs(pt[0]-inter_coor[0])>0.01 or abs(pt[1]-inter_coor[1])>0.01):
                        new_vectors.append([pt[0]-inter_coor[0],pt[1]-inter_coor[1]])
        
        # print(new_vectors)
        for vec in new_vectors:
            if abs(vec[0])<abs(vector[0]) or abs(vec[1])<abs(vector[1]):
                # print(vec)
                vector[0]=vec[0]
                vector[1]=vec[1]
    
    # 2つの多角形の全ての辺を取得
    def getAllEdges(self):
        return GeoFunc.getPolyEdges(self.stationary),GeoFunc.getPolyEdges(self.sliding)
    
    # 終了かどうかを判定
    def judgeEnd(self):
        sliding_locus=self.sliding[self.locus_index]
        main_bt=self.start_point
        if abs(sliding_locus[0]-main_bt[0])<0.1 and abs(sliding_locus[1]-main_bt[1])<0.1:
            if self.start==True:
                self.start=False
                # print("終了判定：いいえ")
                return False
            else:
                # print("終了判定：はい")
                return True
        else:
            # print("終了判定：いいえ")
            return False

    # 最終結果を表示
    def showResult(self):
        PltFunc.addPolygon(self.sliding)
        PltFunc.addPolygon(self.stationary)
        PltFunc.addPolygonColor(self.nfp)
        PltFunc.showPlt()

    # 侵入深度を計算
    def getDepth(self):
        '''
        poly2のcheckTopからNFPまでの距離を計算
        Source: https://stackoverflow.com/questions/36972537/distance-from-point-to-polygon-when-inside
        '''
        d1=Polygon(self.nfp).distance(Point(self.original_top))
        # 点が多角形の内部にある場合、d1=0
        # d2: 点から最も近い境界までの距離
        if d1==0:
            d2=Polygon(self.nfp).boundary.distance(Point(self.original_top))
            # print('d2:',d2)
            return d2
        else: 
            return 0