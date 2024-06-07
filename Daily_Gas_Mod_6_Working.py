# -*- coding: utf-8 -*-
# %%
"""
Created on Fri Jul 28 12:20:43 2023

@author: Cameron Lisy and Jordan Kern
"""

from pyomo.environ import *
from pyomo.environ import value
import numpy as np

model = AbstractModel()

#%% Sets and basic production Qstep and flow tariff step parameters

### Producers by fuel-type
model.NA = Set()

# network data
model.lines = Set() # lines are total pipeline connections betweens states
model.nodes = Set() # nodes are states

# number of Qsteps
model.num_Qsteps = Set()

# number of ftariff steps
model.num_FTariff_steps = Set()

# slack costs
model.pipeline_slack_cost = Param(within=Any)
model.production_slack_cost = Param(within=Any)
model.storage_slack_cost = Param(within=Any)

#qps Qstep and Pstep parameters
model.Qstep = Param(model.NA,model.num_Qsteps,within=Any)
model.Pstep = Param(model.NA,model.num_Qsteps,within=Any)

# pipeline capacities parameter
model.FlowLim = Param(model.lines)

# QPS to node matrix parameter
model.QPS_to_node=Param(model.NA,model.nodes)

# line to node matrix parameter
model.line_to_node=Param(model.lines,model.nodes)

# flow tariff cost  parameter as iterable matrix
model.FTariff = Param(model.lines,model.num_FTariff_steps)


# flow tariff quantity parameter as iterable matrix
model.FTariff_CAP = Param(model.lines,model.num_FTariff_steps) 

#%% Instance data parameters including Demand, storage, imports and exports

######===== Parameters/initial_conditions to run simulation ======####### 

## Full range of time series information
model.SimDays = Param(within=PositiveIntegers) # sets the number of model days
model.SD_periods = RangeSet(1,model.SimDays+1) # creates the array of model days as periods

# Operating horizon information 
model.HorizonDays = Param(within=PositiveIntegers) #sets the number of day in look ahead horizon
model.HD_periods = RangeSet(1,model.HorizonDays) # creates the array of days in horizon period

#Demand information
model.SimDemand = Param(model.nodes*model.SD_periods, within=NonNegativeReals)
model.HorizonDemand = Param(model.nodes*model.HD_periods,within=NonNegativeReals,mutable=True)

# model.nodes*model.SD_periods IS A CARTESIAN PRODUCTION and same thing as [model.nodes,model.SD_periods]


# Storage 
# storage injections and withdrawals over simulation period
# model.Sim_storage_injection = Param(model.nodes*model.SD_periods, within=NonNegativeReals)
# model.Sim_storage_withdrawal = Param(model.nodes*model.SD_periods, within=NonNegativeReals)

# storage injections and withdrawals over look ahead horizon
# model.Horizon_storage_injection = Param(model.nodes*model.HD_periods,within=NonNegativeReals,mutable=True)
# model.Horizon_storage_withdrawal = Param(model.nodes*model.HD_periods,within=NonNegativeReals,mutable=True)

# Storage costs over look ahead horizon
# model.Sim_storage_cost = Param(model.nodes*model.SD_periods,within=NonNegativeReals)
model.Horizon_storage_cost = Param(model.nodes*model.HD_periods,within=NonNegativeReals, mutable=True)

# storage maximum withdrawal
model.storage_max_withdrawal = Param(model.nodes,within=NonNegativeReals, mutable=True)

# Imports and Exports
# Imports and exports over simulation period
model.Sim_imports =  Param(model.nodes*model.SD_periods,within=NonNegativeReals)
model.Sim_exports = Param(model.nodes*model.SD_periods,within=NonNegativeReals,mutable=True)

# Imports and exports over look ahead horizon
model.Horizon_imports = Param(model.nodes*model.HD_periods,within=NonNegativeReals,mutable=True)
model.Horizon_exports = Param(model.nodes*model.HD_periods,within=NonNegativeReals,mutable=True)

# Production
model.Sim_production = Param(model.nodes*model.SD_periods,within=NonNegativeReals)
model.Horizon_production = Param(model.nodes*model.HD_periods,within=NonNegativeReals,mutable=True)



#%% Decision variables

# production at each QPS step
model.step_prod = Var(model.NA,model.num_Qsteps,model.HD_periods,within=NonNegativeReals,initialize=0)

# pipeline flow at each tariff step
model.step_flow = Var(model.lines,model.num_FTariff_steps,model.HD_periods,within=NonNegativeReals, initialize=0) # must be positive and negative

# total pipeline flow (sum of all flow tariff steps)
model.total_pipeline_flow = Var(model.lines,model.HD_periods,within=NonNegativeReals,initialize=0)

# add slack flow variable where flow must exceed pipeline capacity to meet demand and
# make the model feasible
model.pipeline_slack = Var(model.lines,model.HD_periods, within=NonNegativeReals,initialize=0)
model.production_slack = Var(model.nodes,model.HD_periods, within=NonNegativeReals,initialize=0)
model.storage_slack = Var(model.nodes,model.HD_periods, within=NonNegativeReals,initialize=0)

# storage utilized, make it flexible to only use what it wants
# model.storage_utilization = Var(model.nodes*model.HD_periods, within=NonNegativeReals, initialize=0)

# storage withdrawals
model.storage_withdrawal = Var(model.nodes,model.HD_periods,within=NonNegativeReals,initialize=0)
model.storage_injection = Var(model.nodes,model.HD_periods,within=NonNegativeReals,initialize=0)

# storage injections (add after model runs for winter time)


#%% Model Objective Function

def SysCost(model):
    # production and pipeline flow costs
    production = sum(model.step_prod[i,j,t]*model.Pstep[i,j] for i in model.NA for j in model.num_Qsteps for t in model.HD_periods)
    pipeline_flows = sum(model.step_flow[l,k,t]*model.FTariff[l,k] for l in model.lines for k in model.num_FTariff_steps for t in model.HD_periods)

    # storage withdrawal costs
    storage_withdrawals = sum(model.storage_withdrawal[n,t]*model.Horizon_storage_cost[n,t] for n in model.nodes for t in model.HD_periods)

    # slack costs
    pipeline_slack = sum(model.pipeline_slack[l,t]*model.pipeline_slack_cost for l in model.lines for t in model.HD_periods)
    production_slack = sum(model.production_slack[n,t]*model.production_slack_cost for n in model.nodes for t in model.HD_periods)
    storage_slack = sum(model.storage_slack[n,t]*model.storage_slack_cost for n in model.nodes for t in model.HD_periods)
    
  
    return production + pipeline_flows + storage_withdrawals + pipeline_slack + production_slack + storage_slack

model.SystemCost = Objective(rule=SysCost, sense=minimize)

#%% Model Constraints

# Constraint for qstep production to sum to actual production parameter
# This allows production to be divided into qsteps for the objective function
def ProdSum(model,n,t):
    return sum(sum(model.step_prod[i,j,t] for j in model.num_Qsteps)*model.QPS_to_node[i,n] for i in model.NA) == model.Horizon_production[n,t] - model.production_slack[n,t]

model.Qstep_prod = Constraint(model.nodes,model.HD_periods,rule=ProdSum)

# Constraints for max production at each QPS
def MaxQP(model,i,j,t) :
    if j == 1:
        return model.step_prod[i,j,t] <= model.Qstep[i,j]
    elif j < 20: # this should be num qsteps - 1
        return model.step_prod[i,j,t] <= (model.Qstep[i,j] - model.Qstep[i,j-1])
    else:
        return Constraint.Skip
    
model.Max_Cap_QP = Constraint(model.NA,model.num_Qsteps,model.HD_periods,rule=MaxQP)


#  Constraints for pipeline flow for flow tariff
def MaxPipe(model,l,k,t):
    if k == 1:
        return model.step_flow[l,k,t] <= model.FTariff_CAP[l,k]
    elif k < 5: #this should be the num psteps - 1 
        return model.step_flow[l,k,t] <= (model.FTariff_CAP[l,k] - model.FTariff_CAP[l,k-1])
    else:
        return Constraint.Skip
    
model.Max_Cap_Flow = Constraint(model.lines,model.num_FTariff_steps,model.HD_periods,rule=MaxPipe)

# pipeline flow sum constraint
# variable linking flow to lines
def FlowSum(model,l,t):
    return sum(model.step_flow[l,k,t] for k in model.num_FTariff_steps) == model.total_pipeline_flow[l,t]

model.FlowSum_Constraint = Constraint(model.lines,model.HD_periods,rule=FlowSum)

# Pipeline flow Capacity constraints
# total_pipeline_flow variable ties the flow tariff steps to the flow limit
def Flow_lim(model,l,t):
    return model.total_pipeline_flow[l,t] <= model.FlowLim[l] + model.pipeline_slack[l,t] #opposite sign for negative

model.Flow_Constraint = Constraint(model.lines,model.HD_periods,rule=Flow_lim)

# Storage daily capacity constraint
def MaxWithdrawal(model,n,t):
    return model.storage_withdrawal[n,t] <= model.storage_max_withdrawal[n] + model.storage_slack[n,t]

model.MaxStorageWithdrawal= Constraint(model.nodes,model.HD_periods,rule=MaxWithdrawal)


# Nodal Balance Constraints
def Nodal_Balance(model,n,t):
    flow = sum(model.total_pipeline_flow[l,t]*model.line_to_node[l,n] for l in model.lines) # flows into node n if positive, flows out of node n if negative
    production = sum(sum(model.step_prod[i,j,t] for j in model.num_Qsteps)*model.QPS_to_node[i,n] for i in model.NA) # production at node n
    net_demand = model.HorizonDemand[n,t] + model.storage_injection[n,t] - model.storage_withdrawal[n,t] - model.Horizon_imports[n,t] + model.Horizon_exports[n,t] # net demand at node n including storage withdrawals
    
    return flow + production == net_demand

model.Node_Constraint = Constraint(model.nodes,model.HD_periods,rule=Nodal_Balance)
