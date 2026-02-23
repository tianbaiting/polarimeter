//  这一个是用于计算我的探测器摆放位置

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


//  这一个是用于计算我的探测器摆放位置

int main() {

    initializeGlobals(); // 初始化全局变量
    
// 初始化数据点
    const int n = 1000;


    double theta_D_c[n];
    double theta_D_lab[n];
    double theta_p_lab[n];
    double theta_D_c_deg[n];
    double theta_D_lab_deg[n];
    double theta_p_lab_deg[n];
    // 填充数据点
    for (int i = 0; i < n; i++) {
        theta_D_c[i] = i*M_PI/n; // 这里你需要根据实际情况设置theta_D_c的值
        auto result = P_lab(theta_D_c[i], 0.0);
        TLorentzVector P_lab_c_beforeCollision = result.first;
        theta_D_lab[i] = P_lab_c_beforeCollision.Theta();
        TLorentzVector P_p_lab_c_beforeCollision = result.second;

        theta_p_lab[i] =P_p_lab_c_beforeCollision.Theta();

     // 转换为度数
        theta_D_c_deg[i] = theta_D_c[i] * 180.0 / M_PI;
        theta_D_lab_deg[i] = theta_D_lab[i] * 180.0 / M_PI;
        theta_p_lab_deg[i] = theta_p_lab[i] * 180.0 / M_PI;
    }




    // 
//D detector用粉红色 涂抹， 以下范围为y轴


// double delta_theta_P_lab = width_p/distance_p*180/M_PI;
double delta_theta_P1_lab = width_p1/distance_p*180/M_PI;
double delta_theta_P2_lab = width_p2/distance_p*180/M_PI;

double delta_theta_D_lab = width_D/distance_D*180/M_PI;

// 创建TCanvas对象并绘制图形
TCanvas *c1 = new TCanvas("c1", "Theta D_c vs Theta Lab", 800, 600);
    // 创建TGraph对象
TGraph *gr = new TGraph(n,  theta_D_lab_deg,theta_D_c_deg);

// 创建另一个TGraph对象
TGraph *gr2 = new TGraph(n, theta_p_lab_deg, theta_D_c_deg);
// 设置X轴和Y轴的标签
gr2->GetXaxis()->SetTitle("#theta_{lab}(deg)");
gr2->GetYaxis()->SetTitle("#theta_{D_{c}}(deg)");

// 设置X轴和Y轴的范围
gr2->GetXaxis()->SetRangeUser(0, 90);
gr2->GetYaxis()->SetRangeUser(0, 180);

gr2->SetLineColor(kBlue); // 设置第二个图形的线条颜色为蓝色
gr2->Draw("AC"); // "C"表示使用曲线连接数据点，"*"表示绘制数据点

gr->SetLineColor(kRed); // 设置第一个图形的线条颜色为红色
gr->SetTitle("");
gr->Draw("C"); // "A"表示自动选择坐标轴的范围，"C"表示使用曲线连接数据点，"*"表示绘制数据点



// 创建图例并添加标签
TLegend *legend = new TLegend(0.7, 0.7, 0.9, 0.9); // 设置图例的位置
legend->AddEntry(gr2, "proton", "l"); // "l"表示线条类型
legend->AddEntry(gr, "deuteron", "l"); // "l"表示线条类型
legend->Draw();

double y1 = func_theta_P_cm((theta_p1_labdeg - delta_theta_P1_lab / 2) * M_PI / 180) * 180 / M_PI;
double y2 = func_theta_P_cm((theta_p1_labdeg + delta_theta_P1_lab / 2) * M_PI / 180) * 180 / M_PI;
TBox *box1 = new TBox(theta_p1_labdeg - delta_theta_P1_lab / 2, y1, theta_p1_labdeg + delta_theta_P1_lab / 2, y2);
box1->SetFillColor(kCyan);
box1->Draw("same");

gr->GetXaxis()->SetTitleSize(0.05);
gr->GetYaxis()->SetTitleSize(0.05);
c1->SetLeftMargin(0.15);
c1->SetBottomMargin(0.15);

double y3 = func_theta_P_cm((theta_p2_labdeg - delta_theta_P2_lab / 2) * M_PI / 180) * 180 / M_PI;
double y4 = func_theta_P_cm((theta_p2_labdeg + delta_theta_P2_lab / 2) * M_PI / 180) * 180 / M_PI;
TBox *box2 = new TBox(theta_p2_labdeg - delta_theta_P2_lab / 2, y3, theta_p2_labdeg + delta_theta_P2_lab / 2, y4);
box2->SetFillColor(kCyan);
box2->Draw("same");

double x1 = func_theta_D_c((theta_D_scin_labdeg - delta_theta_D_lab / 2) * M_PI / 180).first * 180 / M_PI;
double x2 = func_theta_D_c((theta_D_scin_labdeg + delta_theta_D_lab / 2) * M_PI / 180).first * 180 / M_PI;
TBox *box3 = new TBox(theta_D_scin_labdeg - delta_theta_D_lab / 2, x1, theta_D_scin_labdeg + delta_theta_D_lab / 2, x2);
box3->SetFillColor(kPink);
box3->Draw("same");

double x3 = func_theta_D_c((theta_D_scin_labdeg - delta_theta_D_lab / 2) * M_PI / 180).second * 180 / M_PI;
double x4 = func_theta_D_c((theta_D_scin_labdeg + delta_theta_D_lab / 2) * M_PI / 180).second * 180 / M_PI;
TBox *box4 = new TBox(theta_D_scin_labdeg - delta_theta_D_lab / 2, x3, theta_D_scin_labdeg + delta_theta_D_lab / 2, x4);
box4->SetFillColor(kPink);
box4->Draw("same");



// 保存图形
c1->SaveAs("Pol_angcover_flipped.pdf");
c1->SaveAs("Pol_angcover_flipped.png");
// c1->SaveAs("Pol_angcover_flipped.eps");


    // // 创建TCanvas对象并绘制图形
    // TCanvas *c1 = new TCanvas("c1", "Theta Lab vs Theta D_c", 800, 600);

    // gr->SetLineColor(kRed); // 设置第一个图形的线条颜色为红色
    // gr->SetTitle("");
    // gr->Draw("AC"); // "A"表示自动选择坐标轴的范围���"C"表示使用曲线连接数据点，"*"表示绘制数据点

    // gr2->SetLineColor(kBlue); // 设置第二个图形的线条颜色为蓝色
    // gr2->Draw("C"); // "C"表示使用曲线连接数据点，"*"表示绘制数据点
    // // 创建图例并添加标签
    // TLegend *legend = new TLegend(0.7, 0.7, 0.9, 0.9); // 设置图例的位置
    // legend->AddEntry(gr2, "proton", "l"); // "l"表示线条类型
    // legend->AddEntry(gr, "deuteron", "l"); // "l"表示线条类型
    // legend->Draw(); 

    // double x1=func_theta_P_cm((theta_p1_labdeg - delta_theta_P1_lab/2)*M_PI/180)*180/M_PI;
    // double x2=func_theta_P_cm((theta_p1_labdeg + delta_theta_P1_lab/2)*M_PI/180)*180/M_PI;
    //     TBox *box1 = new TBox(x2, theta_p1_labdeg - delta_theta_P1_lab/2, x1, theta_p1_labdeg + delta_theta_P1_lab/2);
    //     box1->SetFillColor(kCyan);
    //     box1->Draw("same");

    //     gr->GetXaxis()->SetTitleSize(0.05);
    //     gr->GetYaxis()->SetTitleSize(0.05);
    //     c1->SetLeftMargin(0.15);
    //     // c1->SetRightMargin(0.15);
    //     // c1->SetTopMargin(0.15);
    //     c1->SetBottomMargin(0.15);
    
    //     double x3=func_theta_P_cm((theta_p2_labdeg - delta_theta_P2_lab/2)*M_PI/180)*180/M_PI;
    //     double x4=func_theta_P_cm((theta_p2_labdeg + delta_theta_P2_lab/2)*M_PI/180)*180/M_PI;
    //     TBox *box2 = new TBox(x3, theta_p2_labdeg - delta_theta_P2_lab/2, x4, theta_p2_labdeg + delta_theta_P2_lab/2);
    //     box2->SetFillColor(kCyan);
    //     box2->Draw("same");

    //     double y1=func_theta_D_c((theta_D_scin_labdeg - delta_theta_D_lab/2 )*M_PI/180).first*180/M_PI;
    //     double y2=func_theta_D_c((theta_D_scin_labdeg + delta_theta_D_lab/2 )*M_PI/180).first*180/M_PI;
    //     TBox *box3 = new TBox(y1, theta_D_scin_labdeg - delta_theta_D_lab/2, y2, theta_D_scin_labdeg + delta_theta_D_lab/2);
    //     box3->SetFillColor(kPink);
    //     box3->Draw("same");

    //     double y3=func_theta_D_c((theta_D_scin_labdeg - delta_theta_D_lab/2 )*M_PI/180).second*180/M_PI;
    //     double y4=func_theta_D_c((theta_D_scin_labdeg + delta_theta_D_lab/2 )*M_PI/180).second*180/M_PI;
    //     TBox *box4 = new TBox(y3, theta_D_scin_labdeg - delta_theta_D_lab/2, y4, theta_D_scin_labdeg + delta_theta_D_lab/2);
    //     box4->SetFillColor(kPink);
    //     box4->Draw("same");


    //        // 设置X轴和Y轴的标签
    // gr->GetXaxis()->SetTitle("#theta_{D_{c}}(deg)");
    // gr->GetYaxis()->SetTitle("#theta_{lab}(deg)");


    // // 设置X轴和Y轴的范围
    // gr->GetXaxis()->SetRangeUser(0, 180);
    // gr->GetYaxis()->SetRangeUser(0, 90);

    // // 保存图形
    // c1->SaveAs("Pol_angcover.pdf");
    // c1->SaveAs("Pol_angcover.png");
    // // c1->SaveAs("Pol_angcover.eps");

    return 0;

}