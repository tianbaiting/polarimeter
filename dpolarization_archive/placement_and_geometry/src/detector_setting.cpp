// computing the energy of the deutron and proton in the lab frame
// 190MeV/u deutron beam


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
        E_D_lab[i] = (P_lab_c_beforeCollision.E()-mD)/2.0;
        // std::cout << "E_D_lab: " << E_D_lab[i] << std::endl;  
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
    // gr2->SetTitle("Energy vs #theta_{D_{lab}}; #theta_{D_{lab}} (deg);Energy (MeV/u)");
    gr2->SetTitle(" ; #theta_{lab} (deg);Energy (MeV/u)");


    gr2->SetLineColor(kBlue); // 设置第二个图形的线条颜色为蓝色
    gr2->Draw("AC"); // "C"表示使用曲线连接数据点，"SAME"表示在同一画布上绘制
    gr1->Draw("C SAME"); // "A"表示自动选择坐标轴的范围，"C"表示使用曲线连接数据点

    // gr2->SetLineColor(kBlue); // 设置第二个图形的线条颜色为蓝色
    // gr2->Draw("C SAME"); // "C"表示使用曲线连接数据点，"SAME"表示在同一画布上绘制

    // 设置X轴和Y轴的范围
    gr1->GetXaxis()->SetRangeUser(0, 90);
    gr1->GetYaxis()->SetRangeUser(0, 400); // 根据实际数据调整范围



    // 添加图例
    // auto legend = new TLegend(0.8, 0.7, 0.9, 0.9);
    TLegend *legend = new TLegend(0.7, 0.7, 0.9, 0.9); // 
    legend->AddEntry(gr1, "Deutron", "l");
    legend->AddEntry(gr2, "Proton", "l");
    legend->Draw();

        gr2->GetXaxis()->SetTitleSize(0.05);
        gr2->GetYaxis()->SetTitleSize(0.05);
        c1->SetLeftMargin(0.15);
        // c1->SetRightMargin(0.15);
        // c1->SetTopMargin(0.15);
        c1->SetBottomMargin(0.15);

        // designed scintillator 

        // double delta_theta_P_lab = width_p/distance_p*180/M_PI;
        double delta_theta_P1_lab = width_p1/distance_p*180/M_PI;
        double delta_theta_P2_lab = width_p2/distance_p*180/M_PI;

        double delta_theta_D_lab = width_D/distance_D*180/M_PI;

        double x1=P_lab(func_theta_P_cm((theta_p1_labdeg - delta_theta_P1_lab/2)*M_PI/180),0.0).second.E()-mP;
        double x2=P_lab(func_theta_P_cm((theta_p1_labdeg + delta_theta_P1_lab/2)*M_PI/180),0.0).second.E()-mP;
        TBox *box1 = new TBox(theta_p1_labdeg - delta_theta_P1_lab/2,x2, theta_p1_labdeg + delta_theta_P1_lab/2,x1);
        box1->SetFillColor(kCyan);
        box1->Draw("same");

        double x3=P_lab(func_theta_P_cm((theta_p2_labdeg - delta_theta_P2_lab/2)*M_PI/180),0.0).second.E()-mP;
        double x4=P_lab(func_theta_P_cm((theta_p2_labdeg + delta_theta_P2_lab/2)*M_PI/180),0.0).second.E()-mP;
        TBox *box2 = new TBox( theta_p2_labdeg - delta_theta_P2_lab/2, x3, theta_p2_labdeg + delta_theta_P2_lab/2,x4);
        box2->SetFillColor(kCyan);
        box2->Draw("same");
// Deutron
        double y1=P_lab(func_theta_D_c((theta_D_scin_labdeg - delta_theta_D_lab/2 )*M_PI/180).first,0.0).first.E()/2-mD/2;
        double y2=P_lab(func_theta_D_c((theta_D_scin_labdeg + delta_theta_D_lab/2 )*M_PI/180).first,0.0).first.E()/2-mD/2;
        TBox *box3 = new TBox( theta_D_scin_labdeg - delta_theta_D_lab/2,y1, theta_D_scin_labdeg + delta_theta_D_lab/2, y2);
        box3->SetFillColor(kPink);
        box3->Draw("same");

        double y3=P_lab(func_theta_D_c((theta_D_scin_labdeg - delta_theta_D_lab/2 )*M_PI/180).second,0.0).first.E()/2-mD/2;
        double y4=P_lab(func_theta_D_c((theta_D_scin_labdeg + delta_theta_D_lab/2 )*M_PI/180).second,0.0).first.E()/2-mD/2;
        TBox *box4 = new TBox(theta_D_scin_labdeg - delta_theta_D_lab/2,y3,  theta_D_scin_labdeg + delta_theta_D_lab/2, y4);
        box4->SetFillColor(kPink);
        box4->Draw("same");




    // 保存图形
    c1->SaveAs("Energy_vs_ThetaDc_deg.png");
    // c1->SaveAs("Energy_vs_ThetaDc_deg.eps");
    c1->SaveAs("Energy_vs_ThetaDc_deg.pdf");


    return 0;
}