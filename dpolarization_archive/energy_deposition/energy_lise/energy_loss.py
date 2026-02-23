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

# %% [markdown]
# ## 如何将 function.h 编译为 so 动态库
#
# 1. 编写 function.cpp，实现 function.h 中声明的函数。
# 2. 使用 g++ 编译为共享库（假设你的函数实现文件为 function.cpp）：
#
# ```bash
# g++ -fPIC -shared -o function.so function.cpp
# ```
#
# 3. 编译时如有依赖 ROOT，请加上 `root-config` 相关参数：
#
# ```bash
# g++ -fPIC -shared -o function.so function.cpp `root-config --cflags --libs`
# ```
#
# 4. 编译完成后，`function.so` 即为可在 Python 中通过 ROOT 加载的动态库。

# %%
# 假设 function.h 已经被封装为 Python 可调用的模块（如 function.py），否则需用 C++/ROOT 绑定
# 这里以 Python 伪代码演示调用方式

# from function import lab_to_dp_angle_energy

# 示例：输入实验室系角度，输出D、p的实验室系角度和能量
# lab_angle = 30  # 例如30度



# 伪代码调用
# d_angle, p_angle, d_energy, p_energy = lab_to_dp_angle_energy(lab_angle)

# print(f"D粒子角度: {d_angle} 度, 能量: {d_energy} MeV")
# print(f"p粒子角度: {p_angle} 度, 能量: {p_energy} MeV")

# 如果只能用C++，可用ROOT的gSystem.Load和gInterpreter.ProcessLine调用C++函数
# import ROOT

# ROOT.gSystem.Load("function.so")  # 假设已编译为so库
# ROOT.gInterpreter.ProcessLine('auto result = lab_to_dp_angle_energy(30);')
# print(result)

# %%
import numpy as np

# 物理常量
mD = 1875.612
mP = 938.0
mC = 12.011 * 931.5
Ek = 380.0  # D核总动能
ED = mD + Ek
pD = np.sqrt(ED ** 2 - mD ** 2)

# 计算 beta
beta = np.sqrt((mD + Ek) ** 2 - mD ** 2) / (mD + Ek + mP)
beta_DC = np.sqrt((mD + Ek) ** 2 - mD ** 2) / (mD + Ek + mC)
# 计算 gamma_me
gamma_me = 1.0 / np.sqrt(1 - beta ** 2)
gamma_me_DC = 1.0 / np.sqrt(1 - beta_DC ** 2)

# 计算 EDCM, PDCM 和 EPCM
EDCM = gamma_me * (mD + Ek) - gamma_me * beta * np.sqrt((mD + Ek) ** 2 - mD ** 2)
PDCM = -gamma_me * beta * (mD + Ek) + gamma_me * np.sqrt((mD + Ek) ** 2 - mD ** 2)
EPCM = gamma_me * mP

t_beamline = 180.0 * 60.0  # 30 minutes

d_ch2 = 10000.0
MCH2 = 14.0
NA = 6.02214076e23
I = 1.6e-3 * 1e-9
e_q = 1.602176634e-19

theta_p1_labdeg = 55.9
theta_p2_labdeg = 11.3
distance_p = 600.0
width_p1 = 40.0
width_p2 = 40.0
width_p1_phi = 20.0
width_p2_phi = 20.0

theta_D_scin_labdeg = 20.87
distance_D = 500.0
width_D = 50.0
width_D_phi = 40.0

def initialize_globals():
    # 如果需要在程序运行时动态初始化全局变量，可以在这里进行
    pass

def func_theta_D_c(theta_D_lab_rad):
    tan_theta = np.tan(theta_D_lab_rad)
    gamma_me_tan_theta = gamma_me * tan_theta
    sqrt_term = np.sqrt(1 + gamma_me ** 2 * tan_theta ** 2)
    arcsin_term = np.arcsin((tan_theta * gamma_me * beta * EDCM) / (PDCM * sqrt_term))
    theta_D_c_1 = np.arctan(gamma_me_tan_theta) + arcsin_term
    theta_D_c_2 = np.arctan(gamma_me_tan_theta) + np.pi - arcsin_term
    return theta_D_c_1, theta_D_c_2

def func_theta_p_lab(theta_D_c_rad):
    sin_theta = np.sin(theta_D_c_rad)
    cos_theta = np.cos(theta_D_c_rad)
    numerator = PDCM * sin_theta
    denominator = gamma_me * beta * EPCM - gamma_me * PDCM * cos_theta
    theta_p_lab_rad = np.arctan(numerator / denominator)
    return theta_p_lab_rad

def func_theta_P_cm(theta_p_lab):
    tan_theta = np.tan(theta_p_lab)
    gamma_me_tan_theta = gamma_me * tan_theta
    sqrt_term = np.sqrt(1 + gamma_me ** 2 * tan_theta ** 2)
    arcsin_term = np.arcsin((tan_theta * gamma_me * beta * EPCM) / (PDCM * sqrt_term))
    theta_p_cm = np.pi - (np.arctan(gamma_me_tan_theta) + arcsin_term)
    return theta_p_cm



# %%
import numpy as np

class LorentzVector:
    def __init__(self, px=0, py=0, pz=0, E=0):
        self.px = px
        self.py = py
        self.pz = pz
        self.E = E

    def __add__(self, other):
        return LorentzVector(
            self.px + other.px,
            self.py + other.py,
            self.pz + other.pz,
            self.E + other.E
        )

    def boost(self, beta_vec):
        # beta_vec: 3-vector
        bx, by, bz = beta_vec
        b2 = bx**2 + by**2 + bz**2
        gamma = 1.0 / np.sqrt(1 - b2)
        bp = bx*self.px + by*self.py + bz*self.pz
        gamma2 = (gamma - 1.0)/b2 if b2 > 0 else 0.0

        px_ = self.px + gamma2*bp*bx + gamma*bx*self.E
        py_ = self.py + gamma2*bp*by + gamma*by*self.E
        pz_ = self.pz + gamma2*bp*bz + gamma*bz*self.E
        E_  = gamma*(self.E + bp)
        self.px, self.py, self.pz, self.E = px_, py_, pz_, E_

    def set_theta_phi(self, theta, phi):
        p = np.sqrt(self.px**2 + self.py**2 + self.pz**2)
        self.px = p * np.sin(theta) * np.cos(phi)
        self.py = p * np.sin(theta) * np.sin(phi)
        self.pz = p * np.cos(theta)

    def p(self):
        return np.sqrt(self.px**2 + self.py**2 + self.pz**2)

    def __repr__(self):
        return f"LorentzVector(px={self.px}, py={self.py}, pz={self.pz}, E={self.E})"

def P_lab(theta_D_c, phi_D_c):
    # 初始四动量
    P_pro_lab_before = LorentzVector(0, 0, 0, mP)
    P_D_lab_before = LorentzVector(0, 0, pD, ED)
    P_total_lab = P_pro_lab_before + P_D_lab_before

    # boost到质心系
    beta_z = P_total_lab.pz / P_total_lab.E
    boost_vec = np.array([0, 0, beta_z])

    # 质心系下四动量
    P_pro_c = LorentzVector(P_pro_lab_before.px, P_pro_lab_before.py, P_pro_lab_before.pz, P_pro_lab_before.E)
    P_D_c = LorentzVector(P_D_lab_before.px, P_D_lab_before.py, P_D_lab_before.pz, P_D_lab_before.E)
    P_pro_c.boost(-boost_vec)
    P_D_c.boost(-boost_vec)

    # 旋转
    P_pro_c.set_theta_phi(np.pi - theta_D_c, np.pi + phi_D_c)
    P_D_c.set_theta_phi(theta_D_c, phi_D_c)

    # boost回实验室系
    P_pro_c.boost(boost_vec)
    P_D_c.boost(boost_vec)

    return P_D_c, P_pro_c

def P_lab_DCarbon(theta_D_c, phi_D_c):
    # 初始四动量
    P_carbon_lab_before = LorentzVector(0, 0, 0, mC)
    P_D_lab_before = LorentzVector(0, 0, pD, ED)
    P_total_lab = P_carbon_lab_before + P_D_lab_before

    # boost到质心系
    beta_z = P_total_lab.pz / P_total_lab.E
    boost_vec = np.array([0, 0, beta_z])

    # 质心系下四动量
    P_carbon_c = LorentzVector(P_carbon_lab_before.px, P_carbon_lab_before.py, P_carbon_lab_before.pz, P_carbon_lab_before.E)
    P_D_c = LorentzVector(P_D_lab_before.px, P_D_lab_before.py, P_D_lab_before.pz, P_D_lab_before.E)
    P_carbon_c.boost(-boost_vec)
    P_D_c.boost(-boost_vec)

    # 旋转
    P_carbon_c.set_theta_phi(np.pi - theta_D_c, np.pi + phi_D_c)
    P_D_c.set_theta_phi(theta_D_c, phi_D_c)

    # boost回实验室系
    P_carbon_c.boost(boost_vec)
    P_D_c.boost(boost_vec)

    return P_D_c, P_carbon_c
    


# %%

# %%
import matplotlib.pyplot as plt
# x: theta lab
# y : theta_D cm theta_p cm
def plot_theta_cm_vs_lab(theta_lab_range):
    theta_D_cm = []
    theta_D_cm_2 = []
    theta_p_cm = []

    for theta_lab in theta_lab_range:
        theta_D_c_1, theta_D_c_2 = func_theta_D_c(np.radians(theta_lab))
        theta_D_cm.append(np.degrees(theta_D_c_1))
        theta_D_cm_2.append(np.degrees(theta_D_c_2)) 
        theta_p_cm_rad = func_theta_P_cm(np.radians(theta_lab))
        theta_p_cm.append(np.degrees(theta_p_cm_rad))

    plt.figure(figsize=(10, 6))
    plt.plot(theta_lab_range, theta_D_cm, label='Theta D cm', color='blue')
    plt.plot(theta_lab_range, theta_D_cm_2, label='Theta D cm', color='blue')
    plt.plot(theta_lab_range, theta_p_cm, label='Theta p cm', color='red')
    plt.xlabel('Theta Lab (degrees)')
    plt.ylabel('Theta CM (degrees)')
    plt.title('Theta CM vs Theta Lab')
    plt.legend()
    plt.grid()
    plt.show()
plot_theta_cm_vs_lab(np.linspace(0,89, 100))


# %%
# 如果未安装 matplotlib，可以先运行此单元格安装
# # %pip install matplotlib

# %%
import matplotlib.pyplot as plt

# 以实验室系角度 theta_Lab 为横坐标，能量为纵坐标
theta_lab_deg = np.linspace(0.1, 89.0, 300)  # 角度范围可根据实际需求调整
theta_lab_rad = np.deg2rad(theta_lab_deg)

# 计算 D 粒子在实验室系下的能量
theta_D_c_1, theta_D_c_2 = func_theta_D_c(theta_lab_rad)
# 取第一个解
theta_D_c = theta_D_c_1

# 计算 D 粒子在实验室系下的能量（theta_D_c_1）
E_D_lab_1 = []
for th_c in theta_D_c_1:
    if np.isnan(th_c):
        E_D_lab_1.append(np.nan)
    else:
        P_D, _ = P_lab(th_c, 0)
        E_D_lab_1.append(P_D.E)
E_D_lab_1 = np.array(E_D_lab_1)

# 计算 D 粒子在实验室系下的能量（theta_D_c_2）
E_D_lab_2 = []
for th_c in theta_D_c_2:
    if np.isnan(th_c):
        E_D_lab_2.append(np.nan)
    else:
        P_D, _ = P_lab(th_c, 0)
        E_D_lab_2.append(P_D.E)
E_D_lab_2 = np.array(E_D_lab_2)

# 计算 p 粒子在质心系下的角度
theta_p_cm = func_theta_P_cm(theta_lab_rad)


E_p_lab = []
for th_c in theta_p_cm:
    if np.isnan(th_c):
        E_p_lab.append(np.nan)
    else:
        _, P_p = P_lab(th_c, 0)
        E_p_lab.append(P_p.E)


# 计算 p 粒子在实验室系下的能量


plt.figure(figsize=(8, 5))
plt.plot(theta_lab_deg, E_D_lab_1, label="Deuteron Energy (theta_D_c_1)")
plt.plot(theta_lab_deg, E_D_lab_2, label="Deuteron Energy (theta_D_c_2)")
plt.plot(theta_lab_deg, E_p_lab, '--', label="Proton Energy ")
plt.xlabel("Lab Angle θ_lab (deg)")
plt.ylabel("Energy (MeV)")
plt.title("Lab Angle vs Deuteron/Proton Energy")
plt.legend()
plt.grid(True)
plt.show()

# %% [markdown]
# 上面是总能量。 而非动能。

# %%
plt.figure(figsize=(8, 5))
plt.plot(theta_lab_deg, E_D_lab_1, label="Deuteron Energy (theta_D_c_1)")
plt.plot(theta_lab_deg, E_D_lab_2, label="Deuteron Energy (theta_D_c_2)")
plt.plot(theta_lab_deg, E_p_lab, '--', label="Proton Energy ")
plt.xlabel("Lab Angle θ_lab (deg)")
plt.ylabel("Energy (MeV)")
plt.title("Lab Angle vs Deuteron/Proton Energy")
plt.legend()
plt.grid(True)
plt.show()

# %%
# 需要安装 numpy、matplotlib、scipy、pandas
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

def gEdEdxLISE(inputFile):
    # 跳过前三行，读取数据
    df = pd.read_csv(inputFile, delim_whitespace=True, skiprows=3, header=None)
    # energy = 第一列，R[4] = 第九列（下标8）
    energy = df[0].values
    dEdx = df[8].values
    # 返回插值函数
    return interp1d(energy, dEdx, kind='linear', fill_value="extrapolate")

def eloss(A, E0_A, dx, gER, gRE):
    E0 = E0_A * A
    dE = 0
    RE0 = gER(E0 / A)
    if RE0 > dx:
        RE1 = RE0 - dx
        E1 = gRE(RE1)
        dE = E0 - E1 * A
    else:
        dE = E0
    return dE

# 示例主程序
def main():
    # 读取能量-射程关系
    df = pd.read_csv("H_c8h8_range.txt", delim_whitespace=True, skiprows=3, header=None)
    energy = df[0].values
    R = df[1].values  # 假设R[0]在第2列
    # 构建插值函数
    gER = interp1d(energy, R, kind='linear', fill_value="extrapolate")
    gRE = interp1d(R, energy, kind='linear', fill_value="extrapolate")

    E0_A_min = 0
    E0_A_max = 200
    step = 1

    E0_A_values = np.arange(E0_A_min, E0_A_max + step, step)
    eloss_values = []
    eloss_values2 = []

    for E0_A in E0_A_values:
        dE = eloss(1, E0_A, 20000, gER, gRE)
        E2 = E0_A - eloss(1, E0_A, 20000, gER, gRE)
        dE2 = eloss(1, E2, 20000, gER, gRE)
        eloss_values.append(dE)
        eloss_values2.append(dE2)

    plt.figure(figsize=(10, 6))
    plt.plot(E0_A_values, eloss_values, color='red', label='1st scintillator')
    plt.plot(E0_A_values, eloss_values2, color='blue', label='2nd scintillator')
    plt.title('eloss vs E0')
    plt.xlabel('E0 (MeV/u)')
    plt.ylabel('Delta E (MeV)')
    plt.legend()
    plt.savefig('eloss.png')
    plt.show()

if __name__ == "__main__":
    main()

# %%
# 计算氘核和质子在实验室系下的能量，10mm的能损
df = pd.read_csv("2H_c8h8_range_MeV_um.txt", delim_whitespace=True, skiprows=3, header=None)
energy = df[0].values
R = df[1].values  # 假设R[0]在第2列S
# 构建插值函数
gER = interp1d(energy, R, kind='linear', fill_value="extrapolate")
gRE = interp1d(R, energy, kind='linear', fill_value="extrapolate")
# 计算 p 粒子在质心系下的角度
theta_p_cm = func_theta_P_cm(theta_lab_rad)

E_p_lab = []
Ep_kin_peru = []
dEp = []
dEp_20mm = []
for th_c in theta_p_cm:
    if np.isnan(th_c):
        E_p_lab.append(np.nan)
    else:
        _, P_p = P_lab(th_c, 0)
        E_p_lab.append(P_p.E)
        Ep_kin_peru.append(P_p.E - mP)
        dEp.append( eloss(1, P_p.E - mP, 10000, gER, gRE) )
        dEp_20mm.append( eloss(1, P_p.E - mP, 20000, gER, gRE) )
# 绘制质子能量与角度的关系dEp vs thetalab
plt.figure(figsize=(8, 5))
plt.plot(theta_lab_deg, dEp, label="Proton dE (10mm CH2)", color='green')
plt.xlabel("Lab Angle θ_lab (deg)")
plt.ylabel("Proton Energy Loss dE (MeV)")
plt.title("Proton Energy Loss vs Lab Angle (10mm CH2)")
plt.legend()
plt.grid(True)
plt.show()


# %%
# 计算氘核在实验室系下的能量，10mm的能损
d_df = pd.read_csv("2H_c8h8_range_MeV_um.txt", delim_whitespace=True, skiprows=3, header=None)
d_energy = d_df[0].values
d_R = d_df[1].values  # 假设R[0]在第2列
# 构建插值函数
d_gER = interp1d(d_energy, d_R, kind='linear', fill_value="extrapolate")
d_gRE = interp1d(d_R, d_energy, kind='linear', fill_value="extrapolate")
# 计算 p 粒子在质心系下的角度
theta_p_cm = func_theta_P_cm(theta_lab_rad)


E_D_lab = []
ED_kin_peru = []
dED = []
for th_c in theta_D_c_1:
    if np.isnan(th_c):
        dED.append(np.nan)
        ED_kin_peru.append(np.nan)
    else:
        P_D, _ = P_lab(th_c, 0)
        E_D_lab.append(P_D.E)
        ED_kin_peru.append((P_D.E - mD)/2.0)
        dED.append( eloss(2, (P_D.E - mD)/2.0, 10000, d_gER, d_gRE) )

E_D_lab2 = []
ED_kin_peru2 = []
dED2 = []
for th_c in theta_D_c_2:
    if np.isnan(th_c):
        dED2.append(np.nan)
        ED_kin_peru2.append(np.nan)
    else:
        P_D2, _ = P_lab(th_c, 0)
        E_D_lab2.append(P_D2.E)
        ED_kin_peru2.append((P_D2.E - mD)/2.0)
        dED2.append( eloss(2, (P_D2.E - mD)/2.0, 10000, d_gER, d_gRE) )

# 绘制质子能量与角度的关系d_dEp vs thetalab
plt.figure(figsize=(8, 5))
plt.plot(theta_lab_deg, dED, label="Deuteron dE (10mm C8H8)", color='green')
plt.plot(theta_lab_deg, dED2, label="Deuteron dE (10mm C8H8)", color='green')

plt.xlabel("Lab Angle θ_lab (deg)")
plt.ylabel("Deuteron Energy Loss dE (MeV)")
plt.title("Deuteron Energy Loss vs Lab Angle (10mm C8H8)")
plt.legend()
plt.grid(True)
plt.show()

# %%
print(np.array(ED_kin_peru2).shape)
print(np.array(theta_lab_deg).shape)
print(np.array(E_D_lab_1).shape)
print(np.array(dED2).shape)
print(np.array(E_D_lab2).shape)
print(np.array(theta_D_c_2).shape)
print(np.array(theta_D_c_1).shape)
print(np.array(Ep_kin_peru).shape)





plt.figure(figsize=(8, 5))
plt.plot(theta_lab_deg, ED_kin_peru2, label="Deuteron", color='green')
plt.plot(theta_lab_deg, ED_kin_peru, label="Deuteron", color='green')

plt.xlabel("Lab Angle θ_lab (deg)")
plt.ylabel("Deuteron kin (MeV/u)")
plt.title(" Deuteron Kinetic Energy vs Lab Angle ")
plt.legend()
plt.grid(True)
plt.show()

# %%
plt.figure(figsize=(8, 5))
plt.plot(theta_lab_deg, dED, label="Deuteron dE (10mm C8H8,dp_scatering)", color='green')
plt.plot(theta_lab_deg, dED2, label="Deuteron dE (10mm C8H8,dp_scatering)", color='green')
plt.plot(theta_lab_deg, dEp, label="Proton dE (10mm C8H8,dp_scatering)", color='blue')
plt.plot(theta_lab_deg, dEp_20mm, label="Proton dE (20mm C8H8,dp_scatering)", color='red')
plt.xlabel("Lab Angle θ_lab (deg)")
plt.ylabel("Deuteron Energy Loss dE (MeV)")
plt.title("Deuteron Energy Loss vs Lab Angle (10mm C8H8)")
plt.legend()
plt.grid(True)
plt.show()

# %%
theta_Dcarbon_c_rad = np.linspace(0.1, 3.14, 300)  # 角度范围可根据实际需求调整
P_D_lab, P_C_lab = P_lab_DCarbon(theta_Dcarbon_c_rad, 0)
theta_DC_Deutronlab = np.degrees(np.arctan2(P_D_lab.px, P_D_lab.pz))
theta_DC_Carbonlab = np.degrees(np.arctan2(P_C_lab.px, P_C_lab.pz))



plt.figure(figsize=(8, 5))
plt.plot(theta_Dcarbon_c_rad, theta_DC_Deutronlab, label="Deutron labtheta", color='green')
plt.plot(theta_Dcarbon_c_rad, -theta_DC_Carbonlab, label="Carbon labtheta", color='blue')
plt.xlabel(" θ_c (rad)")
plt.ylabel("θ_lab (deg)")
plt.legend()
plt.grid(True)
plt.show()

# %%
carborn_df = pd.read_csv("2H_c8h8_range_MeV_um.txt", delim_whitespace=True, skiprows=3, header=None)
carborn_energy = carborn_df[0].values
carborn_R = carborn_df[1].values  # 假设R[0]在第2列
carborn_gER = interp1d(carborn_energy, carborn_R, kind='linear', fill_value="extrapolate")
carborn_gRE = interp1d(carborn_R, carborn_energy, kind='linear', fill_value="extrapolate")

# %%
# Eloss_carbon = []
# Eloss_Deutron_DCarborn = []
Eloss_carbon = [
    eloss(12, (E - mC)/2.0, 10000, carborn_gER, carborn_gRE)
    for E in np.atleast_1d(P_C_lab.E)
]
Eloss_Deutron_DCarborn = [
    eloss(2, (E - mD)/2.0, 10000, d_gER, d_gRE)
    for E in np.atleast_1d(P_D_lab.E)
]


plt.figure(figsize=(8, 5))
plt.plot(theta_DC_Deutronlab, Eloss_carbon, label="Carbon Eloss (10mm C8H8)", color='blue')
plt.plot(-theta_DC_Carbonlab, Eloss_Deutron_DCarborn, label="Deuteron Eloss (10mm C8H8)", color='green')
plt.xlabel(" θ_c (deg)")    
plt.ylabel("Energy Loss (MeV)")
plt.title("Energy Loss vs θ_c (Deuteron and Carbon)")
plt.legend()
plt.grid(True)
plt.show()

# %%
plt.figure(figsize=(8, 5))
# plt.plot(theta_DC_Deutronlab, Eloss_carbon, label="Carbon Eloss (10mm C8H8)", color='blue')
plt.plot(-theta_DC_Carbonlab, Eloss_Deutron_DCarborn, label="Deuteron Eloss (10mm C8H8)", 
         color='green')

plt.xlabel(" θ_c (deg)")    
plt.ylabel("Energy Loss (MeV)")
plt.title("Energy Loss vs θ_c (Deuteron and Carbon)")
plt.legend()
plt.grid(True)
plt.show()

# %%
plt.figure(figsize=(8, 5))
plt.plot(theta_lab_deg, dED, label="Deuteron dE (10mm C8H8,dp_scatering)", color='green')
plt.plot(theta_lab_deg, dED2, label="Deuteron dE (10mm C8H8,dp_scatering)", color='green')
plt.plot(theta_lab_deg, dEp, label="Proton dE (10mm C8H8,dp_scatering)", color='blue')
plt.plot(theta_lab_deg, dEp_20mm, label="Proton dE (20mm C8H8,dp_scatering)", color='red')
plt.plot(theta_DC_Deutronlab, Eloss_carbon, label="Carbon Eloss (10mm C8H8),DC_scaterring", color='blue')
plt.plot(-theta_DC_Carbonlab, Eloss_Deutron_DCarborn, label="Deuteron Eloss (10mm C8H8),DC_scaterring", color='blue')
plt.xlabel("Lab Angle θ_lab (deg)")
plt.ylabel(" Loss dE (MeV)")
plt.title("Energy Loss vs Lab Angle (10mm C8H8)")
plt.legend()
plt.grid(True)
plt.show()

# %%
plt.figure(figsize=(8, 5))
plt.plot(theta_lab_deg, dED, label="Deuteron dE (10mm C8H8,dp_scattering)", color='green')
plt.plot(theta_lab_deg, dED2, label="Deuteron dE (10mm C8H8,dp_scattering)", color='green', linestyle='--')
plt.plot(theta_lab_deg, dEp, label="Proton dE (10mm C8H8,dp_scattering)", color='blue')
plt.plot(theta_lab_deg, dEp_20mm, label="Proton dE (20mm C8H8,dp_scattering)", color='orange')
# plt.plot(theta_DC_Deutronlab, Eloss_carbon, label="Carbon Eloss (10mm C8H8),DC_scattering", color='red')
plt.plot(-theta_DC_Carbonlab, Eloss_Deutron_DCarborn, label="Deuteron Eloss (10mm C8H8),DC_scattering", color='purple')
plt.xlabel("Lab Angle θ_lab (deg)")
plt.ylabel("Loss dE (MeV)")
plt.title("Energy Loss vs Lab Angle (10mm C8H8)")
plt.legend()
plt.grid(True)
plt.show()

# %%
plt.figure(figsize=(8, 5))
plt.plot(theta_lab_deg, np.degrees(theta_D_c_1), label='Theta D cm, dp scatter', color='green')
plt.plot(theta_lab_deg, np.degrees(theta_D_c_2), color='green')
plt.plot(theta_lab_deg, np.degrees(theta_p_cm), label='Theta p cm, dp scatter', color='red')
plt.plot(np.degrees(theta_Dcarbon_c_rad), theta_DC_Deutronlab, label="Deuteron labtheta, DC scatter", color='orange')
plt.plot(np.degrees(theta_Dcarbon_c_rad), -theta_DC_Carbonlab, label="Carbon labtheta, DC scatter", color='blue')

plt.axvspan(theta_D_scin_labdeg - np.degrees(width_D/distance_D)/2, theta_D_scin_labdeg + np.degrees(width_D/distance_D)/2, color='yellow', alpha=0.3)
plt.axvspan(theta_p1_labdeg - np.degrees(width_p1/distance_p)/2, theta_p1_labdeg + np.degrees(width_p1/distance_p)/2, color='cyan', alpha=0.3)
plt.axvspan(theta_p2_labdeg - np.degrees(width_p2/distance_p)/2, theta_p2_labdeg + np.degrees(width_p2/distance_p)/2, color='magenta', alpha=0.3)

plt.xlabel('Theta Lab (degrees)')
plt.ylabel('Theta CM (degrees)')
plt.title('Theta CM vs Theta Lab')
plt.legend()
plt.grid()
plt.show()

# %%
plt.figure(figsize=(8, 5))
plt.plot(theta_lab_deg, dED, label="Deuteron dE (10mm C8H8,dp_scattering)", color='green')
plt.plot(theta_lab_deg, dED2, label="Deuteron dE (10mm C8H8,dp_scattering)", color='green')
plt.plot(theta_lab_deg, dEp, label="Proton dE (10mm C8H8,dp_scattering)", color='blue')
# plt.plot(theta_lab_deg, dEp_20mm, label="Proton dE (20mm C8H8,dp_scattering)", color='orange')
plt.plot(theta_DC_Deutronlab, Eloss_carbon, label="Carbon Eloss (10mm C8H8),DC_scattering", color='red')
plt.plot(-theta_DC_Carbonlab, Eloss_Deutron_DCarborn, label="Deuteron Eloss (10mm C8H8),DC_scattering", color='purple')


plt.axvspan(theta_D_scin_labdeg - np.degrees(width_D/distance_D)/2, theta_D_scin_labdeg + np.degrees(width_D/distance_D)/2, color='yellow', alpha=0.3)
plt.axvspan(theta_p1_labdeg - np.degrees(width_p1/distance_p)/2, theta_p1_labdeg + np.degrees(width_p1/distance_p)/2, color='cyan', alpha=0.3)
plt.axvspan(theta_p2_labdeg - np.degrees(width_p2/distance_p)/2, theta_p2_labdeg + np.degrees(width_p2/distance_p)/2, color='magenta', alpha=0.3)

plt.xlabel("Lab Angle θ_lab (deg)")
plt.ylabel("Loss dE (MeV)")
plt.title("Energy Loss vs Lab Angle (10mm C8H8)")
plt.legend()
plt.grid(True)
plt.show()
