#Libraries
import numpy as np
import sys
import cv2 as cv
import numpy as np
from sklearn.cluster import KMeans
from datetime import datetime
from collections import Counter, defaultdict
import math

#Image management
import urllib.request
import glob

#OPC functions
#OPCUA
from opcua import Client, ua
import time
#OPCDA
import OpenOPC
import pywintypes
import threading
pywintypes.datetime =  pywintypes.TimeType

#Supress warnings
import warnings

#custom libraries
import CompVis_libs as cvlibs
import CompVis_masks as cvmasks


def fxn():
    warnings.warn("deprecated", DeprecationWarning)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    fxn()
warnings.filterwarnings("ignore")

#Main code:
def get_client():
    #Login to OPC Server
    while True:
        try:
            ##Connect to OPC DA Server
            OPC_HOST = 'UDIWELIPSEPRD02'
            OPC_CONNECTION_NAME = 'Elipse.OPCSvr.1'
            global client
            client = OpenOPC.client()
            client.connect(OPC_CONNECTION_NAME, OPC_HOST) 
            print('Successfully connected to OPC-DA Server')
            return client
            break
        except Exception as e:
            print(e)
            time.sleep(20)
            print('Error connecting to OPC-DA Server')   
     

def visao_comp():
    url = r'http://10.246.234.63//jpeg?id=1'
    median_vector = []
    fillment_vector = []
    median_points = 150
    save_txt = True

    unid = 'UDI'
    proc = 'DES'
    line = 'L1'
    code_full = unid + '_' + proc + '_' + line

    client = get_client()
    flow_correction_flag = 0
    standarized_flow_flag = 0
    if(flow_correction_flag ==1):
        print('Flow correction ON')
    else:
        print('Flow correction OFF')
    if(standarized_flow_flag==1):
        standard_fillment = cvlibs.standarized_flow('standard_flow.jpg', code_full) #standard for line 1

    #watchdog_counter = 0
    #watchdog_limit = 999999

    while True:

        flag_on = True
        try:
            #flag_on = PTU_DP1_STATUS.get_value()
            flag_on = client.read("DriverSecador3e4.LINK_CLP_SUP.LINK_DATA_SUP2.tag001.M10_330.Bit09")[0]
            #flag_on=True
            print('FLAG ON:',flag_on)
        except Exception as e:
            print(e)
            time.sleep(5)
            print('Error getting transporter status - assuming ON')
            try:
               ##Connect to OPC DA Server
               OPC_HOST = 'UDIWELIPSEPRD02'
               OPC_CONNECTION_NAME = 'Elipse.OPCSvr.1'
               client = OpenOPC.client()
               client.connect(OPC_CONNECTION_NAME, OPC_HOST)
               print('Successfully connected to OPC-DA Server')
            except:
               print('Error connecting to OPC-DA Server')

        if flag_on == True:
            dest = r'D:\Runtimes\fotos\\' + unid + '_' + proc + '_' + line + '_' + str(int(time.time())) + '.jpg'
            picture = cvlibs.url_to_image(url)
            
            #cv.imshow('test',picture)
            #time.sleep(300)
            estimated_loss,fillment =  cvmasks.fc_perda_branca_nc(picture, code_full,'runtime')
            if(estimated_loss != 0):
                if(standarized_flow_flag==0):
                    fillment_vector.append(fillment)
                    flow_rate = round(((fillment/np.median(fillment_vector))*100),2)
                else:
                    flow_rate = round(((fillment/standard_fillment)*100),2)
                if(flow_correction_flag==0):
                    estimated_loss = cvlibs.correction_factor(estimated_loss)
                    median_vector.append(estimated_loss)
                else:
                    estimated_loss = (flow_rate*(cvlibs.correction_factor(estimated_loss)))/100
                    median_vector.append(estimated_loss)
                save_flag = np.random.binomial(1,0.0005)
                if(save_flag ==1):
                    cv.imwrite(dest,picture)
                    print('Image randomly saved for further evaluation')

            else:
                flow_rate = 0
                
            if(np.shape(median_vector)[0]>median_points):
                median_vector = median_vector [1:]
                fillment_vector = fillment_vector [1:]
            median = round(np.median(median_vector),2)
            
            #if(watchdog_counter<=watchdog_limit):
            #    watchdog_counter +=1
            #else:
            #    watchdog_counter = 0
                
            print('-----------------------------')
            print(unid,'-', proc,'-',line)
            now = datetime.now()
            current_time = now.strftime("%D - %H:%M:%S")
            print("Current Time: ", current_time)
            print('Estimated Loss: ',round(estimated_loss,2), '%')
            #print('Median_vector: ',median_vector)
            print('Median of last ',median_points,' non-zero points: ',median)
            print('Flow: ',flow_rate, '%')
            print('Fillment: ', round(fillment,2)*100,'%')
            #print('Counter: ',watchdog_counter)
            
            #try:
                #cvlibs.save_opc(estimated_loss,median,flow_rate,fillment,watchdog_counter,OPC_type)
                #cvlibs.save_opc(estimated_loss,median,flow_rate,fillment,OPC_type)
            #except:
                #print('Not saved on OPC server')

            try:    
                client.write(("DriverSecador3e4.CTRL_LINHA_4_TAGNA.VCInstantFill",100*fillment))
                client.write(("DriverSecador3e4.CTRL_LINHA_4_TAGNA.VCInstantLoss",estimated_loss))
                #Save OPC-UA
                #PTU_DP1_VC_PERDA1.set_value(estimated_loss)
                #PTU_DP1_VC_FILL1.set_value(fillment)
                #PTU_DP1_VC_WD.set_value(watchdog_counter)
            
                if(math.isnan(median)==True):
                    median=0
                        
                #PTU_DP1_VC_PERDA2.get_attribute(ua.AttributeIds.Value)
                #PTU_DP1_VC_PERDA2.set_attribute(ua.AttributeIds.Value,ua.DataValue(median))
                #PTU_DP1_VC_PERDA2.set_value(median)
                #skp_SP.get_value()
                print('Successfully saved on OPC-DA')
            except:
                print('OPC Connection Lost - Trying to Reconect')
                try:
                    ##Connect to OPC DA Server
                    OPC_HOST = 'UDIWELIPSEPRD02'
                    OPC_CONNECTION_NAME = 'Elipse.OPCSvr.1'
                    client = OpenOPC.client()
                    client.connect(OPC_CONNECTION_NAME, OPC_HOST)
        
                    print('Successfully connected to OPC-DA Server')
                except:
                    print('Error connecting to OPC-DA Server')  
                
            if(save_txt == True):
                memo_data = int(time.time()),current_time,estimated_loss,median,flow_rate,fillment
                f = open(unid + '_' + proc + '_' + line + '_' +'memo_out2.txt', 'a')
                f.write(str(memo_data)+'\n')
                f.close()
            time.sleep(2)
        #break
        else:
            print('Transporter status OFF')
            time.sleep(2)
            
def watchdog_func():
    watchdog_counter = 0
    watchdog_limit = 9999
    client = get_client()
    while True:
        if(watchdog_counter<=watchdog_limit):
                watchdog_counter +=1
        else:
                watchdog_counter = 0
        try:
                #Save OPC-UA
                #PTU_DP1_VC_WD.set_value(watchdog_counter)
                #Save OPC-DA
                client.write(("DriverSecador3e4.CTRL_LINHA_4_TAGNA.VCWatchdog",watchdog_counter))
                #print('WD Counter:',watchdog_counter)
        except Exception as e:
                print(e)
                print('OPC Connection Lost - Trying to Reconect')
                try:
                    ##Connect to OPC DA Server
                    OPC_HOST = 'UDIWELIPSEPRD02'
                    OPC_CONNECTION_NAME = 'Elipse.OPCSvr.1'
                    client = OpenOPC.client()
                    client.connect(OPC_CONNECTION_NAME, OPC_HOST)
                    
                    print('Successfully connected to OPC-DA Server')
                except:
                    print('Error connecting to OPC-DA Server')
        time.sleep(1)


#import logging
import threading
import time


x = threading.Thread(target=visao_comp)
y = threading.Thread(target=watchdog_func)

x.start()
y.start()

#
x.join()
y.join()

print('End')
