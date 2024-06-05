# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 13:35:03 2024

@author: calisy


"""
#%%

from pyomo.opt import SolverFactory
from pyomo.core import Var
from pyomo.core import Constraint
from pyomo.core import Param
from operator import itemgetter
import pyomo.environ as pyo
from pyomo.environ import value

# from pyomo.contrib.mis import compute_infeasibility_explanation


import pandas as pd
import numpy as np
from datetime import datetime

import sys
import time
import os
import functools

from pyomo.util.infeasible import log_infeasible_constraints
import logging

os.chdir(r'C:\Users\calisy\OneDrive\Energy Research\NG Project\code\Gas Model\Gas Model 6 - Weekly Storage Sets Price')

from Daily_Gas_Mod_6 import model as m1



max_days = 358 # original simulation period, must be total days of demand - 7 since it solves over 7 day horizon
max_days = 365 # current simulation period, additional 2018 days adds 7 back to the original total
days = 30 #simulation days (up to max days)
# days = 1 #for troubleshooting, only run model 1 time

instance = m1.create_instance('daily_gas_mod_data_6_base.dat')
instance.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

# print instance to a file for troubleshooting

# with open('foo.txt', 'w') as output_file:
#     instance.pprint(output_file)

Solvername = 'gurobi'
Timelimit = 3600 # for the simulation of one day in seconds
# Threadlimit = 8 # maximum number of threads to use

opt = pyo.SolverFactory(Solvername)

if Solvername == 'cplex':
    opt.options['timelimit'] = Timelimit
elif Solvername == 'gurobi':           
    opt.options['TimeLimit'] = Timelimit
    
# opt.options['threads'] = Threadlimit

H = instance.HorizonDays
D = 2
K=range(1,H+1) # actual horizon range used to define horizon params

# number of q and tariff steps comes from data setup file
num_qsteps = 20
num_ftariff_steps = 5


## result variable storage arrays
solve_times = []
step_prod = []
step_flow = []
pipeline_slack = []
total_pipeline_flow = []
pipeline_slack = []
production_slack = []
storage_slack = []
storage_withdrawal = []
storage_injection = []
state_node_balance_duals=[]

input_data_filepath = r'C:\Users\calisy\OneDrive\Energy Research\NG Project\code\Gas Model\Model Data Inputs'

# get imports for daily imports (not needed since we include all imports and exports in the model)
# df_net_storage = pd.read_csv(input_data_filepath + '/' + 'Daily Net Storage 2019.csv')
df_daily_imports = pd.read_csv(input_data_filepath + '/' + 'imports - daily pipeline and LNG smoothed - 2015-2019.csv').reset_index()
df_daily_exports = pd.read_csv(input_data_filepath + '/' + 'exports - daily pipeline and LNG smoothed - 2015-2019.csv').reset_index()

# get list of QPS producers
df_QP_NA = pd.read_csv(input_data_filepath + '/' + 'QP_BASE_NA.csv',header=0)
qps = list(df_QP_NA['producer'])
for q in qps:
    new_q = q + '_qps'
    i = qps.index(q)
    qps[i] = new_q
df_QP_NA['producer'] = qps

# review new qps list
df_QP_NA['producer'].head()

#%%

# set new days if degbugging (currently set on just 1 for now)
days = 1

for day in range(1,days+1):
    
    # section defining horizon paramters
    for z in instance.nodes:
    #load Demand and Reserve time series data
        for i in K: # horizon days range
            instance.HorizonDemand[z,i] = instance.SimDemand[z,day-1+i]  # horizon demand depends on the starting day in the simulation
            instance.Horizon_production[z,i] = instance.Sim_production[z,day-1+i]

            if z in df_daily_imports.columns:
                instance.Horizon_imports[z,i] = instance.Sim_imports[z,day-1+i]
            else:
                instance.Horizon_imports[z,i] = 0
            if z in df_daily_exports.columns:
                instance.Horizon_exports[z,i] = instance.Sim_exports[z,day-1+i]
            else:
                instance.Horizon_exports[z,i] = 0
    
    # start with storage cost = 0 to find other bugs first
    for z in instance.nodes:
        for i in K:
            instance.Horizon_storage_cost[z,day-1+i] = 0


                
## solve model instance
    
    start = time.time() #time the model
    
    # solve model
    result = opt.solve(instance,tee=True,symbolic_solver_labels=True, load_solutions=True) ##,tee=True to check number of variables\n",
    print(result)
    # log infeasibility if applicable
    # log_infeasible_constraints(instance, log_expression=True, log_variables=True)
    # logging.basicConfig(filename='gas_model_instance.log', encoding='utf-8', level=logging.INFO)
    
    # print(value(instance.z))
    
    # compute_infeasibility_explanation(m1, solver=Solvername)
    
    # record solve time
    end = time.time()
    elapsed = end-start
    solve_times.append((day,elapsed))
    
    # print()
    # print('solve time: '+str(elapsed) + ' seconds')
    
    
## Store solution information
    instance.solutions.load_from(result)
                         
    # store duals
    for c in instance.component_objects(Constraint, active=True):
        cobject = getattr(instance, str(c))
        if str(c) in ['Node_Constraint']:
            for index in cobject:
                 if int(index[1]==1):
                     # try:
                         state_node_balance_duals.append((index[0],index[1]+day-1, instance.dual[cobject[index]]))
                     # except KeyError:
                         # duals.append((index[0],index[1]+day-1,-999))
                         
                        
    # store variable values
    for v in instance.component_objects(Var, active=True):
        # print('variable',v)
        # if str(v)=='step_prod':
        #     for index in v:
        #         # print(index)
        #         # print("    ",index,value(v[index]))
        
        varobject = getattr(instance, str(v))
        a=str(v)
        
        
       
        # production variables
        if a=='step_prod': # index is tuple with (node, qstep, day)
            for index in varobject: #variable index is tuple with node, qstep, day
                producer = index[0]
                
                if int(index[2]==1): #saving only the first day's solution of the 7 day period
                    step_prod.append((index[0],index[1],index[2]+day-1,varobject[index].value)) #save tuple to list

        # pipeline flow variables          
        if a=='step_flow': # index is tuple with (line, ftariff_step, day)
            for index in varobject:
                if int(index[2]==1):
                    step_flow.append((index[0],index[1],index[2]+day-1,varobject[index].value))
        
        if a=='total_pipeline_flow': # index is tuple with (line, day)
            for index in varobject:
                if int(index[1]==1):
                    total_pipeline_flow.append((index[0],index[1]+day-1,varobject[index].value))

        # storage variables
        if a=='storage_withdrawal': # index is tuple with (node, day)
            for index in varobject:
                if int(index[1]==1):
                    storage_withdrawal.append((index[0],index[1]+day-1,varobject[index].value))

        if a=='storage_injection': # index is tuple with (node, day)
            for index in varobject:
                if int(index[1]==1):
                    storage_injection.append((index[0],index[1]+day-1,varobject[index].value))

        # slack variables
        if a=='pipeline_slack': # index is tuple with (line, day)
            for index in varobject:
                if int(index[1]==1):
                    pipeline_slack.append((index[0],index[1]+day-1,varobject[index].value))
        
        
        if a=='production_slack': # index is tuple with (node, day)
            for index in varobject:
                if int(index[1]==1):
                    production_slack.append((index[0],index[1]+day-1,varobject[index].value))

        if a=='storage_slack': # index is tuple with (node, day)
            for index in varobject:
                if int(index[1]==1):
                    storage_slack.append((index[0],index[1]+day-1,varobject[index].value))
       

    print('Day ' +str(day) + ' complete.')

# create dataframe of dual values]
df_duals = pd.DataFrame(state_node_balance_duals,columns=['Node','Day','node_dual_value'])

# create dataframes of production and line flows
df_step_prod = pd.DataFrame(step_prod,columns=['producer','qstep','day','step_prod'])
df_step_flow = pd.DataFrame(step_flow,columns=['line','ftariff_step','day','step_flow'])

# create dataframes of duals, slack flow, and storage utilized
df_total_pipeline_flow = pd.DataFrame(total_pipeline_flow,columns=['line','day','total_pipeline_flow'])
df_storage_withdrawal = pd.DataFrame(storage_withdrawal,columns=['node','day','storage_withdrawal'])
df_storage_injection = pd.DataFrame(storage_injection,columns=['node','day','storage_injection'])
df_pipeline_slack = pd.DataFrame(pipeline_slack,columns=['line','day','pipeline_slack'])
df_production_slack = pd.DataFrame(production_slack,columns=['node','day','production_slack'])
df_storage_slack = pd.DataFrame(storage_slack,columns=['node','day','storage_slack'])


#create dataframe of solve times
# df_solve_times = pd.DataFrame(solve_times,columns=['day','solution_time'])



