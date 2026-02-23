#include "TLorentzVector.h"
#include "TVector3.h"
#include "function.h"
#include <math.h>
#include "globals.h"


//  实验室系下DP散射后的动量
std::pair<TLorentzVector, TLorentzVector> P_lab(double theta_D_c, double phi_D_c){

    TLorentzVector P_pro_lab_beforeCollision;
    P_pro_lab_beforeCollision.SetPxPyPzE(0, 0, 0, mP);
    
    TLorentzVector P_D_lab_beforeCollision;
    P_D_lab_beforeCollision.SetPxPyPzE(0, 0, pD, ED);

    TLorentzVector P_total_lab = P_pro_lab_beforeCollision + P_D_lab_beforeCollision;

    // Calculate the boost vector to the P_total_lab rest frame
    TVector3 boostVector = P_total_lab.BoostVector();
    // Printf("boost Vec " );

    // boostVector.Print();

    // Printf("Lab Frame the (prton D total) " );

    // // 打印碰撞前的四维动量 实验室系
    // P_pro_lab_beforeCollision.Print();
    // P_D_lab_beforeCollision.Print();
    // P_total_lab.Print();


    // Perform Lorentz transformation
    //

    TLorentzVector P_pro_c_beforeCollision = P_pro_lab_beforeCollision;
    TLorentzVector P_D_c_beforeCollision = P_D_lab_beforeCollision;
    TLorentzVector P_total_c = P_total_lab;
    P_pro_c_beforeCollision.Boost(-boostVector);
    P_D_c_beforeCollision.Boost(-boostVector);
    P_total_c.Boost(-boostVector);





    // Printf("center of mass frame the (prton D total) " );
    // // center of mass frame
    // P_pro_c_beforeCollision.Print();
    // P_D_c_beforeCollision.Print();
    // P_total_c.Print();




    // 提取三维分量
    // double P_pro_c_z_momentum = P_pro_c_beforeCollision.Pz();
    // double P_D_c_z_momentum = P_D_c_beforeCollision.Pz();
    // double P_pro_c_E = P_pro_c_beforeCollision.E();
    // double P_D_c_E = P_D_c_beforeCollision.E();




    // P_pro_c_beforeCollision.SetXYZ(P_pro_c_z_momentum *sin(theta_D_c) * cos(phi_D_c),P_pro_c_z_momentum * sin(theta_D_c) * sin(phi_D_c), P_pro_c_z_momentum *cos(theta_D_c));
    // P_D_c_beforeCollision.SetXYZ(P_D_c_z_momentum *sin(theta_D_c) * cos(phi_D_c),P_D_c_z_momentum * sin(theta_D_c) * sin(phi_D_c), P_D_c_z_momentum *cos(theta_D_c));
    //旋转
    // P_pro_c_beforeCollision.SetPtEtaPhiE(P_D_c_z_momentum ,theta_D_c, phi_D_c, P_D_c_E);
    // P_D_c_beforeCollision.SetPtEtaPhiE(P_pro_c_z_momentum ,theta_D_c, phi_D_c, P_pro_c_E);
    P_pro_c_beforeCollision.SetTheta(M_PI-theta_D_c);
    P_pro_c_beforeCollision.SetPhi(M_PI+phi_D_c);
    P_D_c_beforeCollision.SetTheta(theta_D_c);
    P_D_c_beforeCollision.SetPhi(phi_D_c);

    // Printf("center of mass frame the 旋转后 (prton D total) " );
    // P_pro_c_beforeCollision.Print();
    // P_D_c_beforeCollision.Print();

    // bost回实验室系
    P_pro_c_beforeCollision.Boost(boostVector);
    P_D_c_beforeCollision.Boost(boostVector);

    // Printf("实验室系 (prton D total) " );
    // P_pro_c_beforeCollision.Print();
    // P_D_c_beforeCollision.Print();


    //实验室系下 散射的D和p的四动量
    return std::make_pair( P_D_c_beforeCollision, P_pro_c_beforeCollision);
}



std::pair<double , double> func_theta_D_c(double theta_D_lab_rad){
    double theta_D_c_1 ;
    double theta_D_c_2 ;

    // 计算中间变量
    double tan_theta = tan(theta_D_lab_rad);
    double gamma_me_tan_theta = gamma_me * tan_theta;
    double sqrt_term = sqrt(1 + gamma_me * gamma_me * tan_theta * tan_theta);
    double arcsin_term = asin((tan_theta * gamma_me * beta * EDCM) / (PDCM * sqrt_term));

    // 计算 theta_D_c_1 和 theta_D_c_2
    theta_D_c_1 = atan(gamma_me_tan_theta) + arcsin_term;
    theta_D_c_2 = atan(gamma_me_tan_theta) + M_PI - arcsin_term;


    return std::make_pair(theta_D_c_1, theta_D_c_2);
}




double func_theta_p_lab(double theta_D_c_rad) {
    // 计算中间变量
    double sin_theta = sin(theta_D_c_rad);
    double cos_theta = cos(theta_D_c_rad);
    double numerator = PDCM * sin_theta;
    double denominator = gamma_me * beta * EPCM - gamma_me * PDCM * cos_theta;

 
    double theta_p_lab_rad = atan(numerator / denominator);

    return theta_p_lab_rad;
}

// 从质子实验系角度计算质子cm系角度
double func_theta_P_cm(double theta_p_lab){

    // 计算中间变量
    double tan_theta = tan(theta_p_lab);
    double gamma_me_tan_theta = gamma_me * tan_theta;
    double sqrt_term = sqrt(1 + gamma_me * gamma_me * tan_theta * tan_theta);
    double arcsin_term = asin((tan_theta * gamma_me * beta * EPCM) / (PDCM * sqrt_term));

    
    double theta_p_cm =M_PI -(atan(gamma_me_tan_theta) + arcsin_term);
    return theta_p_cm;

}

