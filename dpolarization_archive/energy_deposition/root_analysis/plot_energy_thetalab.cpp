#include <iostream>
#include <vector>
#include <utility>
#include <cmath>
#include <TLorentzVector.h>
#include <TVector3.h>
#include <TCanvas.h>
#include <TH2F.h>
#include "function.h"
#include <TGraph.h>
#include "globals.h"
#include <TBox.h>
#include <TLegend.h>


std::pair<TLorentzVector, TLorentzVector> P_lab(double theta_D_c, double phi_D_c);

int main() {

    initializeGlobals(); // 初始化全局变量

        const int n = 1000;


    double theta_D_c[n];
    double theta_D_lab[n];
    double theta_p_lab[n];
    double theta_D_c_deg[n];
    double theta_D_lab_deg[n];
    double theta_p_lab_deg[n];
    double E_D_lab[n];
    double E_p_lab[n];
    // 填充数据点
    for (int i = 0; i < n; i++) {
        theta_D_c[i] = i*M_PI/n; // 这里你需要根据实际情况设置theta_D_c的值
        auto result = P_lab(theta_D_c[i], 0.0);
        TLorentzVector P_lab_c_beforeCollision = result.first;

        theta_D_lab[i] = P_lab_c_beforeCollision.Theta();
        E_D_lab[i] = (P_lab_c_beforeCollision.E()-mD);
        std::cout << "E_D_lab: " << E_D_lab[i] << std::endl;  
        TLorentzVector P_p_lab_c_beforeCollision = result.second;

        theta_p_lab[i] =P_p_lab_c_beforeCollision.Theta();
        E_p_lab[i] = P_p_lab_c_beforeCollision.E()-mP; 
                // 打印phi角
        // std::cout << "Phi angle of P_lab_c_beforeCollision: " << P_lab_c_beforeCollision.Phi() << std::endl;
        // std::cout << "Phi angle of P_p_lab_c_beforeCollision: " << P_p_lab_c_beforeCollision.Phi() << std::endl;
     // 转换为度数
        theta_D_c_deg[i] = theta_D_c[i] * 180.0 / M_PI;
        theta_D_lab_deg[i] = theta_D_lab[i] * 180.0 / M_PI;
        theta_p_lab_deg[i] = theta_p_lab[i] * 180.0 / M_PI;
        
    }

    TGraph *gr1 = new TGraph(n, theta_D_lab_deg, E_D_lab);
    TGraph *gr2 = new TGraph(n, theta_p_lab_deg, E_p_lab);

    // 创建TCanvas对象并绘制图形
    TCanvas *c1 = new TCanvas("c1", "Energy vs #theta_{D_{lab}}", 800, 600);
    gr1->SetLineColor(kRed); // 设置第一个图形的线条颜色为红色
    gr1->SetTitle("Energy vs #theta_{D_{lab}}; #theta_{D_{lab}} (deg);Energy (MeV)");
           gr1->GetXaxis()->SetRangeUser(0, 80); // 手动设置X轴范围
    gr1->GetYaxis()->SetRangeUser(0, 400); // 手动设置Y轴范围
    gr2->SetLineColor(kBlue); // 设置第二个图形的线条颜色为蓝色
     gr2->Draw("AL"); 
    gr1->Draw("C SAME"); // "A"表示自动选择坐标轴的范围，"C"表示使用曲线连接数据点


// "C"表示使用曲线连接数据点，"SAME"表示在同一画布上绘制

    // // 设置X轴和Y轴的范围
    // gr1->GetXaxis()->SetRangeUser(0, 90);
    // gr1->GetYaxis()->SetRangeUser(0, 400); // 根据实际数据调整范围

    // 添加图例
    auto legend = new TLegend(0.65, 0.7, 0.9, 0.9);
    legend->AddEntry(gr1, "Deutron", "l");
    legend->AddEntry(gr2, "Proton", "l");
    legend->Draw();

    // 保存图形
    c1->SaveAs("Energy_vs_ThetaDc_deg.png");

    return 0;
}