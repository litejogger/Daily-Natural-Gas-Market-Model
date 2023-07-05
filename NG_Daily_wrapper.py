# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 22:14:07 2017

@author: YSu
"""

from pyomo.opt import SolverFactory
from NGMM_2 import model as m1
from pyomo.core import Var
from pyomo.core import Constraint
from pyomo.core import Param
from operator import itemgetter
import pandas as pd
import numpy as np
from datetime import datetime
import pyomo.environ as pyo
from pyomo.environ import value

import functools

max_days = 358
days = max_days #max_days 

instance = m1.create_instance('NGMM_data.dat')
instance.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

Solvername = 'cplex'
Timelimit = 3600 # for the simulation of one day in seconds
# Threadlimit = 8 # maximum number of threads to use

opt = SolverFactory(Solvername)
if Solvername == 'cplex':
    opt.options['timelimit'] = Timelimit
elif Solvername == 'gurobi':           
    opt.options['TimeLimit'] = Timelimit
    
# opt.options['threads'] = Threadlimit

H = instance.HorizonDays
D = 2
K=range(1,H+1)


#Space to store results
step1_prod =[]
step2_prod =[]
step3_prod =[]
step4_prod =[]
step5_prod =[]
step6_prod =[]
step1_flow =[]
step2_flow =[]
step3_flow =[]
step4_flow =[]
step5_flow =[]
slack = []
duals=[]

df_QP_NA = pd.read_csv('QP_BASE_NA.csv',header=0)
qps = list(df_QP_NA['producer'])
for q in qps:
    new_q = q + '_qps'
    i = qps.index(q)
    qps[i] = new_q
df_QP_NA['producer'] = qps

#max here can be (1,365)
for day in range(1,days+1):
    
    for z in instance.nodes:
    #load Demand and Reserve time series data
        for i in K:
            instance.HorizonDemand[z,i] = instance.SimDemand[z,day-1+i]

    result = opt.solve(instance,tee=True,symbolic_solver_labels=True, load_solutions=False) ##,tee=True to check number of variables\n",
    instance.solutions.load_from(result)  
                           

    for c in instance.component_objects(Constraint, active=True):
        cobject = getattr(instance, str(c))
        if str(c) in ['Node_Constraint']:
            for index in cobject:
                 if int(index[1]==1):
                     # try:
                         duals.append((index[0],index[1]+day-1, instance.dual[cobject[index]]))
                     # except KeyError:
                         # duals.append((index[0],index[1]+day-1,-999))

    for v in instance.component_objects(Var, active=True):
        varobject = getattr(instance, str(v))
        a=str(v)
                                        
        if a=='step1_prod':
            for index in varobject:
                
                producer = index[0]
                               
                if int(index[1]==1):
                    
                    step1_prod.append((index[0],index[1]+day-1,varobject[index].value))   

        if a=='step2_prod':
            for index in varobject:
                
                producer = index[0]
                               
                if int(index[1]==1):
                    
                    step2_prod.append((index[0],index[1]+day-1,varobject[index].value))   

        if a=='step3_prod':
            for index in varobject:
                
                producer = index[0]
                               
                if int(index[1]==1):
                    
                    step3_prod.append((index[0],index[1]+day-1,varobject[index].value))   

        if a=='step4_prod':
            for index in varobject:
                
                producer = index[0]
                               
                if int(index[1]==1):
                    
                    step4_prod.append((index[0],index[1]+day-1,varobject[index].value))   

        if a=='step5_prod':
            for index in varobject:
                
                producer = index[0]
                               
                if int(index[1]==1):
                    
                    step5_prod.append((index[0],index[1]+day-1,varobject[index].value))   

        if a=='step6_prod':
            for index in varobject:
                
                producer = index[0]
                               
                if int(index[1]==1):
                    
                    step6_prod.append((index[0],index[1]+day-1,varobject[index].value))   

        if a=='step1_flow':    
            for index in varobject:
                if int(index[1]==1):
                    step1_flow.append((index[0],index[1]+day-1,varobject[index].value))                                            

        if a=='step2_flow':    
            for index in varobject:
                if int(index[1]==1):
                    step2_flow.append((index[0],index[1]+day-1,varobject[index].value))                                            

        if a=='step3_flow':    
            for index in varobject:
                if int(index[1]==1):
                    step3_flow.append((index[0],index[1]+day-1,varobject[index].value))                                            

        if a=='step4_flow':    
            for index in varobject:
                if int(index[1]==1):
                    step4_flow.append((index[0],index[1]+day-1,varobject[index].value))                                            

        if a=='step5_flow':    
            for index in varobject:
                if int(index[1]==1):
                    step5_flow.append((index[0],index[1]+day-1,varobject[index].value))

        if a=='slack_flow':
            for index in varobject:
                if int(index[1]==1):
                    slack.append((index[0],index[1]+day-1,varobject[index].value))
        

    print(day)
        
step1_prod_pd=pd.DataFrame(step1_prod,columns=('Producer','Day','step1_prod'))
step2_prod_pd=pd.DataFrame(step2_prod,columns=('Producer','Day','step2_prod'))
step3_prod_pd=pd.DataFrame(step3_prod,columns=('Producer','Day','step3_prod'))
step4_prod_pd=pd.DataFrame(step4_prod,columns=('Producer','Day','step4_prod'))
step5_prod_pd=pd.DataFrame(step5_prod,columns=('Producer','Day','step5_prod'))
step6_prod_pd=pd.DataFrame(step6_prod,columns=('Producer','Day','step6_prod'))

step1_flow_pd = pd.DataFrame(step1_flow,columns=('Line','Day','step1_flow'))
step2_flow_pd = pd.DataFrame(step2_flow,columns=('Line','Day','step2_flow'))
step3_flow_pd = pd.DataFrame(step3_flow,columns=('Line','Day','step3_flow'))
step4_flow_pd = pd.DataFrame(step4_flow,columns=('Line','Day','step4_flow'))
step5_flow_pd = pd.DataFrame(step5_flow,columns=('Line','Day','step5_flow'))

slack_flow_pd = pd.DataFrame(slack,columns=('Line','Day','slack_flow'))
duals_pd = pd.DataFrame(duals,columns=['Node','Day','nodal_constraint_dual_val'])

#create dataframe of all outputs combined and save
prod_dfs = [step1_prod_pd,step2_prod_pd,step3_prod_pd,step4_prod_pd,step5_prod_pd,step6_prod_pd]
flow_dfs = [step1_flow_pd,step2_flow_pd,step3_flow_pd,step4_flow_pd,step5_flow_pd]
df_prod_combined = functools.reduce(lambda left,right: pd.merge(left,right,on=['Producer','Day']),prod_dfs)
df_flow_combined = functools.reduce(lambda left,right: pd.merge(left,right,on=['Line','Day']),flow_dfs)

df_prod_combined.to_csv('Outputs/combined_prod.csv', index=False)
df_flow_combined.to_csv('Outputs/combined_flow.csv', index=False)

#to save outputs
step1_prod_pd.to_csv('Outputs/step1_prod.csv', index=False)
step2_prod_pd.to_csv('Outputs/step2_prod.csv', index=False)
step3_prod_pd.to_csv('Outputs/step3_prod.csv', index=False)
step4_prod_pd.to_csv('Outputs/step4_prod.csv', index=False)
step5_prod_pd.to_csv('Outputs/step5_prod.csv', index=False)
step6_prod_pd.to_csv('Outputs/step6_prod.csv', index=False)

step1_flow_pd.to_csv('Outputs/step1_flow.csv', index=False)
step2_flow_pd.to_csv('Outputs/step2_flow.csv', index=False)
step3_flow_pd.to_csv('Outputs/step3_flow.csv', index=False)
step4_flow_pd.to_csv('Outputs/step4_flow.csv', index=False)
step5_flow_pd.to_csv('Outputs/step5_flow.csv', index=False)
slack_flow_pd.to_csv('Outputs/slack_flow.csv', index=False)
duals_pd.to_csv('Outputs/duals.csv', index=False)




