// globals.cpp
#include "Rtypes.h"
#include "globals.h"
#include <cmath> // 包含数学库以使用 sqrt 和其他数学函数

Double_t mD = 1875.612;
Double_t mP = 938;
Double_t Ek = 380; // D核总动能
Double_t ED = mD + Ek;
// 氘核动量
Double_t pD = sqrt(ED * ED - mD * mD);

// 计算 beta
Double_t beta = sqrt((mD + Ek) * (mD + Ek) - mD * mD) / (mD + Ek + mP);

// 计算 gamma_me
Double_t gamma_me = 1.0 / sqrt(1 - beta * beta);

// 计算 EDCM, PDCM 和 EPCM
Double_t EDCM = gamma_me * (mD + Ek) - gamma_me * beta * sqrt((mD + Ek) * (mD + Ek) - mD * mD);
Double_t PDCM = -gamma_me * beta * (mD + Ek) + gamma_me * sqrt((mD + Ek) * (mD + Ek) - mD * mD);
Double_t EPCM = gamma_me * mP;

Double_t t_beamline= 180.0*60.0; // 30 minutes

// 厚度 10000 g/m^2 = 1000 mg/cm^2
double d_ch2 = 10000;
// 聚乙烯摩尔质量 g/mol
double MCH2 = 14;
// 阿伏伽德罗常数
double NA = 6.02214076e23;
// 束流 安培 pna：The electrical current in nanoamperes (10^{-9}A) that would be measured if all beam ions were singly charged. i.e. neglecting the actual charge state. 
double I = 1.6e-3 * 1e-9;
// 电子电荷
double e_q = 1.602176634e-19;

//记得修改 精算  
// double theta_p1_labdeg= 55.9;
double theta_p1_labdeg= 53.4;

double theta_p2_labdeg= 11.2;
double distance_p=620.0;
// double width_p=20.0; //theta p lab width
double width_p1=40.0; //theta p lab width
double width_p2=40.0; //theta p lab width
// double width_p_phi=20.0; //theta p  width
double width_p1_phi=40.0; //theta p  width
double width_p2_phi=40.0; //theta p  width



double theta_D_scin_labdeg=20.9;
double distance_D=400.0;
double width_D=40.0; // theta D lab width
double width_D_phi=40.0; //theta D cm width 确保phi叫大于质子的宽度

void initializeGlobals() {
    // 如果需要在程序运行时动态初始化全局变量，可以在这里进行
}