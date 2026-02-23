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


std::pair<TLorentzVector, TLorentzVector> P_lab(double theta_D_c, double phi_D_c);

int main() {

    initializeGlobals(); // 初始化全局变量
    // // 定义 theta_D_c 和 phi_D_c 的范围和步长
    // double theta_min = 0.0;
    // double theta_max = M_PI;
    // double phi_min = 0.0;
    // double phi_max = 2 * M_PI;
    // double step = 0.1;

    // // 定义 eta 和 phi 的特定值范围
    // double theta_range_min = (21-1)/180*M_PI;
    // double theta_range_max = (21+1)/180*M_PI;
    // double phi_range_min = -1/180*M_PI;
    // double phi_range_max = 1/180*M_PI;

    // // 创建一个二维直方图
    // TH2F *hist = new TH2F("hist", "P_D_c_beforeCollision E分量;theta;phi", 
    //                       (theta_max - theta_min) / step, theta_min, theta_max, 
    //                       (phi_max - phi_min) / step, phi_min, phi_max);

    // // 遍历 theta_D_c 和 phi_D_c
    // for (double theta_D_c = theta_min; theta_D_c <= theta_max; theta_D_c += step) {
    //     for (double phi_D_c = phi_min; phi_D_c <= phi_max; phi_D_c += step) {
    //         // 计算 P_D_c_beforeCollision
    //         auto result = P_lab(theta_D_c, phi_D_c);
    //         TLorentzVector P_D_c_beforeCollision = result.first;

    //         // 计算 eta 和 phi
    //         double eta = P_D_c_beforeCollision.Theta();
    //         double phi = P_D_c_beforeCollision.Phi();

    //         // 检查 eta 和 phi 是否在特定值范围内
    //         if (eta >= theta_range_min && eta <= theta_range_max && phi >= phi_range_min && phi <= phi_range_max) {
    //             // 记录 theta_D_c、phi_D_c 和 P_D_c_beforeCollision 的 E 分量
    //             double E = P_D_c_beforeCollision.E();
    //             hist->Fill(theta_D_c, phi_D_c, E);
    //         }
    //     }
    // }

    // // 绘制图形
    // TCanvas *canvas = new TCanvas("canvas", "P_D_c_beforeCollision E���量图", 800, 600);
    // hist->Draw("COLZ");
    // canvas->SaveAs("P_D_c_beforeCollision_E.png");

    // return 0;

//     double theta_D_c=0.1;
//     double phi_D_c=0.1;
//     auto result = P_lab(theta_D_c, phi_D_c);
//      TLorentzVector P_lab_c_beforeCollision = result.first;
//     //计算 eta 和 phi
//              double theta_D_lab = P_lab_c_beforeCollision.Theta();
//              double phi_lab = P_lab_c_beforeCollision.Phi();
//  printf("theta %f phi %f\n",theta_D_lab,phi_lab);
//     return 0;
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

                // 打印phi角
        // std::cout << "Phi angle of P_lab_c_beforeCollision: " << P_lab_c_beforeCollision.Phi() << std::endl;
        // std::cout << "Phi angle of P_p_lab_c_beforeCollision: " << P_p_lab_c_beforeCollision.Phi() << std::endl;
     // 转换为度数
        theta_D_c_deg[i] = theta_D_c[i] * 180.0 / M_PI;
        theta_D_lab_deg[i] = theta_D_lab[i] * 180.0 / M_PI;
        theta_p_lab_deg[i] = theta_p_lab[i] * 180.0 / M_PI;
    }

    // 创建TGraph对象
    TGraph *gr = new TGraph(n, theta_D_c_deg, theta_D_lab_deg);

    // 创建另一个TGraph对象
    TGraph *gr2 = new TGraph(n, theta_D_c_deg, theta_p_lab_deg);


    // sekeguichi的探测器摆放的位置

//D detector用粉红色 涂抹， 以下范围为y轴
    double theta_D_detector_lab[4]={20.1, 22.7, 25.6,29.3};
    double delta_theta_1=24.0/560*180/M_PI;
    double delta_theta_2=50.0/560*180/M_PI;
    double Deltatheta_D_lab[4]={delta_theta_1,delta_theta_1,delta_theta_1,delta_theta_2};

//P detector用淡蓝色 涂抹， 以下范围为y轴
    double theta_p_detector_lab[8] = {21.3, 26.1, 30.9,35.8,40.8, 45.0, 50.8,55.9};

double delta_theta_P_lab = 20.0/560*180/M_PI;



    // // 创建TGraph对象
    // TGraph *gr = new TGraph(n, theta_D_c, theta_D_lab);

    // // 创建另一个TGraph对象
    // TGraph *gr2 = new TGraph(n, theta_D_c, theta_p_lab);

    // 创建TCanvas对象并绘制图形
    TCanvas *c1 = new TCanvas("c1", "Theta Lab vs Theta D_c", 800, 600);
    gr->SetLineColor(kRed); // 设置第一个图形的线条颜色为红色
    gr->Draw("AC"); // "A"表示自动选择坐标轴的范围���"C"表示使用曲线连接数据点，"*"表示绘制数据点

    gr2->SetLineColor(kBlue); // 设置第二个图形的线条颜色为蓝色
    gr2->Draw("C"); // "C"表示使用曲线连接数据点，"*"表示绘制数据点

    // 绘制D探测器位置
    for (int i = 0; i < 3; i++) {
        double x1=func_theta_D_c((theta_D_detector_lab[i] - Deltatheta_D_lab[i]/2 )*M_PI/180).first*180/M_PI;
        double x2=func_theta_D_c((theta_D_detector_lab[i] + Deltatheta_D_lab[i]/2 )*M_PI/180).first*180/M_PI;

        std::cout<<"D cm" <<x1<<" " <<x2<< std::endl;
        TBox *box1 = new TBox(x1, theta_D_detector_lab[i] - Deltatheta_D_lab[i]/2,x2, theta_D_detector_lab[i] + Deltatheta_D_lab[i]/2);
        box1->SetFillColor(kPink);
        box1->Draw("same");


        double x3=func_theta_D_c((theta_D_detector_lab[i] - Deltatheta_D_lab[i]/2 )*M_PI/180).second*180/M_PI;
        double x4=func_theta_D_c((theta_D_detector_lab[i] + Deltatheta_D_lab[i]/2 )*M_PI/180).second*180/M_PI;
        TBox *box2 = new TBox(x4, theta_D_detector_lab[i] - Deltatheta_D_lab[i]/2, x3, theta_D_detector_lab[i] + Deltatheta_D_lab[i]/2);\
        box2->SetFillColor(kPink);
        box2->Draw("same");
    }

    double max_theta_D_lab = *std::max_element(theta_D_lab, theta_D_lab + n);
        double y1=func_theta_D_c((theta_D_detector_lab[3] - Deltatheta_D_lab[3]/2 )*M_PI/180).first*180/M_PI;
        double y2=func_theta_D_c((theta_D_detector_lab[3] - Deltatheta_D_lab[3]/2 )*M_PI/180).second*180/M_PI;
        TBox *box4 = new TBox(y1, theta_D_detector_lab[3] - Deltatheta_D_lab[3]/2, y2, theta_D_detector_lab[3] + Deltatheta_D_lab[3]/2);
        box4->SetFillColor(kPink);
        box4->Draw("same");

       
        std::cout<< (theta_D_detector_lab[3] - Deltatheta_D_lab[3]/2 ) << std::endl;
        std::cout   << (theta_D_detector_lab[3] + Deltatheta_D_lab[3]/2 ) << std::endl;


std::cout<< "拐点"<< std::endl;



    // 找到 theta_D_lab 的最大值

    std::cout << "theta_D_lab 的最大值: " << max_theta_D_lab*180/M_PI << std::endl;


        // TBox *box1 = new TBox(x1, theta_D_detector_lab[i] - Deltatheta_D_lab[i]/2,x2, theta_D_detector_lab[i] + Deltatheta_D_lab[i]/2);
        // box1->SetFillColor(kPink);
        // box1->Draw("same");


    // 绘制P探测器位置
    for (int i = 0; i < 8; i++) {

        double x1=func_theta_P_cm((theta_p_detector_lab[i] - delta_theta_P_lab/2)*M_PI/180)*180/M_PI;
        double x2=func_theta_P_cm((theta_p_detector_lab[i] + delta_theta_P_lab/2)*M_PI/180)*180/M_PI;
        TBox *box3 = new TBox(x2, theta_p_detector_lab[i] - delta_theta_P_lab/2, x1, theta_p_detector_lab[i] + delta_theta_P_lab/2);
        box3->SetFillColor(kCyan);
        box3->Draw("same");
    }


    //     // 绘制与曲线相交的D探测器位置
    // for (int i = 0; i < 4; i++) {
    //     double y_min = theta_D_detector_lab[i] - Deltatheta_D_lab[i] / 2;
    //     double y_max = theta_D_detector_lab[i] + Deltatheta_D_lab[i] / 2;
    //     for (int j = 0; j < n - 1; j++) {
    //         if ((theta_D_lab[j] >= y_min && theta_D_lab[j] <= y_max) || (theta_D_lab[j + 1] >= y_min && theta_D_lab[j + 1] <= y_max)) {
    //             double x_min = theta_D_c[j];
    //             double x_max = theta_D_c[j + 1];
    //             TBox *box = new TBox(x_min, y_min, x_max, y_max);
    //             box->SetFillColor(kPink);
    //             box->Draw("same");
    //         }
    //     }
    // }

    // // 绘制与曲线相交的P探测器位置
    // for (int i = 0; i < 8; i++) {
    //     double y_min = theta_p_detector_lab[i] - delta_theta_P_lab / 2;
    //     double y_max = theta_p_detector_lab[i] + delta_theta_P_lab / 2;
    //     for (int j = 0; j < n - 1; j++) {
    //         if ((theta_p_lab[j] >= y_min && theta_p_lab[j] <= y_max) || (theta_p_lab[j + 1] >= y_min && theta_p_lab[j + 1] <= y_max)) {
    //             double x_min = theta_D_c[j];
    //             double x_max = theta_D_c[j + 1];
    //             TBox *box = new TBox(x_min, y_min, x_max, y_max);
    //             box->SetFillColor(kCyan);
    //             box->Draw("same");
    //         }
    //     }
    // }


    // 设置X轴和Y轴的范围
    gr->GetXaxis()->SetRangeUser(0, 180);
    gr->GetYaxis()->SetRangeUser(0, 90);

    // 保存图形
    c1->SaveAs("ThetaLab_vs_ThetaDc_deg.png");

    return 0;

}