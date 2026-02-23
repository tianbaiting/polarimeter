//  Description: 本程序用于计算两个探测器的角度分布比值
// 计算的是质子覆盖的LRUD内计数的比例

// 2. 项目自身的头文件
#include "function.h"
#include "globals.h"

// 3. C++标准库
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <math.h>

// 4. 第三方库 (ROOT)
#include <TApplication.h>
#include <TAxis.h>
#include <TCanvas.h>
#include <TGaxis.h>
#include <TGraphErrors.h>
#include <TMultiGraph.h>
#include <TSpline.h>
#include <TStyle.h>

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

void readT22Data(const std::string& filename, std::vector<double>& angles, std::vector<double>& T22, std::vector<double>& deltaT22) {
    std::ifstream infile(filename);
    if (!infile.is_open()) {
        std::cerr << "无法打开文件 " << filename << std::endl;
        return;
    }

    std::string line;
    // 跳过文件头
    std::getline(infile, line);

    double angle, t22, dt22;
    std::string dummy;
    while (infile >> angle >> dummy >> dummy >> dummy >> dummy >> dummy >> dummy >> t22 >> dt22) {
        if (dummy != "null") {
            angles.push_back(angle);
            T22.push_back(t22);
            deltaT22.push_back(dt22);
        }
    }

    infile.close();
}





// 返回给定角度的值
double getValue(double angle, TSpline3* spline) {
    if (!spline) {
        std::cerr << "错误：TSpline3 对象为空" << std::endl;
        return 0.0;
    }
    return spline->Eval(angle);
}





double int_cross_section_LR(double begin, double end, double delta_phi,double pyy,TSpline3* dsigma,TSpline3* T20,TSpline3* T22) {
    double cross_section = 0;
    int n = 100;
    double delta_theta = (end - begin) / n;
    for (double theta = begin; theta < end; theta += (end - begin) / n) {
        // double theta_deg = theta * 180.0 / M_PI;
        // double T20_value = getValue(theta_deg, T20);
        // double T22_value = getValue(theta_deg, T22);
        // double sigma_value = getValue(theta_deg, dsigma);

        // double try_1 = getValue(60.0 ,T22);
        // double try_2 = getValue(60.0 ,T20);

        cross_section += getValue(theta*180.0/M_PI, dsigma)*(1.0 -0.25*pyy*2*sqrt(3.0)*getValue(theta*180.0/M_PI, T22)-0.25*pyy*getValue(theta*180.0/M_PI, T20)*sqrt(2.0))*delta_theta;
    }
    return cross_section*delta_phi*1e-31;// TRANS FORM mb/sr
}

double int_cross_section_UD(double begin, double end, double delta_phi,double pyy,TSpline3* dsigma,TSpline3* T20,TSpline3* T22) {
    double cross_section = 0;
    int n = 100;
    double delta_theta = (end - begin) / n;
    for (double theta = begin; theta < end; theta += (end - begin) / n) {
        cross_section += getValue(theta*180.0/M_PI, dsigma)*(1.0 +0.25*pyy*2*sqrt(3.0)*getValue(theta*180.0/M_PI, T22)-0.25*getValue(theta*180.0/M_PI, T20)*sqrt(2.0)*pyy)*delta_theta;
    }
    return cross_section*delta_phi*1e-31;// TRANS FORM mb/sr
}


double N0_count_1detector(double int_crossection0) {
  
  return d_ch2/MCH2*NA*2*int_crossection0  *I/e_q*t_beamline;
}


int main() {


    initializeGlobals(); // 初始化全局变量氘核质量，能量

    // double theta_det_lab_1=theta_p1_labdeg;
    // double theta_det_lab_2=theta_p2_labdeg;

    double delta_theta_P1_lab = width_p1/distance_p;
    double delta_theta_P2_lab = width_p2/distance_p;

    double delta_phi1 = width_p1_phi/distance_p/sin(theta_p1_labdeg*M_PI/180);
    double delta_phi2 = width_p2_phi/distance_p/sin(theta_p2_labdeg*M_PI/180);

    std::vector<double> angles1;
    std::vector<double> angles2;
    std::vector<double> angles3;

    std::vector<double> crossSections;
    std::vector<double> crossSectionErrors;
    std::vector<double> T20;
    std::vector<double> T20Errors;
    std::vector<double> T22;
    std::vector<double> T22Errors;

    // 读取微分散射截面数据
    readCrossData("./input_data/DataOfCrosssectionAndPol/DSigamaOverDOmega.txt", angles1, crossSections);

    // 读取 T20 数据
    readT20Data("./input_data/DataOfCrosssectionAndPol/CompletSetOFT/T.txt", angles2, T20, T20Errors);



        // 读取 T22 数据
    readT22Data("./input_data/DataOfCrosssectionAndPol/CompletSetOFT/T.txt", angles3, T22, T22Errors);

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

        TGraphErrors* T22Graph = new TGraphErrors(angles3.size(), angles3.data(), T22.data(), nullptr, T22Errors.data());
    if (!T22Graph) {
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

        TSpline3* T22Spline = new TSpline3("T22Spline", T22Graph);
    if (!T22Spline) {
        std::cerr << "TSpline3 创建失败" << std::endl;
        return 1;
    }
//     // 创建画布
//     TCanvas* c2 = new TCanvas("c2", "Cross Section, T20, and T22", 1200, 800);
//     c2->Divide(2, 2);

//     // 绘制微分散射截面图表
//     c2->cd(1);
//     crossSectionGraph->SetTitle("Differential Cross Section");
//     crossSectionGraph->GetXaxis()->SetTitle("Angle (degrees)");
//     crossSectionGraph->GetYaxis()->SetTitle("Cross Section");
//     crossSectionGraph->SetMarkerStyle(20);
//     crossSectionGraph->SetMarkerSize(1.0);
//     crossSectionGraph->SetMarkerColor(kRed);
//     crossSectionGraph->Draw("AP");

//     // 绘制 T20 图表
//     c2->cd(2);
//     T20Graph->SetTitle("T20");
//     T20Graph->GetXaxis()->SetTitle("Angle (degrees)");
//     T20Graph->GetYaxis()->SetTitle("T20");
//     T20Graph->SetMarkerStyle(21);
//     T20Graph->SetMarkerSize(1.0);
//     T20Graph->SetMarkerColor(kGreen);
//     T20Graph->Draw("AP");

//     // 绘制 T22 图表
//     c2->cd(3);
//     T22Graph->SetTitle("T22");
//     T22Graph->GetXaxis()->SetTitle("Angle (degrees)");
//     T22Graph->GetYaxis()->SetTitle("T22");
//     T22Graph->SetMarkerStyle(22);
//     T22Graph->SetMarkerSize(1.0);
//     T22Graph->SetMarkerColor(kBlue);
//     T22Graph->Draw("AP");

//     // 绘制 T20 图表
// c2->cd(2);
// T20Graph->SetTitle("T20");
// T20Graph->GetXaxis()->SetTitle("Angle (degrees)");
// T20Graph->GetYaxis()->SetTitle("T20");
// T20Graph->SetMarkerStyle(21);
// T20Graph->SetMarkerSize(1.0);
// T20Graph->SetMarkerColor(kGreen);
// T20Graph->Draw("AP");

// // 绘制 T20 样条曲线
// T20Spline->SetLineColor(kGreen+2);  // 使用深一点的绿色
// T20Spline->SetLineWidth(2);
// T20Spline->Draw("same");  // "same" 选项使其绘制在同一张图上

// // 绘制 T22 图表
// c2->cd(3);
// T22Graph->SetTitle("T22");
// T22Graph->GetXaxis()->SetTitle("Angle (degrees)");
// T22Graph->GetYaxis()->SetTitle("T22");
// T22Graph->SetMarkerStyle(22);
// T22Graph->SetMarkerSize(1.0);
// T22Graph->SetMarkerColor(kBlue);
// T22Graph->Draw("AP");

// // 绘制 T22 样条曲线
// T22Spline->SetLineColor(kBlue+2);  // 使用深一点的蓝色
// T22Spline->SetLineWidth(2);
// T22Spline->Draw("same");

// // 同样为微分散射截面添加样条曲线
// c2->cd(1);
// crossSectionSpline->SetLineColor(kRed+2);  // 使用深一点的红色
// crossSectionSpline->SetLineWidth(2);
// crossSectionSpline->Draw("same");

//     // 保存图表为PNG文件
//     c2->SaveAs("CrossSection_T20_T22.png");





        double begin_theta_D_c_1;
        double end_theta_D_c_1;
        double begin_theta_D_c_2;
        double end_theta_D_c_2;

        double theta_D_c_2;
        begin_theta_D_c_1 = func_theta_P_cm(theta_p1_labdeg*M_PI/180 + delta_theta_P1_lab/2);
        end_theta_D_c_1   = func_theta_P_cm(theta_p1_labdeg*M_PI/180 - delta_theta_P1_lab/2);

        begin_theta_D_c_2 = func_theta_P_cm(theta_p2_labdeg*M_PI/180 + delta_theta_P2_lab/2);
        end_theta_D_c_2   = func_theta_P_cm(theta_p2_labdeg*M_PI/180 - delta_theta_P2_lab/2);

        


    // 打印角度
    std::cout << "begin_theta_D_c_1: " << begin_theta_D_c_1 <<"\n"<< begin_theta_D_c_1 * 180.0/M_PI << std::endl;
    std::cout << "end_theta_D_c_1: " << end_theta_D_c_1 <<"\n"<< end_theta_D_c_1 * 180.0/M_PI << std::endl;
    std::cout << "begin_theta_D_c_2: " << begin_theta_D_c_2 <<"\n"<< begin_theta_D_c_2 * 180.0/M_PI <<std::endl;
    std::cout << "end_theta_D_c_2: " << end_theta_D_c_2<<"\n"<< end_theta_D_c_2 * 180.0/M_PI << std::endl;





    std::vector<double> pyy_values;
    std::vector<double> N_LR_values;
    std::vector<double> N_UD_values;
    std::vector<double> error_N_LR_values;
    std::vector<double> error_N_UD_values;
    std::vector<double> R_LRUD_values;
    std::vector<double> error_R_LRUD_values;

    // 生成从0到1的10个pyy值，并计算相应的测量theta1处的值
    for (int i = 0; i <= 10; ++i) {
        double pyy = i * 0.1;
        pyy_values.push_back(pyy);

        double int_cross_section0_1_LR = int_cross_section_LR(begin_theta_D_c_1, end_theta_D_c_1, delta_phi1, pyy, crossSectionSpline, T20Spline,T22Spline);
        double int_cross_section0_1_UD = int_cross_section_UD(begin_theta_D_c_1, end_theta_D_c_1, delta_phi1, pyy, crossSectionSpline, T20Spline,T22Spline);


        double N_LR = N0_count_1detector(int_cross_section0_1_LR) * 2;
        

        double N_UD = N0_count_1detector(int_cross_section0_1_UD) * 2;
        double N=I/e_q*t_beamline;

        double P_LR = N_LR/N;
        double P_UD = N_UD/N;
        double R_LRUD = (N_LR-N_UD)/(N_LR+N_UD);
        // 多项式分布
        double sigma_squre_N_LR = N*(1-P_LR)*P_UD;
        double sigma_squre_N_UD = N*(1-P_UD)*P_UD;
        double cov_NLR_NUD = -N*P_LR*P_UD;

        double par_R_NLR = 2*N_UD / pow(N_LR+N_UD,2);
        double par_R_NUD = -2*N_LR / pow(N_LR+N_UD,2);
        
        double sigma_squre_R = pow(par_R_NLR,2)*sigma_squre_N_LR + pow(par_R_NUD,2)*sigma_squre_N_UD + 2* par_R_NLR*par_R_NUD* cov_NLR_NUD;

        error_N_LR_values.push_back(sqrt(sigma_squre_N_LR));
        error_N_UD_values.push_back(sqrt(sigma_squre_N_UD));
        error_R_LRUD_values.push_back(sqrt(sigma_squre_R));
        R_LRUD_values.push_back(R_LRUD);
        N_LR_values.push_back(N_LR);
        N_UD_values.push_back(N_UD);


    }



    



TGraph* graph1 = new TGraphErrors(pyy_values.size(), pyy_values.data(), R_LRUD_values.data(), nullptr, error_R_LRUD_values.data());


TGraph* graph2 = new TGraphErrors(pyy_values.size(), pyy_values.data(), R_LRUD_values.data(), nullptr, error_R_LRUD_values.data());


// 创建画布并设置大小
TCanvas* c1 = new TCanvas("c1", "R_LRUD vs pyy", 800, 600);

// 设置图表样式
gStyle->SetOptStat(0);
gStyle->SetTitleFontSize(0.04);
gStyle->SetTitleX(0.5);
gStyle->SetTitleAlign(23);
gStyle->SetLabelSize(0.06, "XY");
gStyle->SetTitleSize(0.06, "XY"); // 稍微减小标题大小

// 增加边距，特别是底部和左侧
gStyle->SetPadTopMargin(0.1);
gStyle->SetPadBottomMargin(0.5);
gStyle->SetPadLeftMargin(0.5);
gStyle->SetPadRightMargin(0.05);

c1->SetBottomMargin(0.15); // 调整底部边界宽度
c1->SetLeftMargin(0.18); // 调整左边边界宽度
// 设置轴标签
graph1->GetXaxis()->SetTitle("#it{p}_{y'y'}");
graph1->GetYaxis()->SetTitle("#it{R}_{LRUD}");
graph1->GetXaxis()->CenterTitle();
graph1->GetYaxis()->CenterTitle();
// graph1->GetXaxis()->SetTitleOffset(1.5); // 增加X轴标题偏移
// graph1->GetYaxis()->SetTitleOffset(1.8); // 增加Y轴标题偏移
graph1->SetTitle(" ");
// 定义莫兰迪蓝灰色
// int morandiBlue = TColor::GetColor(120, 144, 156);

// 设置标记样式
graph1->SetMarkerStyle(24);      // 空心圆
graph1->SetMarkerSize(2);
// graph1->SetMarkerColor(morandiBlue);
graph1->SetMarkerColor(kBlue);
// 
// graph1->SetLineColor(morandiBlue);
graph1->SetFillColor(0);  
graph1->SetFillStyle(0);  

// 绘制图表
// 先画点（marker）
graph1->SetLineWidth(4);  // 设置线宽
graph1->Draw("AP"); 
graph2->SetLineWidth(3);  // 设置线宽
graph2->Draw("P SAME"); // 绘制第二个图表，使用相同的画布

c1->SetGrid();

// 保存图表为PNG文件
c1->SaveAs("R_LRUD_vs_pyy.png");
c1->SaveAs("R_LRUD_vs_pyy.pdf");

std::cout << "error_R_LRUD_values 中的所有值:" << std::endl;
for (size_t i = 0; i < error_R_LRUD_values.size(); ++i) {
    std::cout << "值 " << i << ": " << error_R_LRUD_values[i] << std::endl;
}
return 0;



}