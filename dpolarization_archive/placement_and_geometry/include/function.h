// function.h
#ifndef FUNCTION_H
#define FUNCTION_H

#include <utility>
#include "TLorentzVector.h"

// 实验室系下DP散射后的动量
std::pair<TLorentzVector, TLorentzVector> P_lab(double theta_D_c, double phi_D_c);

// 实验室系下对应的氘核的两个质心散射角度
std::pair<double, double> func_theta_D_c(double theta_D_lab_rad);


// 实验室系对应的P的散射角度
double func_theta_p_lab(double theta_D_c_rad);
//  质心系下P的散射角度
double func_theta_P_cm(double theta_p_lab);




#endif // FUNCTION_H