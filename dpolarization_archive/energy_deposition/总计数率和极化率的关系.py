# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     formats: ipynb,py:percent
#     notebook_metadata_filter: kernelspec,language_info,jupytext
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.ticker import ScalarFormatter, LogFormatter,LogLocator

import math

# %%
from scipy.interpolate import interp1d
from scipy.interpolate import make_interp_spline

T = pd.read_csv('DataOfCrosssectionAndPol/CompletSetOFT/T.txt', sep=' ', na_values=['NaN'])
DSigamaOverDOmega = pd.read_csv('DataOfCrosssectionAndPol/DSigamaOverDOmega.txt',sep='    ', skiprows=4,engine='python')
iT11 = interp1d(T['θc.m.(deg)'].values/180*np.pi,T["iT11"].values)
T20 = interp1d(T['θc.m.(deg)'].values/180*np.pi,T['T20'].values)
T21 = interp1d(T['θc.m.(deg)'].values/180*np.pi,T["T21"].values)
T22 = interp1d(T['θc.m.(deg)'].values/180*np.pi,T["T22"].values)

σDA=interp1d(DSigamaOverDOmega['theta'].values/180*np.pi,DSigamaOverDOmega['SigamaDA'].values)

valid = ~np.isnan(T["T21"].values)

Ay = interp1d( T['θc.m.(deg)'].values/180*np.pi , -2 / np.sqrt(3) * T["iT11"].values)
AyErr=2 / np.sqrt(3) * T["∆iT11"].values
print(AyErr)
print(-2 / np.sqrt(3) * T["iT11"].values)
Axz = interp1d(T['θc.m.(deg)'].values[valid]/180*np.pi , -np.sqrt(3) * T["T21"].values[valid]     )
AxzErr = -np.sqrt(3) * T["∆T21"].values[valid]
Axx = interp1d(T['θc.m.(deg)'].values/180*np.pi , np.sqrt(3) * T["T22"].values - 1/np.sqrt(2) * T["T20"].values)
AxxErr = np.sqrt(3* np.square( T["∆T22"].values) +1/2*np.square(T["∆T20"].values) )
Ayy = interp1d(T['θc.m.(deg)'].values/180*np.pi , -np.sqrt(3) * T["T22"].values - 1/np.sqrt(2) * T["T20"].values )
AyyErr = np.sqrt( 3* np.square(T["∆T22"].values) + 1/2*np.square(T["∆T20"].values ) )
Azz = interp1d(T['θc.m.(deg)'].values/180*np.pi , np.sqrt(2) * T["T20"].values)
AzzErr = np.sqrt(2) * T["∆T20"].values


# %%
mD = 1875.612
mP = 938
Ek = 380

# %%



    
def TranToThetacm(theta2lab):
    return math.atan(1.08716 * math.tan(theta2lab)) + math.asin(2.04457 * math.tan(theta2lab) / math.sqrt(1.18192 * math.tan(theta2lab)**2 + 1))

def sigamtrans(theta2lab):
    # num = (0.919825 * math.tan(theta_lab)**2 + 0.576941 * math.sqrt(1.18192 * math.tan(theta_lab)**2 + 1) * math.sqrt(1 / (0.334175 * math.tan(theta_lab)**2 + 0.282738) - 2.53684) - 0.306778) * (1 / math.cos(theta_lab)**2) * math.sin(math.asin(2.04457 * math.tan(theta_lab) / math.sqrt(1.18192 * math.tan(theta_lab)**2 + 1)) - math.atan(1.08716 * math.tan(theta_lab)))
    # den = 1 * math.tan(theta_lab)**4 + 0.512562 * math.tan(theta_lab)**2 - 0.282182
    # return num / den * (1 / math.sin(theta_lab))
    num = -0.576941 * (-1.59432 * math.tan(theta2lab)**2 + 1 * math.sqrt(1.18192 * math.tan(theta2lab)**2 + 1) * math.sqrt(1 / (0.334175 * math.tan(theta2lab)**2 + 0.282738) - 2.53684) + 0.531732) * (1 / math.sin(theta2lab)) * (1 / math.cos(theta2lab)**2) * math.sin(math.atan(1.08716 * math.tan(theta2lab)) + math.asin(2.04457 * math.tan(theta2lab) / math.sqrt(1.18192 * math.tan(theta2lab)**2 + 1)))
    den = 1 * math.tan(theta2lab)**4 + 0.512562 * math.tan(theta2lab)**2 - 0.282182
    return num / den

def sigamlab(thetalab):
    return σDA(TranToThetacm(thetalab))*sigamtrans(thetalab)

def Azzlab(thetalab):
    return Azz(TranToThetacm(thetalab))

def TranToThelabDeg(thetacmdeg):   
        thetacmrad=thetacmdeg*math.pi/180
        return math.atan((400.08 * math.sin(thetacmrad)) / (817.991 + 434.952 * math.cos(thetacmrad)))*180/math.pi


# %%

#立体角 跨度一度
dOmega = np.pi*(1/180*np.pi)**2
#厚度 10000 g/m^2 = 1000 mg/cm^2
d=10000
#聚乙烯摩尔质量g/mol
MCH2=14
NA=6.02214076*10**23
#束流 安培 
I=1.6*10**-3*10**-9
e=1.602176634 *10**(-19)

print(dOmega)

# %%
#分钟
N_min=30
t=60*N_min

# %% [markdown]
# 设置角度

# %%
thetalabBest=20.87


# %%
def sigma(P_pol):
    p_scater=d/MCH2*NA*2*sigamlab(thetalabBest/180*np.pi)*10**-31*dOmega*4*(1+0.5*P_pol*Azzlab(thetalabBest/180*np.pi))
    return math.sqrt(I/e*t * (p_scater)*(1-p_scater))

def N_count(P_pol):
    p_scater=d/MCH2*NA*2*sigamlab(thetalabBest/180*np.pi)*10**-31*dOmega*4*(1+0.5*P_pol*Azzlab(thetalabBest/180*np.pi))
    return I/e*t * p_scater
    
    

# %%
p=d/MCH2*NA*sigamlab(22/180*np.pi)*10**-31*dOmega*4*(1+0.5*0.1*Azzlab(22/180*np.pi))
print(p)
print(Azzlab(22/180*np.pi))

# %%

# 创建一个包含从0到1的十个点的数组
P_pol = np.linspace(0, 1, 10)

# 计算 N_count 和 sigma
N_counts = np.array([N_count(p) for p in P_pol])
sigmas = np.array([sigma(p) for p in P_pol])

# 创建一个新的图表并设置图表的大小
plt.figure(figsize=(6, 5))
# 绘制误差棒图
plt.errorbar(P_pol, N_counts, yerr=sigmas, fmt='o',markersize=2)
# 设置全局字体大小
plt.rcParams['font.size'] = 14
# 设置图表标题和坐标轴标签
plt.title('The total counts in {} minutes'.format(N_min) )
plt.xlabel('Pzz')
plt.ylabel('N_countTot')
# 设置纵坐标为科学计数法
plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))

# plt.savefig('test.svg', format='svg')
plt.savefig('fig1.jpg', dpi=600)
# 显示图表
plt.show()
