#%%
# Last update: 2021/04/06
import csv
import pandas as pd
import numpy as np
import re
import os


# set file path to find input parameter data to write to model file
input_data_filepath = r'C:\Users\calisy\OneDrive\Energy Research\NG Project\code\Gas Model\Model Data Inputs'

# Files Referenced

# 1. QP_BASE_NA_Daily_Downscaled.csv
# 2. PipeCapacities_Dec22_Daily_Downscaled.csv
# 3. imports - daily pipeline and LNG smoothed - 2015-2019.csv
# 4. exports - daily pipeline and LNG smoothed - 2015-2019.csv
# 5. state_daily_production_demand_gulf_added_QPS_2015-2019-bcf.csv
# 6. PipelineTariff.csv
# 7. PipeTariffCurveQty_Daily_Downscaled.csv
# 8. state_max_daily_storage.csv

######=================================================########
######               Set simulation horizon            ########
######=================================================########

SimDays = 365
HorizonDays = 1  ##planning horizon 

# name of dat file when complete
data_name = 'daily_gas_mod_data_6'


#### set number of supply curve steps ####

# set num steps
num_steps = 20

# set num additional steps between 5 and 6 for adding additional Qsteps
k = num_steps - 6


pipeline_slack_cost = 1000
production_slack_cost = 5000
storage_slack_cost = 7000


#%% Adding Additional Supply Curve Steps



#read parameters for QP supply regions
df_QP_NA = pd.read_csv(input_data_filepath + '/' + 'QP_BASE_NA_Daily_Downscaled.csv',header=0)

###### add supply curve steps based on setting above #######
df_qbase = df_QP_NA.copy()

# column for quantity between steps to be added as 'x' values
df_qbase['quantity_added'] = (df_qbase['Qstep6'] - df_qbase['Qstep5']) / (k + 1)

# rename 6 for new naming based on number of steps specified
last_Qstep = 'Qstep'+str(num_steps)
last_Pstep = 'Pstep'+str(num_steps)

df_qbase = df_qbase.rename(columns={'Qstep6':last_Qstep,'Pstep6':last_Pstep})

# print()
# print(df_qbase)



# loop to create new qsteps and psteps via linear interpolation 

for i in range(1,k+1):
    df_qbase['Qstep'+str(5+i)] = df_qbase['Qstep5'] + i*df_qbase['quantity_added']
    
    df_qbase['Pstep'+str(5+i)] = df_qbase['Pstep5'] + (df_qbase['Qstep'+str(5+i)]- df_qbase['Qstep5'])*((df_qbase[last_Pstep]-df_qbase['Pstep5'])/(df_qbase[last_Qstep]-df_qbase['Qstep5']))

# change column order to match original
newq_cols = []
[newq_cols.append('Qstep'+str(i)) for i in range(1,num_steps+1)]

newp_cols = []
[newp_cols.append('Pstep'+str(i)) for i in range(1,num_steps+1)]


cols = ['producer','node'] + newq_cols + newp_cols


df_qbase = df_qbase[cols]

# change back df name
df_QP_NA = df_qbase.copy()



# rename qps producer column
qps = list(df_QP_NA['producer'])
for q in qps:
    new_q = q + '_qps'
    i = qps.index(q)
    qps[i] = new_q
df_QP_NA['producer'] = qps

print('Qbase to new Qsteps dataframe complete')

#%% Create line capacities df and the line to node matrix (-1 leaving node and +1 entering node)

#read downscaled pipeline data
df_line_params = pd.read_csv(input_data_filepath + '/' + 'PipeCapacities_Dec22_Daily_Downscaled.csv',header=0,index_col=0) # I CHANGED THIS TO BE ORIGINAL SO EFFECTIVELY NO REAL CAPACITY
i_nodes = list(df_line_params.index)
c_nodes = list(df_line_params.columns)
nodes = i_nodes + c_nodes
all_nodes = [i for n, i in enumerate(nodes) if i not in nodes[:n]]

 
lines = []
caps = []
tos = []
froms = []

for i in all_nodes:
    for j in all_nodes:
        if i != j:
            line = i+'_to_'+j
            if df_line_params.loc[i,j]>0:
                froms.append(i.replace('-','_'))
                tos.append(j.replace('-','_'))
                lines.append(line)
                caps.append(df_line_params.loc[i,j])
                
for l in lines:
    new_l = l.replace('-','_')
    i = lines.index(l)
    lines[i] = new_l

df_pipelines = pd.DataFrame(caps,index = lines,columns = ['capacity'])


# fix the change from '-' to '_'
# must be done after above since the dataframe has old names
full_nodes_list = [i for n, i in enumerate(nodes) if i not in nodes[:n]]
all_nodes = []
for l in full_nodes_list:
    all_nodes.append(l.replace('-','_'))

# print(all_nodes)


# create line to node matrix
# l_to_n = np.zeros((len(lines),len(all_nodes)))

df_l_to_n = pd.DataFrame(columns=all_nodes)
df_l_to_n['line'] = lines
df_l_to_n.set_index('line',inplace=True)

for i in range(0,len(lines)):
    f = froms[i]
    t = tos[i]
    df_l_to_n.loc[lines[i],f] = -1
    df_l_to_n.loc[lines[i],t] = 1

df_l_to_n = df_l_to_n.fillna(0)

df_l_to_n.to_csv(input_data_filepath + '/' + 'line_to_node_map.csv')

# df_line_to_node_map = pd.read_csv(input_data_filepath + '/' + 'line_to_node_map.csv',header=0)

df_line_to_node_map = df_l_to_n

print('line to node matrix complete')

#%% QPS to node matrix (QPS is rows and nodes are columns - simple unidirectional +1 adjacency matrix)


# create QPS to node matrix

A = np.zeros((len(df_QP_NA),len(all_nodes)))

df_A = pd.DataFrame(A)
df_A.columns = all_nodes
df_A['name'] = list(df_QP_NA['producer'])
df_A.set_index('name',inplace=True)

for i in range(0,len(df_QP_NA)):
    node = df_QP_NA.loc[i,'node']
    g = df_QP_NA.loc[i,'producer']
    df_A.loc[g,node] = 1

df_A.to_csv(input_data_filepath + '/' + 'qps_to_node_map.csv')

df_node_to_producer_map = pd.read_csv(input_data_filepath + '/' + 'qps_to_node_map.csv',header=0)

print('QPS to node matrix complete')


#%% Load input data and create flow tariff inputs

df_daily_imports = pd.read_csv(input_data_filepath + '/' + 'imports - daily pipeline and LNG smoothed - 2015-2019.csv').set_index('Date')
df_daily_exports = pd.read_csv(input_data_filepath + '/' + 'exports - daily pipeline and LNG smoothed - 2015-2019.csv').set_index('Date')
df_daily_demand_production = pd.read_csv(input_data_filepath + '/' + 'state_daily_production_demand_gulf_added_QPS_2015-2019-bcf.csv')

df_daily_production_cols = df_daily_demand_production.pivot(index='date',columns='state abbrev',values='production (bcf)')
df_daily_demand_cols = df_daily_demand_production.pivot(index='date',columns='state abbrev',values='demand (bcf)')

# filter for last 7 days of 2018 for initial conditions plus 2019 data


df_daily_imports_write = df_daily_imports.loc['2018-12-25':'2019-12-31'].reset_index()
df_daily_exports_write = df_daily_exports.loc['2018-12-25':'2019-12-31'].reset_index()
df_daily_production_write = df_daily_production_cols.loc['2018-12-25':'2019-12-31'].reset_index()
df_daily_demand_write = df_daily_demand_cols.loc['2018-12-25':'2019-12-31'].reset_index()



# add zero nodes to demand data
zero_nodes = ['ME_CN_E', 'NH_CN_E','VT_CN_E','NY_CN_E','MI_CN_E','MN_CN_W','ND_CN_W','MT_CN_W','ID_CN_W','WA_CN_W',
 'TX_MX_NE','AZ_MX_NW','CA_MX_NW','TX_MX_SS','MX_NE','MX_NW','MX_IW','MX_CE','MX_SS','CN_E','CN_W']

for node in zero_nodes:
    df_daily_demand_write[node] = 0
df_daily_demand_write.to_csv(input_data_filepath + '/' + 'check of zero node demands.csv')

print('zero demand nodes manually added: MX, CN, border nodes')



#node-to-node flow tariffs
nodal_flow_tariffs = pd.read_csv(input_data_filepath + '/' + 'PipelineTariff.csv',header=0,index_col = None)

froms = list(nodal_flow_tariffs['from'])
tos = list(nodal_flow_tariffs['to'])

for f in froms:
    new_f = f.replace('-','_')
    i = froms.index(f)
    froms[i] = new_f

for t in tos:
    new_t = t.replace('-','_')
    i = tos.index(t)
    tos[i] = new_t

L = []
for i in range(0,len(nodal_flow_tariffs)):
    L.append(froms[i] + '_to_' + tos[i])

nodal_flow_tariffs.index=L
nodal_flow_tariffs = nodal_flow_tariffs.drop(columns=['to','from'])



#node-to-node flow tariff quantities
nodal_flow_tariffs_CAP = pd.read_csv(input_data_filepath + '/' + 'PipeTariffCurveQty_Daily_Downscaled.csv',header=0)

froms = list(nodal_flow_tariffs_CAP['from'])
tos = list(nodal_flow_tariffs_CAP['to'])

for f in froms:
    new_f = f.replace('-','_')
    i = froms.index(f)
    froms[i] = new_f

for t in tos:
    new_t = t.replace('-','_')
    i = tos.index(t)
    tos[i] = new_t
    
L = []
for i in range(0,len(nodal_flow_tariffs_CAP)):
    L.append(froms[i] + '_to_' + tos[i])

nodal_flow_tariffs_CAP.index=L
nodal_flow_tariffs_CAP = nodal_flow_tariffs_CAP.drop(columns=['to','from'])


print('node to node flow tariffs and quantities added')

# %% import storage daily max withdrawal data

df_max_withdrawal = pd.read_csv(input_data_filepath + '/' + 'state_max_daily_storage.csv')


#%% Write to data file
print('writing to data file')

######====== write data.dat file ======########
with open(''+str(data_name)+'.dat', 'w') as f:

  
####### producer sets by type  

    # Non-associated
    f.write('set NA :=\n')
    
    # pull relevant generators
    for prod in range(0,len(df_QP_NA)):
        unit_name = df_QP_NA.loc[prod,'producer']
        f.write(unit_name + ' ')
    f.write(';\n\n')        

    print('Producer set written')


######Set nodes, sources and sinks

    # nodes
    f.write('set nodes :=\n')
    for z in all_nodes:
        name = z.replace('-','_')
        f.write(name + ' ')
    f.write(';\n\n')
    
    print('node set written')
    
    # lines
    f.write('set lines :=\n')
    for z in lines:
        f.write(z + ' ')
    f.write(';\n\n')
    
    print('lines set written')
    
    
###### Set of Qsteps
    Qstep_set = [i for i in range(1,num_steps+1)]
    f.write('set num_Qsteps :=\n')
    for i in Qstep_set:
        f.write(str(i) + ' ')
    f.write(';\n\n')
    print('num_Qsteps set written')
    

###### Set of Ftariff steps (currently just the number of columns in the dataframe)
    num_FTariff_steps = len(nodal_flow_tariffs_CAP.columns)
    fstep_set = [i for i in range(1,num_FTariff_steps+1)]
    
    f.write('set num_FTariff_steps :=\n')
    for i in fstep_set:
        f.write(str(i) + ' ')
    f.write(';\n\n')
    print('num_FTariff_steps set written')
    

####### simulation period and horizon
    f.write('param SimDays := %d;' % SimDays)
    f.write('\n')
    f.write('param HorizonDays := %d;' % HorizonDays)
    f.write('\n\n')
    
###### slack costs
    f.write('param pipeline_slack_cost := %d;' % pipeline_slack_cost)
    f.write('\n\n')

    f.write('param production_slack_cost := %d;' % production_slack_cost)
    f.write('\n\n')

    f.write('param storage_slack_cost := %d;' % storage_slack_cost)
    f.write('\n\n')

######=================================================########
######              Producers                     ########
######=================================================########
    
####### create parameter matrix for producers
    f.write('param:' + '\t' + 'Qstep' + '\t'+ 'Pstep')
    # for c in df_QP_NA.columns:
    #     if c not in ['node', 'producer']:
    #         f.write(c + '\t')
    f.write(':=\n\n')
    for i in range(0,len(df_QP_NA)):    
        
        
        for c in range(1,num_steps+1):
            
            unit_name = df_QP_NA.loc[i,'producer']
            unit_name = unit_name.replace(' ','_')
            unit_name = unit_name.replace('&','_')
            unit_name = unit_name.replace('.','')
            qn = 'Qstep' + str(c)
            pn = 'Pstep' + str(c)
            f.write(unit_name + '\t' + str(c) + '\t' + str(df_QP_NA.loc[i,qn]) + '\t' + str(df_QP_NA.loc[i,pn]))  
            f.write('\n')
            
    f.write(';\n\n')     
    
    print('QPS step params written')
    

       

######=================================================########
######               Pipelines                       ########
######=================================================########

####### create parameter matrix for pipeline paths (source and sink connections)
    f.write('param:' + '\t' + 'FlowLim :=' + '\n')
    for z in lines:
        f.write(z + '\t' + str(df_pipelines.loc[z,'capacity']) + '\n')
    f.write(';\n\n')
    
    # create a separate csv file of lines and their capacities for the map
    line_cap = []
    for z in lines:
        line_cap.append(df_pipelines.loc[z,'capacity'])
        
    df_linecap = pd.DataFrame({'line':lines,'capacity':line_cap})
    df_linecap.to_csv(input_data_filepath + '/' + 'lines with capacities.csv',index=False)

    print('pipeline capacities param written')
    
    ####### create parameter matrix for pipeline tariffs and capacities at each step

    f.write('param:' + '\t' + 'FTariff_CAP' + '\t'+ 'FTariff')
    f.write(':=\n\n')
    
    tariff_lst = list(nodal_flow_tariffs.index)
    
    for l in lines:
        for c in range(1,num_FTariff_steps+1):
            line_name = l
            if l in tariff_lst:
                f.write(line_name + '\t' + str(c) + '\t' + str(nodal_flow_tariffs_CAP.loc[l,'step'+str(c)]) + '\t' + str(nodal_flow_tariffs.loc[l,'step'+str(c)]))
                f.write('\n')
            else:
                f.write(line_name + '\t' + str(c) + '\t' + str(0) + '\t' + str(0))
                f.write('\n')
    f.write(';\n\n')
    
    print('pipeline tariffs and quantities param written')
    


    ######=================================================########
    ######               Storage                     ########
    ######=================================================########


    f.write('param:' + '\t' + 'storage_max_withdrawal :=' + '\n')
    for z in all_nodes:
        if z in df_max_withdrawal['State'].values:
            max_with = df_max_withdrawal.loc[df_max_withdrawal['State'] == z]['maxdeliv (bcf)'].values[0]
        else:
            max_with = 0
        f.write(z + '\t' + str(max_with) + '\n')
    f.write(';\n\n')

    
    
    ######=================================================########
    ######               Daily Time Series                     ########
    ######=================================================########


    ###### PRODUCTION #####
    f.write('param:' + '\t' + 'Sim_production :=' + '\n')
    for z in all_nodes:
        for h in range(0,len(df_daily_production_write)):
            new = z.replace('-','_')
            if z in df_daily_production_write.columns:
                daily_prod = df_daily_production_write.loc[h,z]
                f.write(new + '\t' + str(h+1) + '\t' + str(daily_prod) + '\n')
            else:
                f.write(new + '\t' + str(h+1) + '\t' + str(0.0) + '\n')
    f.write(';\n\n')
    
    ###### DEMAND #####

    f.write('param:' + '\t' + 'SimDemand :=' + '\n')      
    for z in all_nodes:
        for h in range(0,len(df_daily_demand_write)):
            new = z.replace('-','_')
            if z in df_daily_demand_write.columns:
                f.write(new + '\t' + str(h+1) + '\t' + str(df_daily_demand_write.loc[h,z]) + '\n')
            else:
                f.write(new + '\t' + str(h+1) + '\t' + str(0.0) + '\n')
    f.write(';\n\n')
    
    print('demand params written')
    
    ###### STORAGE INJECTIONS #####
    # f.write('param:' + '\t' + 'Sim_storage_injection:=' + '\n') 
    # for z in all_nodes:
    #     for h in range(0,len(df_net_storage)):
    #         new = z.replace('-','_')
    #         if z in df_net_storage.columns:
    #             storage_injection = abs(max(df_net_storage.loc[h,z],0))
    #             f.write(new + '\t' + str(h+1) + '\t' + str(storage_injection) + '\n')
    #         else:
    #             f.write(new + '\t' + str(h+1) + '\t' + str(0.0) + '\n')
    # f.write(';\n\n')            
    # print('storage injections written')
    
    ###### STORAGE WITHDRAWALS #####
    # f.write('param:' + '\t' + 'Sim_storage_withdrawal:=' + '\n') 
    # for z in all_nodes:
    #     for h in range(0,len(df_net_storage)):
    #         new = z.replace('-','_')
    #         if z in df_net_storage.columns:
    #             storage_withdrawal = abs(min(df_net_storage.loc[h,z],0))
    #             f.write(new + '\t' + str(h+1) + '\t' + str(storage_withdrawal) + '\n')
    #         else:
    #             f.write(new + '\t' + str(h+1) + '\t' + str(0.0) + '\n')
    # f.write(';\n\n')            
    # print('storage withdrawals written')
    
    ###### IMPORTS #####
    f.write('param:' + '\t' + 'Sim_imports :=' + '\n')
    for z in all_nodes:
        for h in range(0,len(df_daily_imports_write)):
            new = z.replace('-','_')
            if z in df_daily_imports_write.columns:
                daily_import = df_daily_imports_write.loc[h,z]
                f.write(new + '\t' + str(h+1) + '\t' + str(round(daily_import,3)) + '\n')
            else:
                f.write(new + '\t' + str(h+1) + '\t' + str(0.0) + '\n')
    f.write(';\n\n')
    print('imports written')
    
    ###### EXPORTS #####
    f.write('param:' + '\t' + 'Sim_exports :=' + '\n')
    for z in all_nodes:
        for h in range(0,len(df_daily_exports_write)):
            new = z.replace('-','_')
            if z in df_daily_exports_write.columns:
                daily_export = df_daily_exports_write.loc[h,z]
                f.write(new + '\t' + str(h+1) + '\t' + str(round(daily_export,3)) + '\n')
            else:
                f.write(new + '\t' + str(h+1) + '\t' + str(0.0) + '\n')
    f.write(';\n\n')
    print('exports written')
    
    
    ###### QPS TO NODE MAP DATA #####
    
    f.write('param QPS_to_node:')
    f.write('\n')
    f.write('\t' + '\t')

    for j in df_node_to_producer_map.columns:
        if j!= 'name':
            j_new = j.replace('-','_')
            f.write(j_new + '\t')
    f.write(':=' + '\n')
    for i in range(0,len(df_node_to_producer_map)):   
        for j in df_node_to_producer_map.columns:
            f.write(str(df_node_to_producer_map.loc[i,j]) + '\t')
        f.write('\n')
    f.write(';\n\n')
    
    print('Producers to node map written')

    ###### LINE TO NODE MAP DATA #####

    f.write('param line_to_node:')
    f.write('\n')
    f.write('\t' + '\t')

    for j in df_line_to_node_map.columns:
        if j!= 'line':
            j_new = j.replace('-','_')
            f.write(j_new + '\t')
    f.write(':=' + '\n')
    for l in lines:
        f.write(str(l) + '\t')
        for j in df_line_to_node_map.columns:
            f.write(str(df_line_to_node_map.loc[l,j]) + '\t')
        f.write('\n')
    f.write(';\n\n')
    
    print('Line to node map written')

    

print ('Complete:',data_name)
 # this opens the data file in spyder (can comment out if not needed)


# %edit daily_gas_mod_data_5.dat # this opens the data file in spyder (can comment out if not needed)
