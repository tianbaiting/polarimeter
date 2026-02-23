//  Description: 本程序用于计算两个探测器的角度分布比值
// 计算的是氘核覆盖的两个区域内计数的比例

#include <iostream>
#include <fstream>
#include <vector>
#include <math.h>
#include <string>
#include <TSpline.h>
#include <TGraphErrors.h>
#include <TCanvas.h>
#include <TAxis.h>
#include <TApplication.h>
#include "function.h"
#include "globals.h"
#include <TGaxis.h>
// 读取cross_section数据文件
void readCrossData(const std::string& filename, std::vector<double>& angles, std::vector<double>& crossSections) {
    std::ifstream infile(filename);
    if (!infile.is_open()) {
        std::cerr << "无法打开文件 " << filename << std::endl;
        return;
    }

    std::string line;
    // 跳过前几行
    for (int i = 0; i < 5; ++i) {
        std::getline(infile, line);
    }

    double angle, crossSection;
    while (infile >> angle >> crossSection) {
        angles.push_back(angle);
        crossSections.push_back(crossSection);
    }

    infile.close();
}


// 读取数据文件
void readT20Data(const std::string& filename, std::vector<double>& angles, std::vector<double>& T20, std::vector<double>& deltaT20) {
    std::ifstream infile(filename);
    if (!infile.is_open()) {
        std::cerr << "无法打开文件 " << filename << std::endl;
        return;
    }

    std::string line;
    // 跳过文件头
    std::getline(infile, line);

    double angle, t20, dt20;
    std::string dummy;
    while (infile >> angle >> dummy >> dummy >> t20 >> dt20 >> dummy >> dummy >> dummy >> dummy) {
        if (dummy != "null") {
            angles.push_back(angle);
            T20.push_back(t20);
            deltaT20.push_back(dt20);
        }
    }

    infile.close();
}
//



// 返回给定角度的值
double getValue(double angle, TSpline3* spline) {
    return spline->Eval(angle);
}





double int_cross_section0(double begin, double end, double delta_phi,double pzz,TSpline3* dsigma,TSpline3* T20) {
    double cross_section = 0;
    int n = 100;
    double delta_theta = (end - begin) / n;
    for (double theta = begin; theta < end; theta += (end - begin) / n) {
        cross_section += getValue(theta*180.0/M_PI, dsigma)*(1.0+0.5*getValue(theta*180.0/M_PI, T20)*sqrt(2.0)*pzz)*delta_theta;
    }
    return cross_section*delta_phi*1e-31;// TRANS FORM mb/sr
}

double N0_count_1detector(double int_crossection0) {
  
  return d_ch2/MCH2*NA*2*int_crossection0  *I/e_q*t_beamline;
}

int main() {


    initializeGlobals(); // 初始化全局变量氘核质量，能量

    double theta_det_lab=20.87 * M_PI / 180;

    double delta_theta = 2.0*M_PI/180;
    double delta_phi = 2.0*M_PI/180;

    std::vector<double> angles1;
    std::vector<double> angles2;

    std::vector<double> crossSections;
    std::vector<double> crossSectionErrors;
    std::vector<double> T20;
    std::vector<double> T20Errors;

    // 读取微分散射截面数据
    readCrossData("../input_data/DataOfCrosssectionAndPol/DSigamaOverDOmega.txt", angles1, crossSections);

    // 读取 T20 数据
    readT20Data("../input_data/DataOfCrosssectionAndPol/CompletSetOFT/T.txt", angles2, T20, T20Errors);

    // 检查数据是否读取成功
    if (angles1.empty() || crossSections.empty() || T20.empty() || T20Errors.empty()) {
        std::cerr << "数据读取失败或数据为空" << std::endl;
        return 1;
    }


    if (angles1.empty() ) {
        std::cerr << "angle cross数据读取失败或数据为空" << std::endl;
        return 1;
    }

    if (angles2.empty() ) {
        std::cerr << " ct20据读取失败或数据为空" << std::endl;
        return 1;
    }

    // 创建微分散射截面图表
    TGraph* crossSectionGraph = new TGraphErrors(angles1.size(), angles1.data(), crossSections.data(), nullptr);
    if (!crossSectionGraph) {
        std::cerr << "TGraphErrors 创建失败" << std::endl;
        return 1;
    }

    // 创建 T20 图表
    TGraphErrors* T20Graph = new TGraphErrors(angles2.size(), angles2.data(), T20.data(), nullptr, T20Errors.data());
    if (!T20Graph) {
        std::cerr << "TGraphErrors 创建失败" << std::endl;
        return 1;
    }

    // 创建样条插值
    TSpline3* crossSectionSpline = new TSpline3("crossSectionSpline", crossSectionGraph);
    if (!crossSectionSpline) {
        std::cerr << "TSpline3 创建失败" << std::endl;
        return 1;
    }

    TSpline3* T20Spline = new TSpline3("T20Spline", T20Graph);
    if (!T20Spline) {
        std::cerr << "TSpline3 创建失败" << std::endl;
        return 1;
    }

        double begin_theta_D_c_1;
        double end_theta_D_c_1;
        double begin_theta_D_c_2;
        double end_theta_D_c_2;

        double theta_D_c_2;
        begin_theta_D_c_1 = func_theta_D_c(theta_det_lab-delta_theta/2).first;
        end_theta_D_c_1 = func_theta_D_c(theta_det_lab+delta_theta/2).first;

        begin_theta_D_c_2 = func_theta_D_c(theta_det_lab+delta_theta/2).second;
        end_theta_D_c_2 = func_theta_D_c(theta_det_lab-delta_theta/2).second;

        


    // 打印角度
    std::cout << "begin_theta_D_c_1: " << begin_theta_D_c_1 <<"\n"<< begin_theta_D_c_1 * 180.0/M_PI << std::endl;
    std::cout << "end_theta_D_c_1: " << end_theta_D_c_1 <<"\n"<< end_theta_D_c_1 * 180.0/M_PI << std::endl;
    std::cout << "begin_theta_D_c_2: " << begin_theta_D_c_2 <<"\n"<< begin_theta_D_c_2 * 180.0/M_PI <<std::endl;
    std::cout << "end_theta_D_c_2: " << end_theta_D_c_2<<"\n"<< end_theta_D_c_2 * 180.0/M_PI << std::endl;




    // double pzz = 1.0;

    // // 计算积分
    // double int_cross_section0_1 = int_cross_section0(begin_theta_D_c_1, end_theta_D_c_1, delta_phi, pzz,crossSectionSpline,T20Spline);
    // double int_cross_section0_2 = int_cross_section0(begin_theta_D_c_2, end_theta_D_c_2, delta_phi, pzz,crossSectionSpline,T20Spline);


    // double N_total4_1 = N0_count_1detector(int_cross_section0_1)*4;
    // double N_total4_2 = N0_count_1detector(int_cross_section0_2)*4;


    // std::cout << "total count\n" << N_total4_1 << "\n" << begin_theta_D_c_1 << std::endl;
    // std::cout << "total count\n" << N_total4_2 << "\n" << end_theta_D_c_2 << std::endl;

    // std::cout << "ratio\n" << N_total4_1/N_total4_2 << std::endl;



    std::vector<double> pzz_values;
    std::vector<double> N_total4_1_values;
    std::vector<double> N_total4_2_values;
    std::vector<double> ratio_values;
    std::vector<double> N1total_error_values;
    std::vector<double> N2total_error_values;
    std::vector<double> ratio_error_values;

    // 生成从0到1的10个pzz值，并计算相应的N_total4_1和N_total4_2值
    for (int i = 0; i <= 10; ++i) {
        double pzz = i * 0.1;
        pzz_values.push_back(pzz);

        double int_cross_section0_1 = int_cross_section0(begin_theta_D_c_1, end_theta_D_c_1, delta_phi, pzz, crossSectionSpline, T20Spline);
        double int_cross_section0_2 = int_cross_section0(begin_theta_D_c_2, end_theta_D_c_2, delta_phi, pzz, crossSectionSpline, T20Spline);

        double N_total4_1 = N0_count_1detector(int_cross_section0_1) * 4;
        double N_total4_2 = N0_count_1detector(int_cross_section0_2) * 4;

        N_total4_1_values.push_back(N_total4_1);
        N1total_error_values.push_back(sqrt(N_total4_1));

        N_total4_2_values.push_back(N_total4_2);
        N2total_error_values.push_back(sqrt(N_total4_2));

        ratio_values.push_back(N_total4_1 / N_total4_2);

        double N=I/e_q*t_beamline;
        double varf = N_total4_1/pow(N_total4_2,2.0) + pow(N_total4_1,2.0)/pow(N_total4_2,3.0) + 2*N_total4_1/N/pow(N_total4_2,2.0); 
        ratio_error_values.push_back (sqrt(varf) );
    }



    
    // 创建画布
    TCanvas* c1 = new TCanvas("c1", "N_total4_1 and N_total4_2 vs pzz", 800, 600);
    TGraph* graph1 = new TGraphErrors(pzz_values.size(), pzz_values.data(), N_total4_1_values.data(), nullptr, N1total_error_values.data());
    TGraph* graph2 = new TGraphErrors(pzz_values.size(), pzz_values.data(), N_total4_2_values.data(), nullptr, N2total_error_values.data());

    graph1->SetMarkerStyle(20);
    graph1->SetMarkerColor(kRed);
    graph1->SetTitle("N_total4_1 vs pzz; pzz; N_total4_1");
    graph1->Draw("AP");

    graph2->SetMarkerStyle(21);
    graph2->SetMarkerColor(kBlue);
    graph2->SetTitle("N_total4_2 vs pzz; pzz; N_total4_2");
    graph2->Draw("P SAME");

    c1->BuildLegend();
    c1->SaveAs("../cache/N_total4_vs_pzz.png");

    TCanvas* c3 = new TCanvas("c3", "N_total vs pzz", 800, 600);
    graph1->SetMarkerStyle(20);
    graph1->SetMarkerColor(kRed);
    // graph1->SetTitle("N_total vs pzz; pzz; N_total");
    graph1->Draw("AP");
    //    c3->BuildLegend();
    // gPad->SetLogy();
    // TGaxis::SetMaxDigits(2);

    c3->SaveAs("../cache/N1vs_pzz.root");



    // 创建比例图
    TCanvas* c2 = new TCanvas("c2", "Ratio of N_total4_1 to N_total4_2 vs pzz", 800, 600);
    TGraph* ratioGraph = new TGraphErrors(pzz_values.size(), pzz_values.data(), ratio_values.data(), nullptr, ratio_error_values.data());


    ratioGraph->SetMarkerStyle(22);
    ratioGraph->SetMarkerColor(kGreen);
    // ratioGraph->SetTitle("Ratio of N_total4_1 to N_total4_2 vs pzz; pzz; Ratio");
    ratioGraph->Draw("AP");

    c2->SaveAs("../cache/Ratio_vs_pzz.root");

    return 0;



}