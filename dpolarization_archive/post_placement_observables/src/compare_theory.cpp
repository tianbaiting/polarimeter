#include "function.h"
#include "globals.h"

#include <fstream>
#include <iostream>
#include <TGraph.h>
#include <TCanvas.h>
#include <TAxis.h>
#include <cmath>
#include <sys/stat.h>
#include <sys/types.h>



int main() {
    initializeGlobals(); // 初始化全局变量

    int n = 180; // 数据点个数

    // TlorentzVector P_lab计算
    double theta_D_c[n];
    double theta_p_lab[n];
    double theta_D_lab[n];

    // 由d lab 反推 c，从而对比
    double theta_D_c_1[n];
    double theta_D_c_2[n];
    double theta_p_lab_1[n];
    double theta_p_lab_2[n];



    // 打开文件以写入数据
    std::ofstream outfile("../output_data/theta_compare.txt");

    // 检查文件是否成功打开
    if (!outfile.is_open()) {
        std::cerr << "无法打开文件 output_data/theta_compare.txt" << std::endl;
        return 1;
    }

    // 写入文件头
    outfile << "theta_D_c theta_D_lab theta_p_lab theta_D_c_1 theta_D_c_2 theta_p_lab_1" << std::endl;

    // 填充数据点
    for (int i = 0; i < n; i++) {
        theta_D_c[i] = i * M_PI / n; // 这里你需要根据实际情况设置theta_D_c的值
        auto result = P_lab(theta_D_c[i], 0.0);
        TLorentzVector P_lab_c_beforeCollision = result.first;

        theta_D_lab[i] = P_lab_c_beforeCollision.Theta();
        TLorentzVector P_p_lab_c_beforeCollision = result.second;

        theta_p_lab[i] = P_p_lab_c_beforeCollision.Theta();

        // 由d lab 反推 c，从而对比
        theta_D_c_1[i] = func_theta_D_c(theta_D_lab[i]).first;
        theta_D_c_2[i] = func_theta_D_c(theta_D_lab[i]).second;

        theta_p_lab_1[i] = func_theta_p_lab(theta_D_c_1[i]);
        // printf("theta_p_lab_1 %f\n", theta_p_lab_1[i]);

        // 将数据写入文件
        outfile << theta_D_c[i] << " " << theta_D_lab[i] << " " << theta_p_lab[i] << " "
                << theta_D_c_1[i] << " " << theta_D_c_2[i] << " " << theta_p_lab_1[i] << std::endl;
    }

    // 关闭文件
    outfile.close();


    

    return 0;
}