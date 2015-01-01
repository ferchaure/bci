from pyqtgraph.Qt import QtCore #interfaz en general
import pyqtgraph as pg #graphicos
import pyqtgraph.functions as fn
from PyQt4  import QtGui, uic
from scipy import fftpack
import numpy as np
from configuration import GENERAL_CONFIG as CONFIG
from threading import Thread
from copy import copy
from multiprocess_config import *

from collections import namedtuple
from configuration import SPIKE_CONFIG
from configuration import LIBGRAPH_CONFIG as LG_CONFIG
from configuration import FILE_CONFIG
from os import path, system
#import logging

#logging.basicConfig(format='%(levelname)s:%(message)s',filename='bci.log',level=logging.WARNING)


spike_duration_samples = int(SPIKE_CONFIG['SPIKE_DURATION'] / 1000.0*CONFIG['FS'])
CH_COLORS = ['r', 'y', 'g', 'c', 'p', 'm']
NOT_SAVING_MESSAGE = 'without saving'
SAVING_MESSAGE = 'writing in:'
FFT_SIZE = CONFIG['FS'] / LG_CONFIG['FFT_RESOLUTION']
fft_frec = np.linspace(0, CONFIG['FS'] / 2, FFT_SIZE/2)
one_pack_time = CONFIG['PAQ_USB'] / CONFIG['FS']
PACK_xSPIKE_COUNT = int(float(LG_CONFIG['TIME_SPIKE_COUNT']) / one_pack_time)
FREQFIX_xSPIKE_COUNT = (float(PACK_xSPIKE_COUNT)*one_pack_time)
beep_command = "beep -f " + LG_CONFIG['BEEP_FREQ'] + " -l " \
                + str(SPIKE_CONFIG['SPIKE_DURATION']) + " -d "

UIFILE = path.join(path.abspath(path.dirname(__file__)), 'bciui.ui')

SHOW_ERROR_TIME = 5000 #ms

if LG_CONFIG['TWO_WINDOWS']:
    second_win_file = path.join(path.abspath(
                              path.dirname(__file__)),'second_window.ui')


UserOptions_t=namedtuple('UserOptions_t','filter_mode thr_values thr_manual_mode')

if CONFIG['PROBES_CONFIG'] == 'Tetrode':
    ELEC_GROUP = 4
    PROBE_CONF_L = 'TeT'
    GROUP_LABEL  = 'Tetrode'
    
elif CONFIG['PROBES_CONFIG'] == 'Stereotrode':
    ELEC_GROUP = 2
    PROBE_CONF_L = 'SteT' 
    GROUP_LABEL  = 'Stereotrode'
    
else:
    ELEC_GROUP = 1
    PROBE_CONF_L = ''
    GROUP_LABEL  = 'Electrode'
    
class MainWindow(QtGui.QMainWindow):
    channel_changed  = QtCore.pyqtSignal(int) 
    def __init__(self, processing_process, get_data_process):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi(UIFILE, self)
        #self.tabifyDockWidget(self.firing_rates_dock,self.clustering_dock);
        self.clustering_dock.setVisible(False)
        self.processing_process = processing_process
        self.get_data_process = get_data_process
        self.data_handler = bci_data_handler()
        self.signal_config = Channels_Configuration(queue = self.processing_process.ui_config_queue)#HARDCODE
        self.signal_config.try_send()
        
        self.channel_changed.connect(self.change_channel)
        
        self.group_info = plus_display(self.data_handler,self.plus_grid,
                                         self.plus_grid_fr, self.signal_config,
                                         self.thr_p,self.channel_changed)
        self.general_display = GeneralDisplay(self.data_handler,self.espacio_pg, self.group_info)
        
        
        
        QtCore.QObject.connect(self.tet_plus_mode, QtCore.SIGNAL("currentIndexChanged(int)"), 
                               self.group_info.change_display_mode) 
        QtCore.QObject.connect(self.display_scale, QtCore.SIGNAL("valueChanged(int)"),
                               self.general_display.changeYrange)  
        QtCore.QObject.connect(self.filter_mode_button, QtCore.SIGNAL("clicked( bool)"), 
                               self.change_filter_mode)  
        QtCore.QObject.connect(self.paq_view, QtCore.SIGNAL("valueChanged(int)"), 
                               self.changeXrange)                        
        QtCore.QObject.connect(self.active_channel_cb, QtCore.SIGNAL("clicked( bool)"),
                               self.activate_channel)
        QtCore.QObject.connect(self.manual_thr_cb, QtCore.SIGNAL("clicked( bool)"),
                               self.group_info.change_th_mode)
                               
        QtCore.QObject.connect(self.thr_p, QtCore.SIGNAL("textEdited(const QString&)"),
                               self.group_info.thr_changed)
                               
        QtCore.QObject.connect(self.pausa, QtCore.SIGNAL("clicked (bool)"),
                               self.group_info.set_pause)
        
#        QtCore.QObject.connect(self.group_info, QtCore.SIGNAL("channel_changed (bool)"),
#                               self.test)
        
        self.thr_p.setValidator(QtGui.QDoubleValidator())
        self.contador_registro = -1
        self.timer = QtCore.QTimer()
        self.loss_data = 0
        self.timer.timeout.connect(self.update)
        
        self.timer.start(0) #si va demasiado lento deberia bajarse el tiempo
        get_data_process.process.start()
        processing_process.process.start()
        
        self.file_label = QtGui.QLabel("")
        self.statusBar.addPermanentWidget(self.file_label)
        #self.dockWidget.setTitleBarWidget(QtGui.QWidget())
        self.file_label.setText(NOT_SAVING_MESSAGE)
        self.change_filter_mode(self.filter_mode_button.isChecked())
    
    def keyPressEvent(self, e):
    
        if e.key() == QtCore.Qt.Key_A and not e.isAutoRepeat():
            autoRange_state = self.group_info.VB.getState().get('autoRange')
            if autoRange_state.count(True) > 0:
                self.group_info.VB.disableAutoRange()
            else:
                self.group_info.VB.enableAutoRange()
        elif e.key() == QtCore.Qt.Key_P and not e.isAutoRepeat():
            self.pausa.click()
        
    def change_channel(self,channel):
        self.manual_thr_cb.setChecked(self.signal_config.th_manual_modes[channel])
        self.active_channel_cb.setChecked(self.signal_config.active_channels[channel])
        if PROBE_CONF_L:
            self.info_label.setText('{}:{} | C:{}'.format(PROBE_CONF_L,int(channel/ELEC_GROUP)+1,channel%ELEC_GROUP+1))
        else:
            self.info_label.setText('Electrode : {}'.format(channel))
        
    def about(self):
        QtGui.QMessageBox.about(self, "About",
        """Essentially, all expressions of human nature ever produced, from a caveman's paintings to Mozart's symphonies and Einstein's view of the universe, emerge from the same source: the relentless dynamic toil of large populations of interconnected neurons.
        Miguel Nicolelis""")  
     
     
    def change_filter_mode(self, mode):
        """"Define si se pide la segnial pura o la filtrada"""
        self.signal_config.change_filter_mode(mode)
        self.group_info.show_line = mode
        self.group_info.threshold_visible(mode)     

    def update(self):
        """"Loop que se ejecuta si llegan nuevos paquetes"""
        
        try:
            new_struct = self.processing_process.new_data_queue.get(TIMEOUT_GET)
        except Queue_Empty:
            return 1
        if new_struct['type'] == 'monitor': 
            self.data_handler.update(new_struct)
            
            if self.beepbox.isChecked():
                t = Thread(target = beep,
                                     args = [self.data_handler.spikes_times[self.group_info.channel]])
                t.start()
                
            if (not self.get_data_process.warnings.empty()):
                new_mess = self.get_data_process.warnings.get(TIMEOUT_GET)       
                if new_mess[0] != SLOW_PROCESS_SIGNAL:
                    self.loss_data += new_mess[1]
                    self.statusBar.showMessage("Loss data: " + str(self.loss_data),SHOW_ERROR_TIME)
    
                else:
                    self.statusBar.showMessage(Errors_Messages[new_mess[0]],SHOW_ERROR_TIME)
            
            if (not self.processing_process.warnings.empty()):
                self.statusBar.showMessage(Errors_Messages[self.processing_process.warnings.get(TIMEOUT_GET)],SHOW_ERROR_TIME)
    
    
    
            self.general_display.update()
            self.group_info.update()
            
            self.signal_config.try_send()
        
    
    def on_actionDetener(self):
        """detiene el guardado de datos"""
        self.get_data_process.control.send(STOP_SIGNAL)
        self.file_label.setText(NOT_SAVING_MESSAGE)

    def on_actionSalir(self):
        """Pide verificacion, detiene procesos y termina de guardar archivos"""
        if(QtGui.QMessageBox.question(
                        QtGui.QWidget(), 'Exit',
                        "Are you sure you want to exit the application?", 
                        QtGui.QMessageBox.Yes |QtGui.QMessageBox.No, 
                        QtGui.QMessageBox.No) == QtGui.QMessageBox.No):                   
            return
        self.timer.stop()
        self.get_data_process.control.send(EXIT_SIGNAL)
        self.processing_process.control.send(EXIT_SIGNAL)
        self.get_data_process.process.join(2)
        self.processing_process.process.join(1)
        self.processing_process.process.terminate()
        self.get_data_process.process.terminate()
        self.general_display.close()
        #self.close()
        QtCore.QCoreApplication.instance().quit()
        #exit()        
        import sys
        sys.exit()

    def on_actionNuevo(self):
        """Nuevo archivo de registro"""
        self.get_data_process.control.send(START_SIGNAL)
        self.contador_registro += 1
        self.file_label.setText(SAVING_MESSAGE + FILE_CONFIG['GENERIC_FILE'] +'-'+str(self.contador_registro))

    #def set_autoRange(self):
        #if self.autoRange.isChecked():
            #self.general_display.setAutoRange(True)
        #else:
            #self.general_display.setAutoRange(False)
        
    def closeEvent(self, event):
        u"""Redirige las senales que disparen ese evento al metodo on_actionSalir()"""
        self.on_actionSalir()
        
    def changeXrange(self, i):
        """Modifica la cantidad de paquetes que se dibujan en los displays"""
        self.data_handler.change_paq_view(i)
        self.general_display.changeXrange(i)
    
    def activate_channel(self, i):
        """Agrega el canal seleccionado a la lista de canales activos"""
        self.signal_config.active_channels[self.group_info.channel] = i

       
    def on_actionInit_SP(self):
        """Comienza el proceso de spike sorting en los canales activos"""
        self.active_channel_cb.setCheckable(False)
        self.processing_process.control.send(self.active_channels)
        #implementacion pendiente
    #@QtCore.pyqtSlot()          
#    def view_firing_rate_dock(self,view):
#        self.firing_rates_dock.setVisible(view)  
                
class  plus_display():
    """Clase que engloba el display inferior junto a los metodos que lo implican individualmente"""  
    def __init__(self,data_handler, espacio_pg, plus_grid_fr, signal_config, thr_p_label,channel_changed): 
        self.channel_changed = channel_changed
        
        self.data_handler = data_handler
        self.mode = 0 
        self.channel = 0
        self.signal_config = signal_config
        self.tasas_bars = bar_graph()
        self.thr_p_label = thr_p_label
        #layout_graphicos.addItem(self.tasas_bars,row=None, col=0, rowspan=1, colspan=1)
        #graph=layout_graphicos.addPlot(row=None, col=1, rowspan=1, colspan=3)
        self.graph = pg.PlotItem()
        axis = self.graph.getAxis('left')
        axis.setScale(scale = CONFIG['ADC_SCALE'])
        self.std = np.ndarray(CONFIG['#CHANNELS'])
        self.VB = self.graph.getViewBox()
        self.VB.setXRange(0, CONFIG['PAQ_USB']/float(CONFIG['FS']), padding=0, update=True)
        self.VB.setYRange(LG_CONFIG['DISPLAY_LIMY'], -LG_CONFIG['DISPLAY_LIMY'], padding=0, update=True)
        self.graph.setMenuEnabled(enableMenu = False, enableViewBoxMenu = None)
        self.graph.setDownsampling(auto = True)
        self.curve = self.graph.plot()
        #QtCore.QObject.connect(self.graph_umbral, QtCore.SIGNAL("sigPositionChange()"), 
        self.graph.enableAutoRange('y', False)                       #self.pepe)
        
        espacio_pg.setCentralItem(self.graph)
        plus_grid_fr.setCentralItem(self.tasas_bars)
        
        self.graph_umbral = pg.InfiniteLine(pen = pg.mkPen('w', width=2), angle = 0, movable = True)
        self.graph_umbral.sigPositionChangeFinished.connect(self.thr_changed)

        
        self.fft_n = 0
        #self.data_fft = 0
        self.fft_l = 0
        self.fft_aux = np.zeros([LG_CONFIG['FFT_N'], FFT_SIZE / 2])
        self.data_fft_aux = np.zeros([CONFIG['PAQ_USB']*LG_CONFIG['FFT_L_PAQ']])
        
        self.threshold_visible(True)
        self.graph_umbral.setValue(self.signal_config.thresholds[self.channel])
        self.show_line = False
        self.pause_mode = False
        self.change_channel(self.channel)


        self.graph_umbral.sigDragged.connect(self.moving_line)                     
        self.graph_umbral.sigPositionChangeFinished.connect(self.free_line)           
            
        self.graph_thr_updatable = True          
    
    def moving_line(self):
        self.graph_thr_updatable = False
    
    def free_line(self):
        self.graph_thr_updatable = True
        
    def thr_changed(self,p = None):
        if self.signal_config.th_manual_modes[self.channel]:
            
            self.signal_config.change_th(self.channel, self.graph_umbral.value())
            
            self.thr_p_label.setText("{0:.1f}".format(self.graph_umbral.value()/self.std[self.channel]))
        else:
            
            if type(p)== pg.InfiniteLine:
                p = self.graph_umbral.value() / self.std[self.channel]
                self.signal_config.change_th(self.channel, p)
                self.thr_p_label.setText("{0:.1f}".format(p))
            else:
                self.signal_config.change_th(self.channel, float(p))
                self.graph_umbral.setValue(float(p)*self.std[self.channel])


    def set_pause(self,pause_mode):
        if pause_mode == True:
            self.data_old = copy(self.data_handler.graph_data)
        self.pause_mode = pause_mode

                
        
    def update(self):
        """Lo ejecutan al llegar nuevos paquetes"""

        if self.pause_mode == True:
            data = self.data_old
        else:
            data = self.data_handler.graph_data
        
        n_view = self.data_handler.n_view
        xtime = self.data_handler.xtime
        
        self.max_xtime = xtime[n_view-1]
        tet = int(self.channel / ELEC_GROUP)
        
        self.tasas_bars.update(self.data_handler.spikes_times[tet*ELEC_GROUP:tet*ELEC_GROUP+ELEC_GROUP])
        self.std = self.data_handler.std
        
        if self.signal_config.th_manual_modes[self.channel]:
            self.thr_p_label.setText("{0:.1f}".format(self.graph_umbral.value()/self.std[self.channel]))

        if (not self.signal_config.th_manual_modes[self.channel]) and self.graph_thr_updatable:
            self.graph_umbral.setValue(self.signal_config.thresholds[self.channel]*
            self.std[self.channel])



        if self.mode is 0:
            self.curve.setPen(CH_COLORS[self.channel%ELEC_GROUP])
            self.curve.setData(x = xtime[:n_view], y = data[self.channel, :n_view])
      
        else:
            if( self.fft_l < LG_CONFIG['FFT_L_PAQ']):
                self.data_fft_aux[self.fft_l*CONFIG['PAQ_USB']:(1+self.fft_l)*CONFIG['PAQ_USB']] = self.data_handler.data_new[self.channel, :]
                self.fft_l += 1
            else:
                self.fft_l = 0
                if (self.fft_n <LG_CONFIG['FFT_N']):
                    self.fft_aux[self.fft_n, :] = (abs(fftpack.fft(self.data_fft_aux,
                            n = FFT_SIZE)[:FFT_SIZE / 2])
                                ** 2. / float(FFT_SIZE))
                    self.fft_n += 1
                else:
                    self.fft_n = 0
                    self.curve.setPen(CH_COLORS[self.channel%ELEC_GROUP])
                    self.curve.setData(x = fft_frec, y = np.mean(self.fft_aux, 0))
                    
    def threshold_visible(self, visible):
        """Define si el umbral es visible o no"""
        if visible:
            self.graph.addItem(self.graph_umbral)
        else:
            self.graph.removeItem(self.graph_umbral)
            
            
    def change_display_mode(self, new_mode):
        """Define el modo del display. new_mode=0: raw data; new_mode=1: FFT"""
        if new_mode is None:
            new_mode = self.mode
        
        if new_mode is 0:
            self.thr_p_label.setEnabled(True)
            self.VB.setXRange(0, self.max_xtime, padding = 0, update = False)
            #self.graph.setLogMode(x=False,y=False)
            if self.show_line:
                self.threshold_visible(True)
                
            if self.signal_config.th_manual_modes[self.channel]:
                self.graph_umbral.setValue(self.signal_config.thresholds[self.channel])
                self.thr_p_label.setText("{0:.1f}".format(self.graph_umbral.value()/self.std[self.channel]))
            elif self.graph_thr_updatable:
                self.graph_umbral.setValue(self.signal_config.thresholds[self.channel]*self.std[self.channel])    
                self.thr_p_label.setText("{0:.1f}".format(self.signal_config.thresholds[self.channel]))

        #elif new_mode is 1:
            #self.graph.addItem(self.graph_umbral)
            #self.VB.setXRange(0, self.max_xtime, padding=0, update=False)
            ##self.VB.setXRange(0, self_max_xtime, padding=0, update=False)
            #self.graph.setLogMode(x=False,y=False)
            
            #self.graph_umbral.setMovable(True)

        else: 
            #self.graph.setLogMode(x=True,y=True)
            self.thr_p_label.setEnabled(False)
            self.VB.setXRange(0, CONFIG['FS']/2, padding=0, update=False)
            if(self.mode is 0 and self.show_line):
                self.threshold_visible(False)
            self.fft_l = 0
            self.fft_n = 0    
            
        self.mode = new_mode
        
    def change_th_mode(self, manual):
         
        self.signal_config.change_th_mode(self.channel, manual)
        
        if manual:
            self.signal_config.change_th(self.channel, self.signal_config.thresholds[self.channel]*self.std[self.channel])
        else:
            self.signal_config.change_th(self.channel, self.signal_config.thresholds[self.channel] / self.std[self.channel])
        
            
        
    def change_channel(self, canal):
        """Modifica el canal que se grafica actualmente, 
        refrescando las barras de firing rate si pertenece a otro tetrodo"""
        if int(self.channel/ELEC_GROUP) != int(canal/ELEC_GROUP):
            self.tasas_bars.tet_changed()
        self.channel = canal
   
        if self.signal_config.th_manual_modes[self.channel]:
            self.graph_umbral.setValue(self.signal_config.thresholds[self.channel])
            self.thr_p_label.setText("{0:.1f}".format(self.graph_umbral.value()/self.std[self.channel]))
        else:
            self.graph_umbral.setValue(self.signal_config.thresholds[self.channel]*
            self.std[self.channel])
            self.thr_p_label.setText("{0:.1f}".format(self.signal_config.thresholds[self.channel]))
            
        self.fft_l = 0
        self.fft_n = 0
        self.channel_changed.emit(canal)

class  bar_graph(pg.PlotItem):
    """Barras con tasas de disparo"""
    def __init__(self):
        self.npack = 0
        self.tasa_bars = list()
        self.tasas = np.zeros([PACK_xSPIKE_COUNT, ELEC_GROUP])
        pg.PlotItem.__init__(self)
        self.showAxis('bottom', False)
        self.setMenuEnabled(enableMenu = False, enableViewBoxMenu = None)
        #self.showAxis('left', False)
        #self.enableAutoRange('y', False)
        self.setXRange(-0.4, 3 + 0.4)
        self.enableAutoRange('x', False)
        #self.setYRange(0, 500)
        self.setMouseEnabled(x=False, y=True)
        #self.hideButtons()
        self.tasa_bars.append(self.plot(pen = CH_COLORS[0],
                                        fillLevel=0,brush = pg.mkBrush(CH_COLORS[0])))
        self.tasa_bars.append(self.plot(pen = CH_COLORS[1],
                                        fillLevel=0,brush = pg.mkBrush(CH_COLORS[1])))
        self.tasa_bars.append(self.plot(pen = CH_COLORS[2],
                                        fillLevel=0,brush = pg.mkBrush(CH_COLORS[2])))
        self.tasa_bars.append(self.plot(pen = CH_COLORS[3],
                                        fillLevel=0,brush = pg.mkBrush(CH_COLORS[3])))

    def update(self, spike_times):  
        for i in xrange(len(spike_times)):
            self.tasas[self.npack, i] = (np.greater(spike_times[i][1:] - spike_times[i][:-1],
                                                    spike_duration_samples)).sum() + ((spike_times[i]).size > 0)
            tasas_aux = self.tasas[:, i].sum() / FREQFIX_xSPIKE_COUNT  
            self.tasa_bars[i].setData(x = [i%ELEC_GROUP-0.3, i%ELEC_GROUP+0.3], 
                                   y = [tasas_aux,tasas_aux], _callSync='off')
            
        self.npack += 1
        if self.npack is PACK_xSPIKE_COUNT:
            self.npack = 0 

    def tet_changed(self):
        self.npack = 0
        self.tasas = np.zeros([PACK_xSPIKE_COUNT, ELEC_GROUP])
        
class GeneralDisplay():
    def __init__(self, data_handler, espacio_pg, info_tet):
        self.data_handler = data_handler
        layout_graphicos = pg.GraphicsLayout(border = (100, 0, 100)) 
        #para ordenar los graphicos(items) asi como el simil con los widgets
        espacio_pg.setCentralItem(layout_graphicos)

        self.set_canales = list() #canales seleccionados para ser mostrados
        self.curv_canal = list() #curvas para dsp actualizar los datos
        self.graphicos = list() #graphicos, para dsp poder modificar su autorange
        #graphicos principales
        
        
        if LG_CONFIG['TWO_WINDOWS'] is False:
            main_win_ch = CONFIG['#CHANNELS']
    
        else:
            main_win_ch = int(CONFIG['#CHANNELS']*3/ELEC_GROUP/7)*ELEC_GROUP
            self.second_win = Second_Display_Window()            
            layout_graphicos_2 = self.second_win.layout_graphicos
            self.second_win.show()
            
        for i in xrange(CONFIG['#CHANNELS']):
            vb = ViewBox_General_Display(i, info_tet)
            
            if (i < main_win_ch):
                graph = layout_graphicos.addPlot(viewBox = vb, 
                                                 row = int(i/ELEC_GROUP/LG_CONFIG['ROWS_DISPLAY'])*ELEC_GROUP + i%ELEC_GROUP, 
                                                    col = int(i/ELEC_GROUP)%LG_CONFIG['ROWS_DISPLAY'], 
                                                rowspan = 1, colspan = 1)
            else:
                graph = layout_graphicos_2.addPlot(viewBox=vb, 
                                                   row = int((i-main_win_ch) / ELEC_GROUP / LG_CONFIG['ROWS_DISPLAY'])*ELEC_GROUP+(i-main_win_ch)%ELEC_GROUP, 
                                                   col = int((i - main_win_ch) / ELEC_GROUP)%LG_CONFIG['ROWS_DISPLAY'],
                                                    rowspan = 1, colspan = 1)
            
            graph.hideButtons()
            graph.setDownsampling(auto = True)
            VB = graph.getViewBox()
            
            VB.setXRange(0, CONFIG['PAQ_USB'], padding = 0, update = True) #HARDCODE
            VB.setYRange(LG_CONFIG['DISPLAY_LIMY'], -LG_CONFIG['DISPLAY_LIMY'],
                         padding = 0, update = True)

            if i % ELEC_GROUP is 0:
                graph.setTitle("<font size=\"3\">{} {}</font>".format(GROUP_LABEL,str(i / ELEC_GROUP + 1)))
            
            #if i%4 != 3:text
                #graph.showAxis('bottom', show=False)
            graph.showAxis('bottom', show = False) 
            graph.showAxis('top', show = False)
            graph.showAxis('right', show = False)
            graph.showAxis('left', show = False)
            graph.showGrid(y = True)
            graph.setMenuEnabled(enableMenu = False, enableViewBoxMenu = False)
            graph.setMouseEnabled(x = False, y = True)
            self.curv_canal.append(graph.plot())
            self.curv_canal[-1].setPen(width = 1, color = CH_COLORS[i%ELEC_GROUP])
            self.graphicos.append(graph)

        
        
    def changeYrange(self, p):
        p = float(p) / 10
        for i in xrange(CONFIG['#CHANNELS']):
            self.graphicos[i].setYRange(LG_CONFIG['DISPLAY_LIMY'] * p, -1*LG_CONFIG['DISPLAY_LIMY']*p, padding=0, update=False)
    
    
    def changeXrange(self, i):
        max_x = i*CONFIG['PAQ_USB']
        for i in xrange(CONFIG['#CHANNELS']):
            self.graphicos[i].setXRange(0, max_x, padding = 0, update = False)
            
        
    def update(self):
        for i in xrange(CONFIG['#CHANNELS']):
            self.curv_canal[i].setData(y = self.data_handler.graph_data[i, :self.data_handler.n_view])
            
    def close(self):
        if LG_CONFIG['TWO_WINDOWS'] is True:
            self.second_win.Close()
            
class ViewBox_General_Display(pg.ViewBox):
    def __init__(self, i, info_tet):
        pg.ViewBox.__init__(self)
        self.i = i
        self.info_tet = info_tet
    
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton:
            self.info_tet.change_channel(self.i)
    
    def mouseDragEvent(self, ev, axis = None):
        """If axis is specified, event will only affect that axis."""
        ev.accept()  ## we accept all buttons
        
        pos = ev.pos()
        lastPos = ev.lastPos()
        dif = pos - lastPos
        dif = dif * -1

        ## Ignore axes if mouse is disabled
        mouseEnabled = np.array(self.state['mouseEnabled'], dtype=np.float)
        mask = mouseEnabled.copy()
        if axis is not None:
            mask[1-axis] = 0.0

        ## Scale or translate based on mouse button
        if ev.button() & QtCore.Qt.RightButton:
            #print "vb.rightDrag"
            if self.state['aspectLocked'] is not False:
                mask[0] = 0
            
            dif = ev.screenPos() - ev.lastScreenPos()
            dif = np.array([dif.x(), dif.y()])
            dif[0] *= -1
            s = ((mask * 0.02) + 1) ** dif
            
            tr = self.childGroup.transform()
            tr = fn.invertQTransform(tr)
            
            x = s[0] if mouseEnabled[0] == 1 else None
            y = s[1] if mouseEnabled[1] == 1 else None
            
            self.scaleBy(x = x, y = y, center=(0, 0))
            self.sigRangeChangedManually.emit(self.state['mouseEnabled'])
    

class Second_Display_Window(QtGui.QDialog):
    ##Ventana extra
    def __init__(self):
        QtGui.QDialog.__init__(self)
        uic.loadUi(second_win_file, self)
        self.setWindowFlags(QtCore.Qt.Window)
        self.layout_graphicos = pg.GraphicsLayout(border=(100, 0, 100)) 
        #para ordenar los graphicos(items) asi como el simil con los widgets
        self.graphicsView.setCentralItem(self.layout_graphicos)
        self.closeable = False
    
    def Close(self):
        self.closeable = True
        self.close()
        
    def closeEvent(self, evnt):
        if self.closeable is False:
            evnt.ignore()


class  bci_data_handler():
    """Controla el alineado de datos, actualizaciones y configuracion 
    de entrada, agregando una capa de abstraccion al resto de los metodos"""

    def __init__(self):

        self.data_new = np.int16(np.zeros([CONFIG['#CHANNELS'], CONFIG['PAQ_USB']]))
        self.spikes_times = 0 
        self.graph_data = np.int16(np.zeros([CONFIG['#CHANNELS'],
                                             LG_CONFIG['MAX_PAQ_DISPLAY'] * CONFIG['PAQ_USB']]))
        self.paqdisplay = 0
        self.paq_view = 1
        self.new_paq_view = 1
        self.n_view = self.paq_view*CONFIG['PAQ_USB']
        self.xtime = np.zeros([LG_CONFIG['MAX_PAQ_DISPLAY']*CONFIG['PAQ_USB']])
        self.xtime[:self.n_view] = np.linspace(0, self.n_view / float(CONFIG['FS']), self.n_view)
        self.std = np.ndarray(CONFIG['#CHANNELS'])
    
    
    def update(self, data_struct):
              
        if data_struct["filter_mode"] is False:
            #mean = data_struct["new_data"].mean(axis=1)
            self.data_new = data_struct["new_data"] #- mean[:, np.newaxis]
        else:
            self.data_new = data_struct["new_data"]
            
        self.spikes_times = data_struct["spikes_times"]
        
        self.std = data_struct["std"]
        
        if(self.new_paq_view != self.paq_view):
            self.paq_view = self.new_paq_view
            self.n_view = self.paq_view*CONFIG['PAQ_USB']
            self.xtime[:self.n_view] = np.linspace(0, self.n_view / float(CONFIG['FS']), 
                                                    self.n_view)
        
        if self.paqdisplay >= self.paq_view:
            self.paqdisplay = 0
        self.graph_data[:, self.paqdisplay*CONFIG['PAQ_USB']:(self.paqdisplay+1)*CONFIG['PAQ_USB']] = self.data_new
        self.paqdisplay += 1
        
    def change_paq_view(self, i):
        self.new_paq_view =  i
        
        
        
def beep(sk_time):
    if not np.size(sk_time):
        return
    sp = (np.greater(sk_time[1:] - sk_time[:-1], spike_duration_samples)).sum() + 1
    string = beep_command + str(
        int((one_pack_time * 1000.0 - SPIKE_CONFIG['SPIKE_DURATION'] * sp) / sp))
    for _ in xrange(sp):
        system(string)
    return
    

class Channels_Configuration():
    def __init__(self, queue, filter_mode = None):
        
        #all thresholds = -4*std()
        self.th_manual_modes = np.zeros(CONFIG['#CHANNELS'],dtype=bool)
        self.thresholds = -4 * np.ones(CONFIG['#CHANNELS'])
        self.active_channels = [False] *CONFIG['#CHANNELS']
        self.filter_mode = filter_mode
        self.queue = queue
        self.changed = True
        
    def change_th(self, ch, value):
        
        if(self.thresholds[ch] != value):
            self.thresholds[ch] = value
            
            self.changed = True

    def change_th_mode(self, ch, value):
        
        self.th_manual_modes[ch] = value
        self.changed = True

            
            
    def change_filter_mode(self, state):
        self.filter_mode = state
        self.changed = True
        
    def try_send(self):
        if self.changed == True:
            try:
                self.queue.put(UserOptions_t(filter_mode=self.filter_mode, 
                                             thr_values =self.thresholds,
                                             thr_manual_mode = self.th_manual_modes))
            except Queue_Full:
                pass
            self.changed = False
