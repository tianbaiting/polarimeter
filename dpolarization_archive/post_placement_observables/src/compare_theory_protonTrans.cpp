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

    double theta_Dc[n];
    double theta_plab[n];
    double theta_Pcm[n];



    // 打开文件以写入数据
    std::ofstream outfile("./output_data/theta_compare_proton_trans.txt");

    // 检查文件是否成功打开
    if (!outfile.is_open()) {
        std::cerr << "无法打开文件 output_data/theta_compare_proton_trans.txt" << std::endl;
        return 1;
    }

    // 写入文件头
    outfile << "theta_Dc theta_plab theta_pcm" << std::endl;

    for (int i = 0; i < n; i++)
    {
       theta_Dc[i] = i * M_PI / n; 
       theta_plab[i] = func_theta_p_lab(theta_Dc[i]);
       theta_Pcm[i] = func_theta_P_cm(theta_plab[i]);

       outfile << theta_Dc[i]*180/M_PI << " " << theta_plab[i]*180/M_PI  << " " << theta_Pcm[i] *180/M_PI << " "<< std::endl;
    }
    

    // 关闭文件
    outfile.close();


    

    return 0;
}