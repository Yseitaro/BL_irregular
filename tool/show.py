import matplotlib.pyplot as plt
import sys
import os

class PltFunc(object):

    def addPolygon(poly):
        for i in range(0,len(poly)):
            if i == len(poly)-1:
                PltFunc.addLine([poly[i],poly[0]])
            else:
                PltFunc.addLine([poly[i],poly[i+1]])

    def addWiring(wirings, startpoint, distance_list):

        for i in range(0,len(wirings)-1):
            plt.plot([wirings[i][0],wirings[i+1][0]],[wirings[i][1],wirings[i+1][1]],color="red",linewidth=1)
            if i == 0:
                plt.plot(wirings[i][0],wirings[i][1],'o',markersize=5,color="red")
            else:
                plt.plot(wirings[i][0],wirings[i][1],'o',markersize=5,color="black")
            plt.plot(wirings[i+1][0],wirings[i+1][1],'o',markersize=5,color="black")

            # plt.title(f'Start point at {startpoint+1} Wiring Length: {distance_list[i]:.2f}')
            # os.makedirs(f'results/Start_point{startpoint+1}', exist_ok=True)
            # plt.savefig(f'results/Start_point{startpoint+1}/dataset_6_opt_wire_{i}.png')
        plt.title(f'Start point at {startpoint+1} Wiring Length: {distance_list[i]:.2f}')
        os.makedirs(f'results/Start_point{startpoint+1}', exist_ok=True)
        plt.savefig(f'results/Start_point{startpoint+1}/dataset_opt_wire_{i}.png')

    def addPolygonColor(poly):
        for i in range(0,len(poly)):
            if i == len(poly)-1:
                PltFunc.addLine([poly[i],poly[0]],color="blue")
            else:
                PltFunc.addLine([poly[i],poly[i+1]],color="blue")

    def addLine(line,**kw):
        if len(kw)==0:
            plt.plot([line[0][0],line[1][0]],[line[0][1],line[1][1]],color="black",linewidth=0.5)
        else:
            plt.plot([line[0][0],line[1][0]],[line[0][1],line[1][1]],color=kw["color"],linewidth=0.5)            
    
    def showGif(polygons, **kw):
        for i in range(0, len(polygons)):
            PltFunc.addPolygon(polygons[i])
            PltFunc.showPlt(width=900,height=800, id=i)

    def showPlt(**kw):
        if len(kw)>0:
            if "minus" in kw:
                plt.axhline(y=0,c="blue")
                plt.axvline(x=0,c="blue")
                plt.axis([-kw["minus"],kw["width"],-kw["minus"],kw["height"]])
                
            else:
                plt.xlim(0, kw["width"])
                plt.ylim(0, kw["height"])
                # plt.axis([0,kw["width"],0,kw["height"]+1000])
        else:
            plt.axis([0,1000,0,1000])
            # plt.axis([-1000,2000,-979400.4498015114,20000])
            # plt.axis([-500,1000,0,1500])
        
        if "id" in kw:
            plt.savefig(f'results/dataset_{kw["id"]+1}.png')
        else:
            plt.savefig(f'results/dataset_opt_wire.png')
        # plt.show()
        # plt.clf()

    def showPolys(polys):
        for poly in polys:
            PltFunc.addPolygon(poly)
        PltFunc.showPlt(width=2000,height=2000)

    def saveFig(name):
        plt.savefig('figs\\'+name+'.png')
        plt.cla()
    
    