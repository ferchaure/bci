#!/usr/bin/python

from multiprocessing import Process, Pipe
from pyqtgraph.Qt import QtGui, QtCore #interfaz en general
import pyqtgraph as pg #graficos

import numpy as np #vectores, operaciones matematicas
import time #hora local 
from scipy import signal #proc de segnales
from PyQt4  import uic #leer archivo con user interface
import os #ayuda a lo anterior y renombra archivo para largo

from capture import capture_init
from libgraf import bar_graf,Dialog_Tet,mymenu

CANT_CANALES=32
FS=20000

PAQ_USB=10000
TIEMPO_DISPLAY=PAQ_USB/FS*1000 #minimo en ms.. 
CANT_DISPLAY= PAQ_USB #minimo 



#hardcodeos... u optimizaciones...
subm=25
xtime=np.arange(0,float(CANT_DISPLAY)/float(FS),subm/float(FS))
fft_frec= np.linspace(0, FS/2, CANT_DISPLAY/2/subm)
xtime_dialog=np.linspace(0,float(CANT_DISPLAY)/float(FS),CANT_DISPLAY)
fft_frec_dialog= np.linspace(0, FS/2, CANT_DISPLAY/2)

#Filtros: (revisar orden del filtro, tardan demasiado)

[b_spike,a_spike]=signal.iirfilter(4,[float(300*2)/FS, float(6000*2)/FS], rp=None, rs=None, btype='band', analog=False, ftype='butter',output='ba')
pasa_bajos=signal.firwin(61, 0.01)
pasa_altos=signal.firwin(61, 0.01, pass_zero=False)


#habria q activar aca el usb... si hay error q salte lo antes posible



# archivos de conf grafica... basica sin pg
uifile = os.path.join(
    os.path.abspath(
        os.path.dirname(__file__)),'bciui.ui')

        
class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi(uifile, self)
        self.layout_graficos = pg.GraphicsLayout() #para ordenar los graficos(items) asi como el simil con los widgets
        self.espacio_pg.setCentralItem(self.layout_graficos)
        
        self.set_canales=list()
        self.s_modes=list()
        #graficos principales    
        self.curv_canal=list()
        self.graficos=list()
        for i in range((CANT_CANALES)/4):
            graf = self.layout_graficos.addPlot(row=None, col=None, rowspan=1, colspan=1)
            graf.setTitle('Tetrodo ' + str(i+1))
            graf.ctrlMenu = mymenu()
            
            self.set_canales.append(graf.ctrlMenu.opciones.cb_c1)
            self.set_canales.append(graf.ctrlMenu.opciones.cb_c2)
            self.set_canales.append(graf.ctrlMenu.opciones.cb_c3)
            self.set_canales.append(graf.ctrlMenu.opciones.cb_c4)
            
            self.s_modes.append(graf.ctrlMenu.opciones.s_filtro)
            
            self.curv_canal.append(graf.plot(pen='r'))  
            self.curv_canal.append(graf.plot(pen='y'))  
            self.curv_canal.append(graf.plot(pen='g'))  
            self.curv_canal.append(graf.plot(pen='c'))
            self.graficos.append(graf)
            if not (i+1)%4:
                self.layout_graficos.nextRow()
                
                
        #creo y defino el diagolo q da mas info del canal
        self.dialogo=Dialog_Tet()
        
        self.layout_ecualizer= pg.GraphicsLayout() #para ordenar los graficos(items) asi como el simil con los widgets
        self.ecualizer_grid.setCentralItem(self.layout_ecualizer)
        self.tasa_bars=list()
        for i in range((CANT_CANALES)/4):
            graf=bar_graf(i,self.tasa_bars,self.dialogo)
            self.layout_ecualizer.addItem(graf,row=None, col=None, rowspan=1, colspan=1)
                

        
        #inicializo vector de muestras en cero
        self.data=np.int16(np.zeros([CANT_CANALES,CANT_DISPLAY]))        
        
        #quedo sin conectar xq no ser estandar de la interfaz
        QtCore.QObject.connect(self.autoRange, QtCore.SIGNAL("clicked()"), self.set_autoRange)
        
        
        #preparo proceso de adquisicion de datos
        #try:
        self.p_ob_datos,self.control_sampler,self.datos_in=capture_init()
        
        #except:
            #print(" ERROR EN INICIO USB")
            #self.on_actionSalir()
        
        self.p_ob_datos.start()
            
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(TIEMPO_DISPLAY) #esto deberia cambiarse con un boton, ojo q afecta largo de vectores

    def update(self):
        if(self.datos_in.poll()):
            t1 = time.time()

            if not self.pausa.isChecked():
                data_new=self.datos_in.recv() 
                self.data=np.concatenate((self.data[:,CANT_DISPLAY:], data_new),axis=1) 
                calcular_tasas_spikes(self.data,self.tasa_bars)           
            self.update_graficos()
            
            self.status.setText('update: '+str(int((time.time() - t1)*1000)))
          
    def update_graficos(self):    

        if self.dialogo.isVisible():
            tet=self.dialogo.tet_selec
            canal=range(tet*4,tet*4+4)
            for i in range(len(self.dialogo.set_canal)):
                if not self.dialogo.set_canal[i].isChecked():
                    self.dialogo.curv_canal[i].clear()
                elif self.dialogo.normal.isChecked():
                    self.dialogo.curv_canal[i].setData(x=xtime_dialog,y=self.data[canal[i],:])
                elif self.dialogo.pasaaltos.isChecked():
                    self.dialogo.curv_canal[i].setData(x=xtime_dialog,y=signal.lfilter(pasa_bajos, 1,self.data[canal[i],:]))
                elif self.dialogo.pasabajos.isChecked():
                    self.dialogo.curv_canal[i].setData(x=xtime_dialog,y=signal.lfilter(pasa_altos, 1,self.data[canal[i],:]))
                else:
                    aux=np.fft.fft(self.data[canal[i],:]) #/CANT_DISPLAY
                    self.dialogo.curv_canal[i].setData(x=fft_frec_dialog,y=abs(aux[:np.size(aux)/2]))


        canales_mostrados_sf = list()
        canales_pasa_bajos = list()
        canales_pasa_altos = list()
        canales_fft = list()
        
        for i in range(CANT_CANALES):
            if self.set_canales[i].isChecked() == 0:
                self.curv_canal[i].clear()
            elif self.s_modes[i/4].currentIndex() ==0:
                canales_mostrados_sf.append(i)
            elif self.s_modes[i/4].currentIndex() ==1:
                canales_pasa_bajos.append(i)
            elif self.s_modes[i/4].currentIndex() ==2:
                canales_pasa_altos.append(i)
            else:
                canales_fft.append(i)

        for i in canales_mostrados_sf:
            self.curv_canal[i].setData(x=xtime,y=self.data[i,::subm], _callSync='off')
        
        if len(canales_pasa_bajos) !=0:
            aux=signal.lfilter(pasa_bajos, 1,self.data[canales_pasa_bajos,:]) 
            for i in range(len(canales_pasa_bajos)):
                self.curv_canal[canales_pasa_bajos[i]].setData(x=xtime,y=aux[i,::subm], _callSync='off')
        
        if len(canales_pasa_altos) !=0:
            aux=signal.lfilter(pasa_altos, 1,self.data[canales_pasa_altos,:]) 
            for i in range(len(canales_pasa_altos)):
                self.curv_canal[canales_pasa_altos[i]].setData(x=xtime,y=aux[i,::subm], _callSync='off')    
        
        if len(canales_fft) !=0:
            aux=np.fft.fft(self.data[canales_fft,:]) #/CANT_DISPLAY
            aux = abs(aux[:,:np.size(aux,1)/2:subm])
            for i in range(len(canales_fft)):
                self.curv_canal[canales_fft[i]].setData(x=fft_frec,y=aux[i,:], _callSync='off')  
        


    
    def on_actionDetener(self):
        #detiene el guardado de datos
        self.control_sampler.send('detener')
    
    def on_actionNuevo(self):
        #Comienza el guardado de datos, abre el archivo etc
        self.control_sampler.send('nuevo')
       

    def on_actionSalir(self):
        self.control_sampler.send('salir')
        self.p_ob_datos.join(1)
        self.dialogo.close()
        self.close()
    
    def set_autoRange(self):
        if self.autoRange.isChecked():
            for grafico in self.graficos:
                grafico.enableAutoRange('xy', True)
        else:
            for grafico in self.graficos:
                grafico.enableAutoRange('xy', False)  
        
        
    #@QtCore.pyqtSlot()          
    #def on_s_canal1_valueChanged(self,int):
        #print str(self.s_canal1.value())



def calcular_tasas_spikes(data,tasa_bars):
        
    umbrales=4*np.median(abs(signal.lfilter(b_spike,a_spike,data))/0.6745,1)
    for i in range(len(tasa_bars)):
        valor=np.random.random()*100
        tasa_bars[i].setData(x=[i-0.3,i+0.3],y=[valor,valor], _callSync='off')


        
def main():
    app = QtGui.QApplication([])
    
    window=MainWindow()
    window.show()
    app.exec_()

if __name__ == '__main__':
    main()
