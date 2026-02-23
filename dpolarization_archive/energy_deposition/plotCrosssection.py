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
#     display_name: base
#     language: python
#     name: python3
# ---

# %%
import pandas as pd
import numpy as np
# 使用空格分隔符，将-视为缺失值
T = pd.read_csv('DataOfCrosssectionAndPol/CompletSetOFT/T.txt', sep=' ', na_values=['NaN'])


# %%
print(T)

# %%
DSigamaOverDOmega = pd.read_csv('DataOfCrosssectionAndPol/DSigamaOverDOmega.txt',sep='    ', skiprows=4,engine='python')

# %%
print(DSigamaOverDOmega)

# %% [markdown]
# 写插值函数

# %%
from scipy.interpolate import interp1d
from scipy.interpolate import make_interp_spline

iT11 = interp1d(T['θc.m.(deg)'].values/180*np.pi,T["iT11"].values)
T20 = interp1d(T['θc.m.(deg)'].values/180*np.pi,T['T20'].values)
T21 = interp1d(T['θc.m.(deg)'].values/180*np.pi,T["T21"].values)
T22 = interp1d(T['θc.m.(deg)'].values/180*np.pi,T["T22"].values)

σDA=interp1d(DSigamaOverDOmega['theta'].values/180*np.pi,DSigamaOverDOmega['SigamaDA'].values)


# σDA=make_interp_spline(DSigamaOverDOmega['theta'].values/180*np.pi,DSigamaOverDOmega['SigamaDA'].values,k=2)


# %% [markdown]
# ## 画图

# %% [markdown]
#

# %%
def ones(x):
    return 1.0



# %%
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.ticker import ScalarFormatter, LogFormatter,LogLocator

# %%
theta, phi = np.linspace(0.49, 2.94, 100), np.linspace(0, np.pi, 100)
sigama = σDA(theta)

fig, ax = plt.subplots()
# 绘制函数图像
ax.plot(theta*180/np.pi, sigama)

# 添加坐标轴标签和标题
plt.xlabel(r'$\theta_{c.m}$[deg]',fontsize=18)
plt.ylabel(r'$\frac{d \sigma}{d \Omega} $[mb/sr]',fontsize=18)
plt.title('Unpolarized differential scattering cross-section')
ax.yaxis.set_label_coords(-0.1, 0.5) # 设置标签位置
ax.set_yscale('log')
# 显示图形

# 设置 y 轴刻度标签的格式
ax.yaxis.set_major_formatter(LogFormatter(base=10))

# 自定义 y 轴上的刻度
ax.yaxis.set_minor_locator(LogLocator(subs=np.arange(0.1, 1, 0.1), numticks=10))
ax.set_ylim([0, 10])


plt.show()

# %%


# 定义球面上的坐标点
theta, phi = np.linspace(0.49, 2.94, 100), np.linspace(0, 2*np.pi, 100)
theta, phi = np.meshgrid(theta, phi)
x, y, z = np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)

# 计算球面上的场值
field = σDA(theta)*ones(phi)


# 绘制球面上的场值图
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
P1 = ax.scatter(x, y, z, c=field, cmap='jet')
# 添加颜色条
fig.colorbar(P1)
plt.xlabel('x')
plt.ylabel('y')
plt.title('Unpolarized differential scattering cross-section')

plt.show()

# %% [markdown]
# ## 极化情况
#
#

# %%
from scipy.interpolate import CubicSpline

valid = ~np.isnan(T["T21"].values)

Ay = CubicSpline(T['θc.m.(deg)'].values/180*np.pi, -2 / np.sqrt(3) * T["iT11"].values)
AyErr = 2 / np.sqrt(3) * T["∆iT11"].values
print(AyErr)
print(-2 / np.sqrt(3) * T["iT11"].values)

Axz = CubicSpline(T['θc.m.(deg)'].values[valid]/180*np.pi, -np.sqrt(3) * T["T21"].values[valid])
AxzErr = np.sqrt(3) * T["∆T21"].values[valid]

Axx = CubicSpline(T['θc.m.(deg)'].values/180*np.pi, np.sqrt(3) * T["T22"].values - 1/np.sqrt(2) * T["T20"].values)
AxxErr = np.sqrt(3 * np.square(T["∆T22"].values) + 1/2 * np.square(T["∆T20"].values))

Ayy = CubicSpline(T['θc.m.(deg)'].values/180*np.pi, -np.sqrt(3) * T["T22"].values - 1/np.sqrt(2) * T["T20"].values)
AyyErr = np.sqrt(3 * np.square(T["∆T22"].values) + 1/2 * np.square(T["∆T20"].values))

Azz = CubicSpline(T['θc.m.(deg)'].values/180*np.pi, np.sqrt(2) * T["T20"].values)
AzzErr = np.sqrt(2) * T["∆T20"].values

# %% [markdown]
#

# %%
theta_tem = np.linspace(44/180*np.pi, 160/180*np.pi, 100) 
mask = np.logical_not(np.isnan(-np.sqrt(3) * T["T21"].values))

# 设置图形大小和分辨率
plt.figure(figsize=(10, 6), dpi=300, facecolor='white')

plt.ylim(-1.5, 1.5)


plt.errorbar(
    T['θc.m.(deg)'].values, 
    -2 / np.sqrt(3) * T["iT11"].values, 
    yerr=AyErr, 
    label=r"$A_{y}$",
    color='#1b1b1b',
    linestyle='-',
    # marker='o',
    # markersize=6,
    # markerfacecolor='white',
    # markeredgewidth=1.2,
    capsize=3,
    zorder=2
)
plt.errorbar(
    T['θc.m.(deg)'].values[mask], 
    -np.sqrt(3) * T["T21"].values[mask], 
    yerr=AxzErr, 
    label=r"$A_{xz}$",
    color='#4e79a7',
    linestyle='--',
    # marker='s',
    # markersize=6,
    # markerfacecolor='white',
    # markeredgewidth=1.2,
    capsize=3,
    zorder=2
)
plt.errorbar(
    T['θc.m.(deg)'].values, 
    2 * np.sqrt(3) * T["T22"].values, 
    yerr=AzzErr, 
    label=r"$A_{xx}-A_{zz}$",
    color='#f28e2b',
    linestyle='-.',
    # marker='^',
    # markersize=6,
    # markerfacecolor='white',
    # markeredgewidth=1.2,
    capsize=3,
    zorder=2
)
plt.errorbar(
    T['θc.m.(deg)'].values, 
    np.sqrt(2) * T["T20"].values, 
    yerr=AzzErr, 
    label=r"$A_{zz}$",
    color='#e15759',
    linestyle=':',
    # marker='D',
    # markersize=6,
    # markerfacecolor='white',
    # markeredgewidth=1.2,
    capsize=3,
    zorder=2
)
# 让误差棒在marker之上
# for line in plt.gca().lines:
#     line.set_zorder(3)
# for cap in plt.gca().collections:
#     cap.set_zorder(4)
# 设置刻度标签的字体大小
plt.xticks(fontsize=24)
plt.yticks(fontsize=24)
# 设置标签并添加背景颜色
plt.xlabel(r'$\theta_{\mathrm{c.m.}}$[deg]', fontsize=28, labelpad=18, bbox=dict(facecolor='white', edgecolor='none'))
plt.ylabel('Analysing Power', fontsize=28, labelpad=18, bbox=dict(facecolor='white', edgecolor='none'))


# 设置坐标轴刻度为科学计数法
plt.ticklabel_format( axis='both')


# 增加图例和网格线
plt.legend(fontsize=18, loc='upper left', frameon=False)
plt.grid(True)

# 保存图形为矢量图
plt.savefig('A_zzshow.pdf', format='pdf', bbox_inches='tight')

plt.show()


# %%
import scipy
print(scipy.__version__)

# %%
px=0
py=0
pxz=0
pyz=0
pxx=0
pyy=0
pxy=0
pzz=0

# 定义球面上的坐标点
theta, phi = np.linspace(44/180*np.pi, 160/180*np.pi, 100), np.linspace(0, 2*np.pi, 100)
theta, phi = np.meshgrid(theta, phi)
x, y, z = np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)

# 计算球面上的场值
field = σDA(theta)*(1+ 3/2*(px*np.sin(phi)+py*np.cos(phi)) * Ay(theta) + 2/3 * (pxz*np.cos(phi)-pyz*np.sin(phi))*Axz(theta) + 1/6* ((pxx-pyy)*np.cos(2*phi)-2*pxy*np.sin(2*phi))*(Axx(theta)-Ayy(theta)) + 1/2*pzz*Azz(theta))


# 绘制球面上的场值图
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
P1 = ax.scatter(x, y, z, c=field, cmap='jet')
# 添加颜色条
fig.colorbar(P1)
plt.xlabel('x')
plt.ylabel('y')
plt.title('Polarized differential scattering cross-section')

plt.show()

# %% [markdown]
# 散射截面差值

# %%
px=0
py=0
pxz=0
pyz=0
pxx=0
pyy=0
pxy=0
pzz=1.0

# 定义球面上的坐标点
theta, phi = np.linspace(44/180*np.pi, 160/180*np.pi, 100), np.linspace(0, 2*np.pi, 100)
theta, phi = np.meshgrid(theta, phi)
x, y, z = np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)

# 计算球面上的场值 差值
field = σDA(theta)*(3/2*(px*np.sin(phi)+py*np.cos(phi)) * Ay(theta) + 2/3 * (pxz*np.cos(phi)-pyz*np.sin(phi))*Axz(theta) + 1/6* ((pxx-pyy)*np.cos(2*phi)-2*pxy*np.sin(2*phi))*(Axx(theta)-Ayy(theta)) + 1/2*pzz*Azz(theta))


# 绘制球面上的场值图
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
P1 = ax.scatter(x, y, z, c=field, cmap='jet')
# 添加颜色条
fig.colorbar(P1)
plt.xlabel('x')
plt.ylabel('y')
plt.title('diff')

plt.show()

# %%
px=0
py=0
pxz=0
pyz=0
pxx=0
pyy=1
pxy=0
pzz=0

# 定义球面上的坐标点
theta, phi = np.linspace(44/180*np.pi, 160/180*np.pi, 100), np.linspace(0, 2*np.pi, 100)
theta, phi = np.meshgrid(theta, phi)
x, y, z = np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)

# 计算球面上的场值 差值
# field = σDA(theta)*(3/2*(px*np.sin(phi)+py*np.cos(phi)) * Ay(theta) + 2/3 * (pxz*np.cos(phi)-pyz*np.sin(phi))*Axz(theta) + 1/6* ((pxx-pyy)*np.cos(2*phi)-2*pxy*np.sin(2*phi))*(Axx(theta)-Ayy(theta)) + 1/2*pzz*Azz(theta))
field = (3/2*(px*np.sin(phi)+py*np.cos(phi)) * Ay(theta) + 2/3 * (pxz*np.cos(phi)-pyz*np.sin(phi))*Axz(theta) + 1/6* ((pxx-pyy)*np.cos(2*phi)-2*pxy*np.sin(2*phi))*(Axx(theta)-Ayy(theta)) + 1/2*pzz*Azz(theta))



# 绘制球面上的场值图
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
P1 = ax.scatter(x, y, z, c=field, cmap='jet')
# 添加颜色条
fig.colorbar(P1)
plt.xlabel('x')
plt.ylabel('y')
plt.title('diff')

plt.show()

# %% [markdown]
# ## 转参考系

# %% [markdown]
# ### 非相对论情况
#
# $\theta_cm\text{:=}\sin ^{-1}\left(\frac{{m_D} \sin (\theta_{lab})}{{m_P}}\right)+\theta_{lab}$
#
# $sin(\theta_{cm}) d \theta_{cm} / (sin(\theta_{lab}) d \theta _{lab} )$
#
# $$\csc (\text{thetalab}) \sin \left(\sin ^{-1}\left(\frac{\text{mD} \sin (\text{thetalab})}{\text{mP}}\right)+\text{thetalab}\right) \left(\frac{\text{mD} \cos (\text{thetalab})}{\text{mP} \sqrt{1-\frac{\text{mD}^2 \sin ^2(\text{thetalab})}{\text{mP}^2}}}+1\right)$$

# %% [markdown]
# ### 相对论变化
#
#
#

# %%
mD = 1875.612
mP = 938
Ek = 380

# %%
import math


    
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



# %%
thetalab, phi = np.linspace(0.2, 0.5, 100), np.linspace(0, np.pi, 100)

sigamlab_values = [sigamlab(theta) for theta in thetalab]
TransTotheta_values = [TranToThetacm(theta) for theta in thetalab]
sigamtrans_values = [sigamtrans(theta) for theta in thetalab]



# %%
fig, ax = plt.subplots()
# 绘制函数图像
ax.plot(thetalab*180/np.pi, sigamlab_values )
# ax.plot(thetalab*180/np.pi, TransTotheta_values )
# ax.plot(thetalab*180/np.pi, sigamtrans_values )

# 添加坐标轴标签和标题
plt.xlabel(r'$\theta_{lab}$[deg]',fontsize=18)
plt.ylabel(r'$\frac{d \sigma}{d \Omega} $[mb/sr]',fontsize=18)
plt.title('Unpolarized differential scattering cross-section')
ax.yaxis.set_label_coords(-0.1, 0.5) # 设置标签位置
ax.set_yscale('log')

plt.show()



# %%
def Azzlab(thetalab):
    return Azz(TranToThetacm(thetalab))

def TranToThelabDeg(thetacmdeg):   
        thetacmrad=thetacmdeg*math.pi/180
        return math.atan((400.08 * math.sin(thetacmrad)) / (817.991 + 434.952 * math.cos(thetacmrad)))*180/math.pi



# %%
thetalab_values=[TranToThelabDeg(theta) for theta in T['θc.m.(deg)'].values[:15]]

# %%
plt.xlabel(r'$\theta_{lab}$[deg]',fontsize=18)
plt.ylabel('Analysing Power',fontsize=18)
# plt.errorbar(thetalab_values, np.sqrt(2) * T["T22"].values[:13],yerr =AzzErr[:13],label = 'Azz')
plt.errorbar(thetalab_values, np.sqrt(2) * T["T20"].values[:15],yerr =AzzErr[:15],label = 'Azz')
plt.legend()
plt.show()

# %%
plt.xlabel(r'$\theta_{lab}$[deg]',fontsize=18)
plt.ylabel('Analysing Power',fontsize=18)
# plt.errorbar(thetalab_values, np.sqrt(2) * T["T22"].values[:13],yerr =AzzErr[:13],label = 'Azz')
plt.errorbar([TranToThelabDeg(theta) for theta in T['θc.m.(deg)'].values[15:]], np.sqrt(2) * T["T20"].values[15:],yerr =AzzErr[15:],label = 'Azz')
plt.legend()
plt.show()

# %% [markdown]
#

# %%
plt.xlabel(r'$\theta_{lab}$[deg]',fontsize=18)
plt.ylabel('Analysing Power',fontsize=18)
# plt.errorbar(thetalab_values, np.sqrt(2) * T["T22"].values[:13],yerr =AzzErr[:13],label = 'Azz')
plt.errorbar([TranToThelabDeg(theta) for theta in T['θc.m.(deg)'].values[0:]], np.sqrt(2) * T["T20"].values[0:],yerr =AzzErr[0:],label = 'Azz')
plt.legend()
plt.show()

# %%

# %% [markdown]
# ## 计算计数率和显著性

# %%
dOmega = np.pi*(1/180*np.pi)**2
d=10000
MCH2=14
NA=6.02214076*10**23
I=1.6*10**-3*10**-9
e=1.602176634 *10**(-19)




# %% [markdown]
# 未极化时候，单个粒子散射概率：

# %%
Pzz=1
p_unPol=d/MCH2*NA*sigamlab(22/180*np.pi)*10**-31*dOmega*4
print(p_unPol)
p_Pol=d/MCH2*NA*sigamlab(22/180*np.pi)*10**-31*dOmega*4*(1+0.5*Pzz*Azzlab(22/180*np.pi))
print(p_Pol)
p_1over10Pol=d/MCH2*NA*sigamlab(22/180*np.pi)*10**-31*dOmega*4*(1+0.5*0.1*Azzlab(22/180*np.pi))
print(p_1over10Pol)
print(0.5*Pzz*Azzlab(22/180*np.pi))

# %% [markdown]
# 大数定理

# %%
N=I/e*3600*3
print('{:.2e}'.format(N))
print(I/e)

# %%
fangcha_unPol=N*p_unPol*(1-p_unPol)
fangcha_Pol=N*p_Pol*(1-p_Pol)
junzhi_unPol = N *p_unPol
junzhi_Pol=N*p_Pol
fangcha_1over10Pol=N*p_1over10Pol*(1-p_1over10Pol)
junzhi_1over10Pol = N *p_1over10Pol

print(junzhi_unPol)
print(junzhi_Pol)

# %%


n_unpol = np.linspace(junzhi_unPol - 3*np.sqrt(fangcha_unPol), junzhi_unPol + 3*np.sqrt(fangcha_unPol), 100)
y1 = 1/(np.sqrt(2*np.pi)*np.sqrt(fangcha_unPol))*np.exp(-(n_unpol-junzhi_unPol)**2/(2*np.sqrt(fangcha_unPol)**2))

# 第二个正态分布，均值为 2，方差为 2

n_Pol = np.linspace(junzhi_Pol - 3*np.sqrt(fangcha_Pol), junzhi_Pol + 3*np.sqrt(fangcha_Pol), 100)
y2 = 1/(np.sqrt(2*np.pi)*np.sqrt(fangcha_Pol))*np.exp(-(n_Pol-junzhi_Pol)**2/(2*np.sqrt(fangcha_Pol)**2))

n_1over10Pol= np.linspace(junzhi_1over10Pol - 3*np.sqrt(fangcha_1over10Pol), junzhi_1over10Pol + 3*np.sqrt(fangcha_1over10Pol), 100)
y3 = 1/(np.sqrt(2*np.pi)*np.sqrt(fangcha_1over10Pol))*np.exp(-(n_1over10Pol-junzhi_1over10Pol)**2/(2*np.sqrt(fangcha_1over10Pol)**2))
# 画图
plt.plot(n_unpol, y1, label='Pzz=0')
plt.plot(n_Pol, y2, label='Pzz=1')
plt.plot(n_1over10Pol, y3, label='Pzz=0.1')
plt.legend(loc='upper center')  # 将图例放置在中心位置
plt.title('The Distribution of Counts')
plt.xlabel('Counts')
plt.ylabel('Probability density')
plt.show()

# %% [markdown]
# 均值差：
# 3σ1+3σ2：分别是

# %%
print(junzhi_1over10Pol-junzhi_unPol)
print(3*np.sqrt(fangcha_1over10Pol)+3*np.sqrt(fangcha_unPol))

# %% [markdown]
# 23年12月3日画图

# %%
