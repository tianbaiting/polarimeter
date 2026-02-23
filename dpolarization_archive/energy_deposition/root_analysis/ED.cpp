#include <cmath>
#include <sys/stat.h>
#include <sys/types.h>
#include <vector>
#include <iostream>
#include "TCanvas.h"
#include "TGraph.h"
#include "TLorentzVector.h"
#include "globals.h"
#include "TAxis.h"
// 假设这个函数在其他地方定义
std::pair<TLorentzVector, TLorentzVector> P_lab(double theta_D_c, double phi);

int main() {
    initializeGlobals(); // 初始化全局变量

    double theta_Dc = 68.6/180*M_PI;
    double theta_Dc_2 = 111.4/180*M_PI;
    auto result1 = P_lab(theta_Dc, 0.0);
    auto result2 = P_lab(theta_Dc_2, 0.0);
    double E_68_D = result1.first.E()-mD;
    double E_156_D = result2.first.E()-mD;

    double E_68_P = result1.second.E()-mP;
    double E_156_P = result2.second.E()-mP;
    std::cout << "E_68_D: " << E_68_D << std::endl;
    std::cout << "E_156_D: " << E_156_D << std::endl;
    std::cout << "E_68_P: " << E_68_P << std::endl;
    std::cout << "E_156_P: " << E_156_P << std::endl;

    std::cout<< "ED" << ED << std::endl;
    return 0;



//计算最佳角度68.6度，  同个实验室系角度会有多个质心角。

// 计算这两个质心角度的能量
}